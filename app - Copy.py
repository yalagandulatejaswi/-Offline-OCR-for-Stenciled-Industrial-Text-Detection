"""
Streamlit Web Interface for Industrial OCR System
==================================================
Single-page application for offline OCR processing

Features:
- Image upload interface
- Real-time OCR processing
- Visual results display
- JSON output download
- Preprocessing visualization
"""

import streamlit as st
import cv2
import numpy as np
from PIL import Image
import json
import io
from pathlib import Path
import sys

# Import OCR system
from main import IndustrialOCRSystem

# Page configuration
st.set_page_config(
    page_title="Industrial OCR System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_ocr_system(use_gpu=False):
    """
    Load OCR system with caching to avoid reinitialization.
    
    Streamlit's @st.cache_resource ensures the model is loaded only once
    and reused across user sessions for better performance.
    """
    return IndustrialOCRSystem(languages=['en'], gpu=use_gpu)


def main():
    """Main Streamlit application."""
    
    # Header
    st.markdown('<div class="main-header">🔍 Industrial OCR System</div>', 
                unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Offline OCR for Stenciled & Industrial Text Detection</div>', 
                unsafe_allow_html=True)
    
    # Sidebar configuration
    st.sidebar.title("⚙️ Configuration")
    
    use_gpu = st.sidebar.checkbox(
        "Enable GPU Acceleration",
        value=False,
        help="Enable if CUDA-compatible GPU is available"
    )
    
    show_preprocessing = st.sidebar.checkbox(
        "Show Preprocessing Steps",
        value=True,
        help="Display intermediate preprocessing images"
    )
    
    confidence_threshold = st.sidebar.slider(
        "Confidence Threshold",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.05,
        help="Filter detections below this confidence"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### 📋 About
    This system uses:
    - **EasyOCR** for text detection
    - **Advanced preprocessing** for challenging conditions
    - **100% Offline** operation
    
    ### 🎯 Optimized For
    - Faded/weathered paint
    - Low contrast text
    - Surface damage & noise
    - Industrial stenciled fonts
    """)
    
    # Main content area
    st.markdown("---")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "📤 Upload Industrial Image",
        type=['jpg', 'jpeg', 'png', 'bmp', 'tiff'],
        help="Upload an image containing stenciled or industrial text"
    )
    
    if uploaded_file is not None:
        # Load image
        image_bytes = uploaded_file.read()
        image = Image.open(io.BytesIO(image_bytes))
        image_np = np.array(image)
        
        # Convert RGB to BGR for OpenCV
        if len(image_np.shape) == 3 and image_np.shape[2] == 3:
            image_cv = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        else:
            image_cv = image_np
        
        # Display original image
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📷 Original Image")
            st.image(image, use_container_width=True)
        
        # Process button
        if st.button("🚀 Run OCR", type="primary", use_container_width=True):
            with st.spinner("Initializing OCR system..."):
                try:
                    ocr_system = load_ocr_system(use_gpu)
                except Exception as e:
                    st.error(f"Failed to initialize OCR system: {e}")
                    return
            
            # Preprocessing
            with st.spinner("Preprocessing image..."):
                preprocessed, enhanced = ocr_system.preprocess_image(image_cv)
            
            # Show preprocessing results
            if show_preprocessing:
                with col2:
                    st.subheader("🔧 Preprocessed Image")
                    st.image(preprocessed, use_container_width=True, channels="GRAY")
            
            # Run OCR
            with st.spinner("Running OCR inference..."):
                detections = ocr_system.run_ocr(image_cv, preprocessed)
            
            # Filter by confidence
            filtered_detections = [
                d for d in detections 
                if d['confidence'] >= confidence_threshold
            ]
            
            # Display results
            st.markdown("---")
            st.subheader("📊 OCR Results")
            
            if not filtered_detections:
                st.warning("No text detected above confidence threshold. Try lowering the threshold.")
                return
            
            # Metrics
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            
            with col_m1:
                st.metric("Total Detections", len(filtered_detections))
            
            with col_m2:
                avg_conf = np.mean([d['confidence'] for d in filtered_detections])
                st.metric("Avg Confidence", f"{avg_conf:.2%}")
            
            with col_m3:
                high_conf = sum(1 for d in filtered_detections if d['confidence'] > 0.8)
                st.metric("High Confidence", high_conf)
            
            with col_m4:
                quality = ocr_system._calculate_quality_score(filtered_detections)
                st.metric("Quality Score", quality)
            
            # Annotated image
            st.subheader("🎯 Detected Text Regions")
            annotated = image_cv.copy()
            
            for detection in filtered_detections:
                bbox = detection['bbox']
                text = detection['text']
                conf = detection['confidence']
                
                # Color based on confidence
                if conf > 0.8:
                    color = (0, 255, 0)  # Green
                elif conf > 0.6:
                    color = (0, 255, 255)  # Yellow
                else:
                    color = (0, 0, 255)  # Red
                
                cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 3)
                
                # Add label with background
                label = f"{text} ({conf:.2f})"
                (label_w, label_h), _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                )
                cv2.rectangle(
                    annotated, 
                    (bbox[0], bbox[1] - label_h - 10),
                    (bbox[0] + label_w, bbox[1]),
                    color, -1
                )
                cv2.putText(
                    annotated, label, (bbox[0], bbox[1] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2
                )
            
            # Convert back to RGB for display
            annotated_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            st.image(annotated_rgb, use_container_width=True)
            
            # Detected text table
            st.subheader("📝 Extracted Text")
            
            import pandas as pd
            df = pd.DataFrame([
                {
                    'Text': d['text'],
                    'Confidence': f"{d['confidence']:.2%}",
                    'Bounding Box': f"({d['bbox'][0]}, {d['bbox'][1]}) - ({d['bbox'][2]}, {d['bbox'][3]})"
                }
                for d in filtered_detections
            ])
            st.dataframe(df, use_container_width=True)
            
            # Structured JSON output
            st.subheader("📄 Structured JSON Output")
            
            output_data = ocr_system.structure_output(
                filtered_detections, 
                uploaded_file.name
            )
            
            # Display JSON in expandable section
            with st.expander("View JSON", expanded=False):
                st.json(output_data)
            
            # Download buttons
            col_d1, col_d2 = st.columns(2)
            
            with col_d1:
                # Download JSON
                json_str = json.dumps(output_data, indent=2, ensure_ascii=False)
                st.download_button(
                    label="⬇️ Download JSON",
                    data=json_str,
                    file_name=f"{Path(uploaded_file.name).stem}_ocr.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with col_d2:
                # Download annotated image
                is_success, buffer = cv2.imencode(".jpg", annotated)
                if is_success:
                    st.download_button(
                        label="⬇️ Download Annotated Image",
                        data=buffer.tobytes(),
                        file_name=f"{Path(uploaded_file.name).stem}_annotated.jpg",
                        mime="image/jpeg",
                        use_container_width=True
                    )
            
            # Success message
            st.success(f"✅ OCR completed successfully! Detected {len(filtered_detections)} text regions.")
    
    else:
        # Instructions when no file uploaded
        st.info("""
        ### 📖 How to Use
        
        1. **Upload an image** containing industrial or stenciled text
        2. **Configure settings** in the sidebar (optional)
        3. **Click "Run OCR"** to process the image
        4. **Review results** and download outputs
        
        ### 💡 Tips for Best Results
        
        - Use well-lit images with minimal shadows
        - Ensure text is in focus and readable
        - For angled shots, the system will auto-correct rotation
        - Lower confidence threshold if text is very faded
        - Enable preprocessing visualization to debug issues
        """)
        
        # Example use cases
        st.markdown("---")
        st.subheader("🎯 Ideal Use Cases")
        
        col_u1, col_u2, col_u3 = st.columns(3)
        
        with col_u1:
            st.markdown("""
            **Military Equipment**
            - Serial numbers
            - Batch codes
            - Stenciled markings
            """)
        
        with col_u2:
            st.markdown("""
            **Industrial Boxes**
            - Shipping labels
            - Part numbers
            - Weight/dimensions
            """)
        
        with col_u3:
            st.markdown("""
            **Warehouse Inventory**
            - SKU codes
            - Expiry dates
            - Location markers
            """)


if __name__ == "__main__":
    main()
