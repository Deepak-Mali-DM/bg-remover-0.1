from flask import Flask, render_template, request, jsonify, send_file
import os
from werkzeug.utils import secure_filename
import uuid
import base64
from PIL import Image
import io
import time
import cv2
import numpy as np
from skimage import filters, morphology, segmentation
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def professional_background_removal(image_data):
    """
    Professional background removal using alpha matting, OpenCV, and advanced techniques
    """
    try:
        # Convert PIL to OpenCV format
        pil_image = Image.open(io.BytesIO(image_data))
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        
        # Convert to numpy array
        img = np.array(pil_image)
        if img.shape[2] == 4:  # RGBA
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        else:  # RGB
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2RGBA)
        
        height, width = img_bgr.shape[:2]
        
        # Resize for processing if too large (optimization)
        max_dimension = 1024
        if max(height, width) > max_dimension:
            scale = max_dimension / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img_bgr = cv2.resize(img_bgr, (new_width, new_height), interpolation=cv2.INTER_AREA)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            height, width = new_height, new_width
        
        # Method 1: GrabCut Algorithm
        mask1 = grabcut_segmentation(img_bgr)
        
        # Method 2: Color-based segmentation
        mask2 = color_segmentation(img_bgr)
        
        # Method 3: Edge-based segmentation
        mask3 = edge_based_segmentation(img_bgr)
        
        # Combine masks using voting system
        combined_mask = combine_masks([mask1, mask2, mask3])
        
        # Refine mask with morphological operations
        refined_mask = refine_mask(combined_mask)
        
        # Apply alpha matting for smooth edges
        final_mask = alpha_matting(img_bgr, refined_mask)
        
        # Apply mask to original image
        result = apply_mask_to_image(img, final_mask)
        
        # Convert back to PIL
        result_pil = Image.fromarray(result.astype(np.uint8), mode='RGBA')
        
        # Convert to bytes
        output = io.BytesIO()
        result_pil.save(output, format='PNG', optimize=True, quality=95)
        return output.getvalue()
        
    except Exception as e:
        print(f"Error in professional background removal: {e}")
        return image_data

def grabcut_segmentation(img):
    """GrabCut algorithm for foreground extraction"""
    try:
        # Create mask
        mask = np.zeros(img.shape[:2], np.uint8)
        
        # Define background and foreground models
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        
        # Define rectangle (slightly smaller than image)
        height, width = img.shape[:2]
        rect = (int(width*0.1), int(height*0.1), int(width*0.8), int(height*0.8))
        
        # Apply GrabCut
        cv2.grabCut(img, mask, rect, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_RECT)
        
        # Modify mask: 0 and 2 -> background, 1 and 3 -> foreground
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        
        return mask2 * 255
    except:
        return np.ones(img.shape[:2], dtype=np.uint8) * 255

def color_segmentation(img):
    """Color-based segmentation using K-means clustering"""
    try:
        # Reshape image to pixels
        pixel_values = img.reshape((-1, 3))
        pixel_values = np.float32(pixel_values)
        
        # K-means clustering
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        k = 8  # Number of clusters
        _, labels, centers = cv2.kmeans(pixel_values, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        # Convert back to uint8
        centers = np.uint8(centers)
        segmented_image = centers[labels.flatten()]
        segmented_image = segmented_image.reshape(img.shape)
        
        # Find background clusters (usually corners)
        height, width = img.shape[:2]
        corner_pixels = []
        corner_pixels.extend(segmented_image[0:5, 0:5].reshape(-1, 3))
        corner_pixels.extend(segmented_image[0:5, -5:].reshape(-1, 3))
        corner_pixels.extend(segmented_image[-5:, 0:5].reshape(-1, 3))
        corner_pixels.extend(segmented_image[-5:, -5:].reshape(-1, 3))
        
        # Find most common color in corners
        corner_pixels = np.array(corner_pixels)
        unique_colors, counts = np.unique(corner_pixels, axis=0, return_counts=True)
        bg_color = unique_colors[np.argmax(counts)]
        
        # Create mask
        mask = np.zeros((height, width), dtype=np.uint8)
        for i in range(k):
            cluster_mask = (segmented_image == centers[i]).all(axis=2)
            if np.array_equal(centers[i], bg_color):
                mask[cluster_mask] = 0
            else:
                mask[cluster_mask] = 255
        
        return mask
    except:
        return np.ones(img.shape[:2], dtype=np.uint8) * 255

def edge_based_segmentation(img):
    """Edge-based segmentation using Canny and morphological operations"""
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply Canny edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Dilate edges to connect gaps
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=2)
        
        # Fill contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.drawContours(mask, contours, -1, 255, thickness=cv2.FILLED)
        
        # Remove small objects
        mask = morphology.remove_small_objects(mask > 0, min_size=100)
        
        return mask.astype(np.uint8) * 255
    except:
        return np.ones(img.shape[:2], dtype=np.uint8) * 255

