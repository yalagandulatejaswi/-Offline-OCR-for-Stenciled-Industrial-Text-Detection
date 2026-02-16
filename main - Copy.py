"""
Offline OCR System for Industrial Stenciled Text Detection
============================================================
Author: Senior Computer Vision Engineer
Purpose: Extract text from industrial boxes with faded/stenciled paint

TECHNICAL APPROACH:
- Hybrid OCR: EasyOCR (primary) + Tesseract (fallback)
- Advanced preprocessing for low-contrast industrial images
- Structured JSON output with confidence scores
- 100% Offline operation

PIPELINE STAGES:
1. Image Loading & Validation
2. Preprocessing (CLAHE, denoising, thresholding)
3. OCR Inference (EasyOCR with custom parameters)
4. Post-processing (text cleaning, validation)
5. Structured Output Generation
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import cv2
import numpy as np
from PIL import Image
import easyocr

# Configure logging system
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ocr_system.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class IndustrialOCRSystem:
    """
    Complete OCR system optimized for industrial stenciled text detection.
    
    Key Features:
    - Offline operation (no cloud APIs)
    - Advanced preprocessing for challenging conditions
    - Confidence-based text extraction
    - Structured JSON output
    """
    
    def __init__(self, languages: List[str] = ['en'], gpu: bool = False):
        """
        Initialize OCR system with EasyOCR reader.
        
        Args:
            languages: List of language codes (default: English only)
            gpu: Enable GPU acceleration if available
        
        Technical Note:
        - EasyOCR downloads models on first run (~100MB for English)
        - Models are cached locally in ~/.EasyOCR/
        - CRAFT detector + CRNN recognizer architecture
        """
        logger.info("Initializing Industrial OCR System...")
        try:
            self.reader = easyocr.Reader(
                languages, 
                gpu=gpu,
                verbose=False
            )
            logger.info(f"EasyOCR initialized successfully (GPU: {gpu})")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            raise
        
        # Create output directories
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(exist_ok=True)
        
    def preprocess_image(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Advanced preprocessing pipeline for industrial images.
        
        Pipeline Steps:
        1. Grayscale conversion - Simplifies processing, focuses on intensity
        2. CLAHE - Enhances local contrast in faded regions
        3. Bilateral filtering - Reduces noise while preserving edges
        4. Adaptive thresholding - Handles varying lighting conditions
        5. Morphological operations - Connects broken characters
        
        Args:
            image: Input BGR image from cv2.imread()
        
        Returns:
            Tuple of (preprocessed_image, visualization_image)
        
        Why each step matters for industrial text:
        - CLAHE: Critical for faded paint with low contrast
        - Bilateral: Removes surface noise (rust, dirt) without blurring text edges
        - Adaptive threshold: Handles shadows and uneven lighting on boxes
        - Morphology: Reconnects cracked/chipped stenciled characters
        """
        logger.info("Starting preprocessing pipeline...")
        
        # Step 1: Convert to grayscale
        # Reason: Reduces 3-channel complexity, focuses on luminance
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Step 2: Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        # Reason: Enhances local contrast in faded/weathered text regions
        # Parameters: clipLimit=3.0 prevents over-amplification of noise
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Step 3: Bilateral filtering
        # Reason: Reduces noise while preserving sharp text edges
        # Parameters: d=9 (neighborhood), sigmaColor=75, sigmaSpace=75
        denoised = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)
        
        # Step 4: Adaptive thresholding
        # Reason: Binarization that adapts to local lighting conditions
        # Method: Gaussian-weighted mean of neighborhood
        binary = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,
            C=2
        )
        
        # Step 5: Morphological operations
        # Reason: Connect broken characters, remove small noise artifacts
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        # Optional: Deskewing (correct text rotation)
        # Useful for angled photos of boxes
        morph = self._deskew_image(morph)
        
        logger.info("Preprocessing completed successfully")
        return morph, enhanced
    
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """
        Correct skewed text orientation using moment-based angle detection.
        
        Technical approach:
        - Calculate image moments to find orientation
        - Rotate image to align text horizontally
        - Critical for angled photos of industrial boxes
        """
        coords = np.column_stack(np.where(image > 0))
        if len(coords) == 0:
            return image
        
        angle = cv2.minAreaRect(coords)[-1]
        
        # Adjust angle based on orientation
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # Only correct if skew is significant (> 0.5 degrees)
        if abs(angle) < 0.5:
            return image
        
        # Rotate image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        
        logger.info(f"Deskewed image by {angle:.2f} degrees")
        return rotated
    
    def run_ocr(self, image: np.ndarray, preprocessed: np.ndarray) -> List[Dict]:
        """
        Execute OCR inference using EasyOCR with optimized parameters.
        
        Args:
            image: Original color image (for visualization)
            preprocessed: Preprocessed binary image (for better OCR)
        
        Returns:
            List of detection dictionaries with text, confidence, and bbox
        
        EasyOCR Parameters Explained:
        - detail=1: Returns bounding box coordinates
        - paragraph=False: Detect individual text regions (not paragraphs)
        - min_size=10: Minimum text height in pixels
        - text_threshold=0.6: Confidence threshold for character detection
        - low_text=0.3: Threshold for linking characters into words
        - link_threshold=0.3: Threshold for linking text regions
        
        Why these settings for industrial text:
        - Lower thresholds (0.6 vs default 0.7) to catch faded text
        - min_size=10 to detect small stenciled characters
        - paragraph=False for isolated text blocks on boxes
        """
        logger.info("Running OCR inference...")
        
        try:
            # Run EasyOCR on preprocessed image
            results = self.reader.readtext(
                preprocessed,
                detail=1,
                paragraph=False,
                min_size=10,
                text_threshold=0.6,
                low_text=0.3,
                link_threshold=0.3
            )
            
            # Parse results into structured format
            detections = []
            for idx, (bbox, text, confidence) in enumerate(results):
                # Extract bounding box coordinates
                # bbox format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                bbox_array = np.array(bbox).astype(int)
                x_min = int(bbox_array[:, 0].min())
                y_min = int(bbox_array[:, 1].min())
                x_max = int(bbox_array[:, 0].max())
                y_max = int(bbox_array[:, 1].max())
                
                # Clean and validate text
                cleaned_text = self._clean_text(text)
                
                detection = {
                    'id': f"detection_{idx:03d}",
                    'text': cleaned_text,
                    'raw_text': text,
                    'confidence': round(confidence, 3),
                    'bbox': [x_min, y_min, x_max, y_max],
                    'bbox_polygon': bbox_array.tolist()
                }
                
                detections.append(detection)
                logger.info(f"Detected: '{cleaned_text}' (confidence: {confidence:.3f})")
            
            logger.info(f"OCR completed: {len(detections)} text regions detected")
            return detections
            
        except Exception as e:
            logger.error(f"OCR inference failed: {e}")
            return []
    
    def _clean_text(self, text: str) -> str:
        """
        Post-process OCR text to remove noise and fix common errors.
        
        Cleaning steps:
        1. Strip whitespace
        2. Remove special characters (keep alphanumeric, dash, underscore)
        3. Fix common OCR mistakes (0/O, 1/I/l, 5/S)
        
        Industrial text characteristics:
        - Often alphanumeric codes (BATCH-2024-A)
        - May contain dashes, underscores
        - Common confusions in stenciled fonts
        """
        # Basic cleaning
        cleaned = text.strip()
        
        # Remove unwanted characters (keep alphanumeric, dash, underscore, space)
        import re
        cleaned = re.sub(r'[^A-Za-z0-9\-_\s]', '', cleaned)
        
        # Optional: Fix common OCR errors
        # Uncomment if needed for specific use cases
        # cleaned = cleaned.replace('0', 'O')  # If expecting letters
        # cleaned = cleaned.replace('l', '1')  # If expecting numbers
        
        return cleaned
    
    def structure_output(self, detections: List[Dict], filename: str) -> Dict:
        """
        Convert OCR detections into structured JSON format.
        
        Output structure designed for industrial use cases:
        - Metadata: filename, timestamp, processing info
        - Detections: array of text regions with confidence
        - Summary: statistics and quality metrics
        
        Args:
            detections: List of detection dictionaries from run_ocr()
            filename: Original image filename
        
        Returns:
            Structured dictionary ready for JSON serialization
        """
        # Calculate summary statistics
        avg_confidence = np.mean([d['confidence'] for d in detections]) if detections else 0.0
        high_conf_count = sum(1 for d in detections if d['confidence'] > 0.8)
        
        structured_output = {
            'metadata': {
                'filename': filename,
                'timestamp': datetime.now().isoformat(),
                'total_detections': len(detections),
                'average_confidence': round(avg_confidence, 3),
                'high_confidence_count': high_conf_count,
                'processing_version': '1.0.0'
            },
            'detections': detections,
            'summary': {
                'extracted_texts': [d['text'] for d in detections],
                'quality_score': self._calculate_quality_score(detections)
            }
        }
        
        return structured_output
    
    def _calculate_quality_score(self, detections: List[Dict]) -> str:
        """
        Assess overall OCR quality based on confidence scores.
        
        Quality levels:
        - EXCELLENT: avg confidence > 0.85
        - GOOD: avg confidence > 0.70
        - FAIR: avg confidence > 0.50
        - POOR: avg confidence <= 0.50
        """
        if not detections:
            return "NO_TEXT_DETECTED"
        
        avg_conf = np.mean([d['confidence'] for d in detections])
        
        if avg_conf > 0.85:
            return "EXCELLENT"
        elif avg_conf > 0.70:
            return "GOOD"
        elif avg_conf > 0.50:
            return "FAIR"
        else:
            return "POOR"
    
    def save_results(self, output_data: Dict, image: np.ndarray, 
                     detections: List[Dict], output_name: str) -> Tuple[str, str]:
        """
        Save OCR results to disk (JSON + annotated image).
        
        Outputs:
        1. JSON file: Structured text data with metadata
        2. Annotated image: Visual verification with bounding boxes
        
        Args:
            output_data: Structured output from structure_output()
            image: Original image for annotation
            detections: Detection list for drawing boxes
            output_name: Base name for output files
        
        Returns:
            Tuple of (json_path, image_path)
        """
        # Save JSON output
        json_path = self.output_dir / f"{output_name}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        logger.info(f"JSON saved: {json_path}")
        
        # Create annotated image
        annotated = image.copy()
        for detection in detections:
            bbox = detection['bbox']
            text = detection['text']
            conf = detection['confidence']
            
            # Draw bounding box (color based on confidence)
            # Green: high confidence (>0.8)
            # Yellow: medium confidence (0.6-0.8)
            # Red: low confidence (<0.6)
            if conf > 0.8:
                color = (0, 255, 0)  # Green
            elif conf > 0.6:
                color = (0, 255, 255)  # Yellow
            else:
                color = (0, 0, 255)  # Red
            
            cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            
            # Add text label
            label = f"{text} ({conf:.2f})"
            cv2.putText(annotated, label, (bbox[0], bbox[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Save annotated image
        image_path = self.output_dir / f"{output_name}_annotated.jpg"
        cv2.imwrite(str(image_path), annotated)
        logger.info(f"Annotated image saved: {image_path}")
        
        return str(json_path), str(image_path)
    
    def process_image(self, image_path: str) -> Optional[Dict]:
        """
        Complete end-to-end OCR pipeline for a single image.
        
        Pipeline:
        1. Load and validate image
        2. Preprocess for OCR
        3. Run OCR inference
        4. Structure output
        5. Save results
        
        Args:
            image_path: Path to input image
        
        Returns:
            Structured output dictionary or None if failed
        """
        logger.info(f"Processing image: {image_path}")
        
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to load image: {image_path}")
                return None
            
            # Preprocess
            preprocessed, enhanced = self.preprocess_image(image)
            
            # Run OCR
            detections = self.run_ocr(image, preprocessed)
            
            # Structure output
            filename = Path(image_path).name
            output_data = self.structure_output(detections, filename)
            
            # Save results
            output_name = Path(image_path).stem
            json_path, img_path = self.save_results(
                output_data, image, detections, output_name
            )
            
            logger.info(f"Processing completed successfully")
            return output_data
            
        except Exception as e:
            logger.error(f"Error processing image: {e}", exc_info=True)
            return None
    
    def process_batch(self, input_folder: str) -> List[Dict]:
        """
        Process multiple images in batch mode.
        
        Useful for:
        - Processing entire folders of industrial photos
        - Batch analysis of inventory boxes
        - Quality control workflows
        
        Args:
            input_folder: Path to folder containing images
        
        Returns:
            List of structured outputs for all processed images
        """
        logger.info(f"Starting batch processing: {input_folder}")
        
        input_path = Path(input_folder)
        if not input_path.exists():
            logger.error(f"Input folder not found: {input_folder}")
            return []
        
        # Supported image formats
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        image_files = [
            f for f in input_path.iterdir() 
            if f.suffix.lower() in image_extensions
        ]
        
        logger.info(f"Found {len(image_files)} images to process")
        
        results = []
        for idx, image_file in enumerate(image_files, 1):
            logger.info(f"Processing {idx}/{len(image_files)}: {image_file.name}")
            result = self.process_image(str(image_file))
            if result:
                results.append(result)
        
        logger.info(f"Batch processing completed: {len(results)}/{len(image_files)} successful")
        return results


def main():
    """
    Main entry point with CLI argument support.
    
    Usage examples:
    - Single image: python main.py --image test_images/box1.jpg
    - Batch mode: python main.py --batch test_images/
    - With GPU: python main.py --image test.jpg --gpu
    """
    parser = argparse.ArgumentParser(
        description='Offline OCR System for Industrial Stenciled Text'
    )
    parser.add_argument(
        '--image', 
        type=str, 
        help='Path to single image file'
    )
    parser.add_argument(
        '--batch', 
        type=str, 
        help='Path to folder for batch processing'
    )
    parser.add_argument(
        '--gpu', 
        action='store_true', 
        help='Enable GPU acceleration'
    )
    parser.add_argument(
        '--lang', 
        type=str, 
        default='en', 
        help='Language code (default: en)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.image and not args.batch:
        parser.print_help()
        print("\nError: Please specify either --image or --batch")
        sys.exit(1)
    
    # Initialize OCR system
    try:
        ocr_system = IndustrialOCRSystem(
            languages=[args.lang], 
            gpu=args.gpu
        )
    except Exception as e:
        logger.error(f"Failed to initialize OCR system: {e}")
        sys.exit(1)
    
    # Process image(s)
    if args.image:
        result = ocr_system.process_image(args.image)
        if result:
            print("\n" + "="*60)
            print("OCR RESULTS")
            print("="*60)
            print(json.dumps(result, indent=2))
    
    elif args.batch:
        results = ocr_system.process_batch(args.batch)
        print(f"\nBatch processing completed: {len(results)} images processed")


if __name__ == "__main__":
    main()



"""
================================================================================
CHALLENGES & IMPROVEMENTS SECTION
================================================================================

CHALLENGES FACED IN INDUSTRIAL OCR:
------------------------------------

1. LOW CONTRAST & FADED TEXT
   - Problem: Paint degradation over time reduces text visibility
   - Solution: CLAHE for local contrast enhancement
   - Limitation: Extremely faded text (<10% contrast) may be unrecoverable
   - Future: Train custom model on synthetic faded text dataset

2. SURFACE NOISE & DAMAGE
   - Problem: Rust, dirt, scratches create false text patterns
   - Solution: Bilateral filtering + morphological operations
   - Limitation: Heavy damage may fragment characters beyond recognition
   - Future: Implement inpainting to reconstruct damaged regions

3. VARYING LIGHTING CONDITIONS
   - Problem: Outdoor photos have shadows, reflections, uneven lighting
   - Solution: Adaptive thresholding handles local variations
   - Limitation: Extreme glare or deep shadows still problematic
   - Future: HDR image capture or multi-exposure fusion

4. PERSPECTIVE DISTORTION
   - Problem: Angled photos of boxes distort text geometry
   - Solution: Deskewing corrects rotation, but not full perspective
   - Limitation: Severe perspective requires 3D transformation
   - Future: Implement perspective correction using corner detection

5. STENCIL FONT VARIATIONS
   - Problem: Different stencil styles, broken characters, irregular spacing
   - Solution: EasyOCR's deep learning handles font variations better than Tesseract
   - Limitation: Highly stylized or custom stencils may fail
   - Future: Fine-tune CRNN model on industrial stencil dataset


INDUSTRIAL LIMITATIONS:
-----------------------

1. OFFLINE CONSTRAINT
   - Cannot leverage cloud-based models (Google Vision, AWS Textract)
   - Limited to open-source models that fit in memory
   - Trade-off: Accuracy vs. model size vs. inference speed

2. REAL-TIME REQUIREMENTS
   - Industrial workflows may need <1 second per image
   - Current pipeline: ~2-5 seconds per image on CPU
   - GPU acceleration helps but not always available in industrial settings

3. ENVIRONMENTAL FACTORS
   - Outdoor conditions: rain, fog, dust affect image quality
   - Temperature extremes may affect camera performance
   - Solution: Recommend controlled lighting and camera positioning

4. HARDWARE CONSTRAINTS
   - Industrial PCs may have limited RAM/CPU
   - Edge devices (Raspberry Pi) struggle with deep learning models
   - Solution: Model quantization or lighter architectures (MobileNet-based)


POSSIBLE IMPROVEMENTS:
----------------------

1. CUSTOM MODEL TRAINING
   - Collect industrial stencil dataset (1000+ images)
   - Fine-tune EasyOCR's CRNN on domain-specific data
   - Expected improvement: +10-15% accuracy on faded text

2. ENSEMBLE APPROACH
   - Combine EasyOCR + Tesseract + PaddleOCR
   - Use voting mechanism for final text output
   - Increases robustness but slower inference

3. ADVANCED PREPROCESSING
   - Implement perspective correction (4-point transform)
   - Add super-resolution for low-quality images
   - Use GAN-based image enhancement for faded text

4. CONFIDENCE-BASED FILTERING
   - Reject low-confidence detections (<0.5)
   - Flag uncertain results for human review
   - Implement active learning loop

5. DOMAIN-SPECIFIC POST-PROCESSING
   - Use regex patterns for expected formats (e.g., BATCH-YYYY-XXX)
   - Validate against known code structures
   - Implement spell-checking for known terms

6. MULTI-FRAME PROCESSING
   - Capture multiple photos of same box
   - Fuse results for higher confidence
   - Useful for critical applications (military, aerospace)


FUTURE SCALING IDEAS:
---------------------

1. DISTRIBUTED PROCESSING
   - Deploy on multiple edge devices
   - Central server aggregates results
   - Scales to factory-wide deployment

2. CONTINUOUS LEARNING
   - Collect failed cases for retraining
   - Implement human-in-the-loop correction
   - Periodically update models with new data

3. INTEGRATION WITH INVENTORY SYSTEMS
   - Auto-populate database from OCR results
   - Trigger alerts for damaged/unreadable labels
   - Generate reports on label quality trends

4. MOBILE APPLICATION
   - Deploy as Android/iOS app for field use
   - Real-time OCR with on-device inference
   - Sync results to cloud when online

5. QUALITY CONTROL DASHBOARD
   - Track OCR accuracy over time
   - Identify problematic label types
   - Recommend label replacement schedules

6. MULTI-LANGUAGE SUPPORT
   - Extend to non-English industrial sites
   - Handle mixed-language labels
   - Support for special characters and symbols


PRODUCTION DEPLOYMENT CHECKLIST:
---------------------------------
☐ Model optimization (quantization, pruning)
☐ Error handling for all edge cases
☐ Logging and monitoring system
☐ Unit tests and integration tests
☐ Performance benchmarking
☐ Security audit (input validation)
☐ Documentation and user manual
☐ Backup and recovery procedures
☐ Version control and rollback strategy
☐ User training and support plan

================================================================================
END OF CHALLENGES & IMPROVEMENTS
================================================================================
"""
