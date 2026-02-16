# Installation Guide

## Prerequisites

### System Requirements
- **OS**: Windows 10/11, Linux (Ubuntu 18.04+), macOS 10.14+
- **Python**: 3.8 or higher
- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: 2GB free space (for models and dependencies)
- **GPU** (Optional): CUDA-compatible GPU for acceleration

### Required Software
1. **Python 3.8+**: Download from https://www.python.org/
2. **Tesseract OCR** (Optional fallback):
   - Windows: Download installer from https://github.com/UB-Mannheim/tesseract/wiki
   - Linux: `sudo apt-get install tesseract-ocr`
   - macOS: `brew install tesseract`

## Installation Steps

### 1. Clone or Download Project
```bash
# If using git
git clone <repository-url>
cd project

# Or extract downloaded ZIP file
```

### 2. Create Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**Note**: First run will download EasyOCR models (~100MB for English). This happens automatically and models are cached in `~/.EasyOCR/`.

### 4. Verify Installation
```bash
# Test import
python -c "import easyocr; print('EasyOCR installed successfully')"

# Check OpenCV
python -c "import cv2; print('OpenCV version:', cv2.__version__)"
```

## GPU Setup (Optional)

For CUDA acceleration:

### 1. Install CUDA Toolkit
- Download from: https://developer.nvidia.com/cuda-downloads
- Recommended version: CUDA 11.8 or 12.1

### 2. Install PyTorch with CUDA
```bash
# For CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### 3. Verify GPU
```bash
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

## Troubleshooting

### Issue: EasyOCR model download fails
**Solution**: 
- Check internet connection (required for first-time setup)
- Manually download models from: https://github.com/JaidedAI/EasyOCR/releases
- Place in `~/.EasyOCR/model/`

### Issue: OpenCV import error
**Solution**:
```bash
pip uninstall opencv-python opencv-python-headless
pip install opencv-python==4.8.1.78
```

### Issue: Tesseract not found
**Solution**:
- Ensure Tesseract is installed and in PATH
- Windows: Add `C:\Program Files\Tesseract-OCR` to PATH
- Verify: `tesseract --version`

### Issue: Memory error during processing
**Solution**:
- Reduce image size before processing
- Process images in smaller batches
- Close other applications

## Quick Test

```bash
# Test with sample image (create a test image first)
python main.py --image test_images/sample.jpg

# Run Streamlit app
streamlit run app.py
```

## Next Steps

1. Place test images in `test_images/` folder
2. Run OCR: `python main.py --image test_images/your_image.jpg`
3. Check results in `outputs/` folder
4. For web interface: `streamlit run app.py`

## Offline Operation

After initial setup, the system works 100% offline:
- EasyOCR models are cached locally
- No internet connection required for inference
- All processing happens on local machine
