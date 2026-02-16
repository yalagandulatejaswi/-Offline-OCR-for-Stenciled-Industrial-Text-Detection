"""
Test Script for Industrial OCR System
======================================
Validates system functionality and performance
"""

import os
import sys
import time
import json
from pathlib import Path
import cv2
import numpy as np

from main import IndustrialOCRSystem


def create_test_image():
    """
    Create a synthetic test image with stenciled text.
    Useful for testing when no real images are available.
    """
    print("Creating synthetic test image...")
    
    # Create blank image (gray background)
    img = np.ones((400, 800, 3), dtype=np.uint8) * 120
    
    # Add text using OpenCV (simulates stenciled text)
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    texts = [
        ("BATCH-2024-A", (50, 100)),
        ("WEIGHT-50KG", (50, 200)),
        ("SERIAL-XYZ-123", (50, 300))
    ]
    
    for text, pos in texts:
        cv2.putText(img, text, pos, font, 1.5, (255, 255, 255), 3)
    
    # Add some noise to simulate real conditions
    noise = np.random.normal(0, 10, img.shape).astype(np.uint8)
    img = cv2.add(img, noise)
    
    # Save test image
    test_dir = Path("test_images")
    test_dir.mkdir(exist_ok=True)
    test_path = test_dir / "synthetic_test.jpg"
    cv2.imwrite(str(test_path), img)
    
    print(f"✓ Test image created: {test_path}")
    return str(test_path)


def test_initialization():
    """Test OCR system initialization."""
    print("\n" + "="*60)
    print("TEST 1: System Initialization")
    print("="*60)
    
    try:
        ocr = IndustrialOCRSystem(languages=['en'], gpu=False)
        print("✓ OCR system initialized successfully")
        return True, ocr
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        return False, None


def test_preprocessing(ocr, image_path):
    """Test preprocessing pipeline."""
    print("\n" + "="*60)
    print("TEST 2: Preprocessing Pipeline")
    print("="*60)
    
    try:
        image = cv2.imread(image_path)
        if image is None:
            print(f"✗ Failed to load image: {image_path}")
            return False
        
        print(f"  Input image shape: {image.shape}")
        
        preprocessed, enhanced = ocr.preprocess_image(image)
        
        print(f"  Preprocessed shape: {preprocessed.shape}")
        print(f"  Enhanced shape: {enhanced.shape}")
        print("✓ Preprocessing completed successfully")
        return True
    except Exception as e:
        print(f"✗ Preprocessing failed: {e}")
        return False


def test_ocr_inference(ocr, image_path):
    """Test OCR inference."""
    print("\n" + "="*60)
    print("TEST 3: OCR Inference")
    print("="*60)
    
    try:
        image = cv2.imread(image_path)
        preprocessed, _ = ocr.preprocess_image(image)
        
        start_time = time.time()
        detections = ocr.run_ocr(image, preprocessed)
        inference_time = time.time() - start_time
        
        print(f"  Inference time: {inference_time:.2f} seconds")
        print(f"  Detections found: {len(detections)}")
        
        for i, det in enumerate(detections):
            print(f"    [{i}] Text: '{det['text']}' | Confidence: {det['confidence']:.3f}")
        
        print("✓ OCR inference completed successfully")
        return True, detections
    except Exception as e:
        print(f"✗ OCR inference failed: {e}")
        return False, []


def test_output_generation(ocr, image_path):
    """Test structured output generation."""
    print("\n" + "="*60)
    print("TEST 4: Output Generation")
    print("="*60)
    
    try:
        result = ocr.process_image(image_path)
        
        if result is None:
            print("✗ Processing returned None")
            return False
        
        # Validate JSON structure
        required_keys = ['metadata', 'detections', 'summary']
        for key in required_keys:
            if key not in result:
                print(f"✗ Missing key in output: {key}")
                return False
        
        print("  Output structure validation:")
        print(f"    ✓ metadata: {len(result['metadata'])} fields")
        print(f"    ✓ detections: {len(result['detections'])} items")
        print(f"    ✓ summary: {len(result['summary'])} fields")
        
        # Check output files
        output_dir = Path("outputs")
        json_files = list(output_dir.glob("*.json"))
        img_files = list(output_dir.glob("*_annotated.jpg"))
        
        print(f"  Output files:")
        print(f"    JSON files: {len(json_files)}")
        print(f"    Annotated images: {len(img_files)}")
        
        print("✓ Output generation completed successfully")
        return True
    except Exception as e:
        print(f"✗ Output generation failed: {e}")
        return False


def test_batch_processing(ocr):
    """Test batch processing mode."""
    print("\n" + "="*60)
    print("TEST 5: Batch Processing")
    print("="*60)
    
    try:
        test_dir = "test_images"
        if not Path(test_dir).exists() or not list(Path(test_dir).glob("*.jpg")):
            print("  ⚠ No test images found, skipping batch test")
            return True
        
        start_time = time.time()
        results = ocr.process_batch(test_dir)
        batch_time = time.time() - start_time
        
        print(f"  Batch processing time: {batch_time:.2f} seconds")
        print(f"  Images processed: {len(results)}")
        print(f"  Average time per image: {batch_time/max(len(results), 1):.2f} seconds")
        
        print("✓ Batch processing completed successfully")
        return True
    except Exception as e:
        print(f"✗ Batch processing failed: {e}")
        return False


def test_error_handling(ocr):
    """Test error handling."""
    print("\n" + "="*60)
    print("TEST 6: Error Handling")
    print("="*60)
    
    # Test with non-existent file
    result = ocr.process_image("nonexistent_file.jpg")
    if result is None:
        print("  ✓ Correctly handled non-existent file")
    else:
        print("  ✗ Should return None for non-existent file")
        return False
    
    # Test with invalid image
    invalid_path = Path("test_images/invalid.jpg")
    invalid_path.parent.mkdir(exist_ok=True)
    with open(invalid_path, 'w') as f:
        f.write("This is not an image")
    
    result = ocr.process_image(str(invalid_path))
    if result is None:
        print("  ✓ Correctly handled invalid image file")
    else:
        print("  ✗ Should return None for invalid image")
        return False
    
    # Cleanup
    invalid_path.unlink()
    
    print("✓ Error handling tests passed")
    return True


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "="*70)
    print(" "*15 + "INDUSTRIAL OCR SYSTEM - TEST SUITE")
    print("="*70)
    
    # Create test image if needed
    test_image = create_test_image()
    
    # Track results
    results = {}
    
    # Test 1: Initialization
    success, ocr = test_initialization()
    results['initialization'] = success
    
    if not success:
        print("\n✗ Cannot proceed without successful initialization")
        return
    
    # Test 2: Preprocessing
    results['preprocessing'] = test_preprocessing(ocr, test_image)
    
    # Test 3: OCR Inference
    success, detections = test_ocr_inference(ocr, test_image)
    results['ocr_inference'] = success
    
    # Test 4: Output Generation
    results['output_generation'] = test_output_generation(ocr, test_image)
    
    # Test 5: Batch Processing
    results['batch_processing'] = test_batch_processing(ocr)
    
    # Test 6: Error Handling
    results['error_handling'] = test_error_handling(ocr)
    
    # Summary
    print("\n" + "="*70)
    print(" "*25 + "TEST SUMMARY")
    print("="*70)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name.replace('_', ' ').title():<30} {status}")
    
    print("-"*70)
    print(f"  Total: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n  🎉 All tests passed! System is ready for use.")
    else:
        print(f"\n  ⚠ {total_tests - passed_tests} test(s) failed. Please review errors above.")
    
    print("="*70)


if __name__ == "__main__":
    run_all_tests()
