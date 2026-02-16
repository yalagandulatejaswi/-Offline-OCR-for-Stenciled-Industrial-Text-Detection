# Usage Guide

## Command Line Interface (CLI)

### Basic Usage

#### Process Single Image
```bash
python main.py --image test_images/box1.jpg
```

#### Batch Processing
```bash
python main.py --batch test_images/
```

#### Enable GPU Acceleration
```bash
python main.py --image test_images/box1.jpg --gpu
```

#### Multi-language Support
```bash
python main.py --image test_images/box1.jpg --lang en
```

### CLI Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--image` | Path to single image | `--image test.jpg` |
| `--batch` | Path to folder for batch processing | `--batch images/` |
| `--gpu` | Enable GPU acceleration | `--gpu` |
| `--lang` | Language code (default: en) | `--lang en` |

## Streamlit Web Interface

### Launch Application
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

### Using the Web Interface

1. **Upload Image**
   - Click "Browse files" or drag & drop
   - Supported formats: JPG, PNG, BMP, TIFF

2. **Configure Settings** (Sidebar)
   - Enable GPU if available
   - Toggle preprocessing visualization
   - Adjust confidence threshold

3. **Run OCR**
   - Click "Run OCR" button
   - Wait for processing (2-5 seconds)

4. **Review Results**
   - View annotated image with bounding boxes
   - Check extracted text table
   - Inspect JSON output

5. **Download Results**
   - Download JSON file
   - Download annotated image

## Output Files

### JSON Structure
```json
{
  "metadata": {
    "filename": "box_001.jpg",
    "timestamp": "2024-02-14T10:30:00",
    "total_detections": 3,
    "average_confidence": 0.85,
    "high_confidence_count": 2,
    "processing_version": "1.0.0"
  },
  "detections": [
    {
      "id": "detection_000",
      "text": "BATCH-2024-A",
      "raw_text": "BATCH-2024-A",
      "confidence": 0.923,
      "bbox": [120, 45, 340, 85],
      "bbox_polygon": [[120, 45], [340, 45], [340, 85], [120, 85]]
    }
  ],
  "summary": {
    "extracted_texts": ["BATCH-2024-A"],
    "quality_score": "EXCELLENT"
  }
}
```

### Annotated Images
- Saved in `outputs/` folder
- Filename: `{original_name}_annotated.jpg`
- Color coding:
  - **Green**: High confidence (>0.8)
  - **Yellow**: Medium confidence (0.6-0.8)
  - **Red**: Low confidence (<0.6)

## Best Practices

### Image Quality
- **Resolution**: Minimum 1280x720, recommended 1920x1080
- **Focus**: Ensure text is sharp and in focus
- **Lighting**: Even lighting, avoid harsh shadows
- **Distance**: 0.5m to 2m from subject
- **Angle**: Front-facing preferred, max 30° angle

### Preprocessing Tips
- System automatically handles most cases
- For extremely faded text, try multiple photos
- Clean lens before capturing images
- Use flash in low-light conditions

### Performance Optimization
- **CPU Mode**: 2-5 seconds per image
- **GPU Mode**: 0.5-2 seconds per image
- **Batch Processing**: More efficient for multiple images
- **Image Size**: Resize large images (>4K) for faster processing

## Common Use Cases

### 1. Inventory Management
```bash
# Process entire warehouse folder
python main.py --batch warehouse_photos/

# Results saved to outputs/ folder
# Import JSON files into inventory system
```

### 2. Quality Control
```bash
# Check single box label
python main.py --image qc_sample.jpg

# Review confidence scores
# Flag low-confidence detections for manual review
```

### 3. Field Operations
```bash
# Use Streamlit app on tablet/laptop
streamlit run app.py

# Upload photos from mobile device
# Immediate visual feedback
```

## Troubleshooting

### No Text Detected
- Check image quality and focus
- Ensure text is visible to human eye
- Lower confidence threshold
- Try different lighting conditions

### Low Confidence Scores
- Improve image quality
- Clean surface before photographing
- Use better lighting
- Capture from optimal angle

### Incorrect Text Recognition
- Text may be too degraded
- Try preprocessing adjustments
- Consider manual verification
- Collect more training data for fine-tuning

## Advanced Usage

### Custom Preprocessing
Modify `preprocess_image()` in `main.py`:
```python
# Adjust CLAHE parameters
clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(16, 16))

# Change threshold settings
binary = cv2.adaptiveThreshold(
    denoised, 255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY,
    blockSize=15,  # Increase for larger text
    C=3
)
```

### Batch Processing with Filtering
```python
from main import IndustrialOCRSystem

ocr = IndustrialOCRSystem()
results = ocr.process_batch('test_images/')

# Filter high-quality results
good_results = [
    r for r in results 
    if r['metadata']['average_confidence'] > 0.8
]
```

## Integration Examples

### Python Script Integration
```python
from main import IndustrialOCRSystem

# Initialize
ocr = IndustrialOCRSystem(languages=['en'], gpu=False)

# Process image
result = ocr.process_image('box.jpg')

# Extract specific fields
batch_number = result['detections'][0]['text']
confidence = result['detections'][0]['confidence']

# Use in your application
if confidence > 0.8:
    update_database(batch_number)
```

### REST API Wrapper (Future Enhancement)
```python
from flask import Flask, request, jsonify
from main import IndustrialOCRSystem

app = Flask(__name__)
ocr = IndustrialOCRSystem()

@app.route('/ocr', methods=['POST'])
def process_ocr():
    file = request.files['image']
    result = ocr.process_image(file)
    return jsonify(result)
```