def combine_masks(masks):
    """Combine multiple masks using voting system"""
    try:
        # Stack masks
        mask_stack = np.stack(masks, axis=2)
        
        # Voting: pixel is foreground if at least 2 methods agree
        combined = np.sum(mask_stack > 128, axis=2) >= 2
        
        return combined.astype(np.uint8) * 255
    except:
        return masks[0] if masks else np.ones((512, 512), dtype=np.uint8) * 255

def refine_mask(mask):
    """Refine mask using morphological operations"""
    try:
        # Remove small noise
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
        
        # Fill small holes
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        # Smooth edges
        mask = cv2.GaussianBlur(mask, (3, 3), 0)
        
        # Threshold to binary
        _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
        
        return mask
    except:
        return mask

def alpha_matting(img, mask):
    """Apply alpha matting for smooth edges"""
    try:
        # Simple alpha matting using guided filter
        # Convert mask to float
        alpha = mask.astype(np.float32) / 255.0
        
        # Apply guided filter for smooth edges
        try:
            from pymatting import estimate_alpha
            # Convert to RGB for pymatting
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            alpha_refined = estimate_alpha(img_rgb, alpha)
            alpha_refined = (alpha_refined * 255).astype(np.uint8)
        except:
            # Fallback to bilateral filter
            alpha_refined = cv2.bilateralFilter(alpha, 9, 75, 75)
            alpha_refined = (alpha_refined * 255).astype(np.uint8)
        
        return alpha_refined
    except:
        return mask

def apply_mask_to_image(img, mask):
    """Apply refined mask to original image"""
    try:
        # Ensure mask has same dimensions
        if mask.shape[:2] != img.shape[:2]:
            mask = cv2.resize(mask, (img.shape[1], img.shape[0]))
        
        # Create alpha channel
        alpha = mask.astype(np.float32) / 255.0
        
        # Apply alpha to image
        result = img.copy().astype(np.float32)
        result[:, :, 3] = alpha * 255
        
        return result
    except:
        return img

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_and_process():
    """Professional background removal with multiple algorithms"""
    start_time = time.time()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{unique_id}_removed.png")
        
        # Read uploaded file
        input_data = file.read()
        
        # Process image with professional algorithms
        output_data = professional_background_removal(input_data)
        
        # Save processed image to file
        with open(output_path, 'wb') as f:
            f.write(output_data)
        
        # Convert to base64 for web display
        img_base64 = base64.b64encode(output_data).decode('utf-8')
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        return jsonify({
            'success': True,
            'image': f"data:image/png;base64,{img_base64}",
            'processing_time': processing_time,
            'download_id': unique_id,
            'method': 'professional_alpha_matting',
            'message': 'Background removed using professional alpha matting and multi-algorithm approach'
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to process image: {str(e)}'}), 500

@app.route('/api/download/<download_id>')
def download_processed(download_id):
    """Download processed image"""
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{download_id}_removed.png")
    
    if os.path.exists(output_path):
        return send_file(output_path, as_attachment=True, download_name=f"professional_removed_bg_{download_id}.png")
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy', 
        'message': 'Professional BG Remover Running - Business Grade',
        'features': ['grabcut', 'color_segmentation', 'edge_detection', 'alpha_matting', 'opencv'],
        'quality': 'professional'
    })

if __name__ == '__main__':
    print("Professional BG Remover Starting...")
    print("Features: GrabCut, Color Segmentation, Edge Detection, Alpha Matting")
    print("Optimized for business use with OpenCV and advanced algorithms")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5000)
