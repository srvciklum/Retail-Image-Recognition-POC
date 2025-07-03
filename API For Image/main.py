from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from models import Planogram, PlanogramCreate, ComplianceResult, Product, ProductCreate
from planogram_service import PlanogramService
from product_service import ProductService
from ultralytics import YOLO
import easyocr
import cv2
import uuid
import os
import numpy as np
import logging
from typing import List
import traceback

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Allow React frontend to access this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify ["http://localhost:3000"] for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory to save processed images
OUTPUT_DIR = "saved_images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Serve saved images as static files
app.mount("/images", StaticFiles(directory=OUTPUT_DIR), name="images")

# Initialize services
model = YOLO("best.pt")
reader = easyocr.Reader(['en'])
planogram_service = PlanogramService()
product_service = ProductService()

# Product management endpoints
@app.post("/products", response_model=Product)
async def create_product(product: ProductCreate):
    try:
        return product_service.create_product(product)
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    product = product_service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.get("/products", response_model=List[Product])
async def list_products():
    return product_service.list_products()

@app.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, product: Product):
    if product_id != product.id:
        raise HTTPException(status_code=400, detail="Product ID mismatch")
    updated = product_service.update_product(product)
    if not updated:
        raise HTTPException(status_code=404, detail="Product not found")
    return updated

@app.delete("/products/{product_id}")
async def delete_product(product_id: str):
    if not product_service.delete_product(product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}

@app.get("/products/search/{query}", response_model=List[Product])
async def search_products(query: str):
    return product_service.search_products(query)

# Planogram management endpoints
@app.post("/planograms", response_model=Planogram)
async def create_planogram(planogram: PlanogramCreate):
    try:
        return planogram_service.create_planogram(planogram)
    except Exception as e:
        logger.error(f"Error creating planogram: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/planograms/{planogram_id}", response_model=Planogram)
async def get_planogram(planogram_id: str):
    planogram = planogram_service.get_planogram(planogram_id)
    if not planogram:
        raise HTTPException(status_code=404, detail="Planogram not found")
    return planogram

@app.get("/planograms", response_model=List[Planogram])
async def list_planograms():
    return planogram_service.list_planograms()

@app.put("/planograms/{planogram_id}", response_model=Planogram)
async def update_planogram(planogram_id: str, planogram: PlanogramCreate):
    try:
        logger.debug(f"Updating planogram {planogram_id} with data: {planogram.dict()}")
        updated = planogram_service.update_planogram(planogram_id, planogram)
        if not updated:
            logger.error(f"Failed to save planogram {planogram_id}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save planogram {planogram_id}"
            )
        return updated
    except Exception as e:
        logger.error(f"Error handling planogram {planogram_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while handling planogram: {str(e)}"
        )

@app.delete("/planograms/{planogram_id}")
async def delete_planogram(planogram_id: str):
    if not planogram_service.delete_planogram(planogram_id):
        raise HTTPException(status_code=404, detail="Planogram not found")
    return {"message": "Planogram deleted successfully"}

def detect_shelf_layout(image_path: str):
    """Detect shelf layout dynamically and assign row/column coordinates to detected products"""
    image = cv2.imread(image_path)
    height, width, _ = image.shape
    
    # Use the same dynamic grid detection logic as /detect-grid endpoint
    def detect_dynamic_grid(img):
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        # Look for horizontal lines (shelf separators)
        h_kernel_size = max(20, width // 15)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_size, 1))
        horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
        
        h_contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        shelf_separators = []
        
        for contour in h_contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            if w > width * 0.4 and area > width * 0.3:
                shelf_separators.append(y + h // 2)
        
        # Look for vertical lines (product separators)  
        v_kernel_size = max(15, height // 20)
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kernel_size))
        vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
        
        v_contours, _ = cv2.findContours(vertical_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        product_separators = []
        
        for contour in v_contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            if h > height * 0.25 and area > height * 0.15:
                product_separators.append(x + w // 2)
        
        # Filter close lines
        def filter_close_lines(lines, min_distance):
            if not lines:
                return []
            filtered = [lines[0]]
            for line in sorted(lines)[1:]:
                if line - filtered[-1] >= min_distance:
                    filtered.append(line)
            return filtered
        
        shelf_separators = filter_close_lines(shelf_separators, height * 0.15)
        product_separators = filter_close_lines(product_separators, width * 0.08)
        
        # Create grid lines
        h_lines = [0] + shelf_separators + [height]
        v_lines = [0] + product_separators + [width]
        
        h_lines = sorted(set(h_lines))
        v_lines = sorted(set(v_lines))
        
        rows = len(h_lines) - 1
        cols = len(v_lines) - 1
        
        # Validation and fallback
        if (rows > 6 or cols > 8 or rows < 1 or cols < 1 or 
            (rows == 1 and cols <= 2) or  # Single row with <=2 cols is unrealistic
            (cols == 1 and rows <= 2)):   # Single column with <=2 rows is unrealistic
            raise ValueError("Grid detection failed validation")
            
        return rows, cols, h_lines, v_lines
    
    # Try dynamic detection first
    try:
        num_rows, num_cols, h_lines, v_lines = detect_dynamic_grid(image)
        logger.debug(f"Dynamic grid detection in analyze: {num_rows} rows x {num_cols} columns")
    except Exception as e:
        logger.warning(f"Dynamic grid detection failed in analyze: {e}, using intelligent fallback")
        
        # Intelligent fallback based on image characteristics
        aspect_ratio = width / height
        
        if aspect_ratio > 2.5:  # Very wide - likely single shelf
            num_rows = 1
            num_cols = min(6, max(3, int(width / 150)))
        elif aspect_ratio > 1.8:  # Wide - likely 2 shelves  
            num_rows = 2
            num_cols = min(6, max(3, int(width / 120)))
        elif aspect_ratio > 1.2:  # Moderate - likely 2-3 shelves
            num_rows = 2 if height < 500 else 3
            num_cols = min(5, max(3, int(width / 100)))
        elif aspect_ratio > 0.8:  # Square - likely 3 shelves
            num_rows = 3
            num_cols = min(4, max(2, int(width / 150)))
        else:  # Tall - likely 3-4 shelves
            num_rows = min(4, max(3, int(height / 150)))
            num_cols = min(3, max(2, int(width / 200)))
        
        logger.debug(f"Fallback grid in analyze: {num_rows} rows x {num_cols} columns")
        
        # Create evenly spaced grid lines
        h_lines = [int(i * height / num_rows) for i in range(num_rows + 1)]
        v_lines = [int(i * width / num_cols) for i in range(num_cols + 1)]
    
    # Calculate grid cell dimensions
    row_heights = [h_lines[i+1] - h_lines[i] for i in range(num_rows)]
    col_widths = [v_lines[i+1] - v_lines[i] for i in range(num_cols)]
    
    def assign_coordinates(box):
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        center_y = (y1 + y2) // 2
        center_x = (x1 + x2) // 2
        
        # Assign row based on vertical position
        row = 0
        for i, h_line in enumerate(h_lines[1:]):
            if center_y <= h_line:
                row = i
                break
        else:
            row = num_rows - 1
            
        # Assign column based on horizontal position
        column = 0
        for i, v_line in enumerate(v_lines[1:]):
            if center_x <= v_line:
                column = i
                break
        else:
            column = num_cols - 1
            
        # Ensure bounds
        row = max(0, min(num_rows - 1, row))
        column = max(0, min(num_cols - 1, column))
        
        return row, column

    return assign_coordinates

@app.post("/analyze")
async def analyze_image(
    image: UploadFile = File(...),
    planogram_id: str = Form(None)
):
    logger.debug(f"Analyzing image with planogram_id: {planogram_id}")
    
    # Save uploaded image with a unique filename
    image_bytes = await image.read()
    image_id = str(uuid.uuid4())
    input_path = os.path.join(OUTPUT_DIR, f"input_{image_id}.jpg")
    with open(input_path, "wb") as f:
        f.write(image_bytes)

    logger.debug(f"Saved input image to: {input_path}")

    # Read original image
    image = cv2.imread(input_path)
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image file.")
    
    original_height, original_width, _ = image.shape
    logger.debug(f"Original image dimensions: {original_width}x{original_height}")

    # Normalize image size while maintaining aspect ratio
    TARGET_WIDTH = 600  # Standard width we'll use for processing
    aspect_ratio = original_width / original_height
    normalized_width = TARGET_WIDTH
    normalized_height = int(TARGET_WIDTH / aspect_ratio)
    
    # Ensure height is reasonable (not too small or large)
    MIN_HEIGHT = 400
    MAX_HEIGHT = 1200
    if normalized_height < MIN_HEIGHT:
        normalized_height = MIN_HEIGHT
        normalized_width = int(MIN_HEIGHT * aspect_ratio)
    elif normalized_height > MAX_HEIGHT:
        normalized_height = MAX_HEIGHT
        normalized_width = int(MAX_HEIGHT * aspect_ratio)
    
    # Resize image to normalized dimensions
    normalized_image = cv2.resize(image, (normalized_width, normalized_height), interpolation=cv2.INTER_AREA)
    logger.debug(f"Normalized image dimensions: {normalized_width}x{normalized_height}")

    # Save normalized image for debugging
    normalized_path = os.path.join(OUTPUT_DIR, f"normalized_{image_id}.jpg")
    cv2.imwrite(normalized_path, normalized_image)
    logger.debug(f"Saved normalized image to: {normalized_path}")

    # Run YOLO on the normalized image
    results = model.predict(source=normalized_path, show=False, save=False, conf=0.1, line_width=2)

    # Get coordinate assignment function based on normalized image
    assign_coordinates = detect_shelf_layout(normalized_path)

    # Process detection results
    detected_products = []
    counts = {}
    empty_shelf_items = []
    boxes = results[0].boxes
    names = model.names
    empty_shelf_boxes = []

    # Scale factor to convert normalized coordinates back to original image size
    scale_x = original_width / normalized_width
    scale_y = original_height / normalized_height

    # Process each detected object
    for box in boxes:
        cls = int(box.cls[0])
        label = names[cls]
        
        # Get coordinates in normalized space
        row, column = assign_coordinates(box)
        
        logger.debug(f"Detected {label} at row {row}, column {column}")
        
        # Add to counts
        counts[label] = counts.get(label, 0) + 1
        
        # Add to detected products with coordinates
        detected_products.append({
            "label": label,
            "row": row,
            "column": column,
            "quantity": 1  # Basic quantity detection
        })

        if label.lower() in ['empty_shelf', 'empty', 'empty_space', 'emptyspace']:
            empty_shelf_boxes.append((box, row, column))

    logger.debug(f"Total detected products: {len(detected_products)}")
    logger.debug(f"Product counts: {counts}")

    # Process empty shelf areas
    for box, row, column in empty_shelf_boxes:
        # Get coordinates in normalized space
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        
        # Extract ROI from normalized image
        roi = normalized_image[y2:min(y2 + 120, normalized_height), x1:x2]
        
        ocr_result = reader.readtext(roi)
        
        found = False
        for _, text, conf in ocr_result:
            if conf > 0.7:
                cleaned = text.strip().title()
                empty_shelf_items.append({
                    "item": cleaned,
                    "row": row,
                    "column": column
                })
                found = True
                break
        
        if not found:
            empty_shelf_items.append({
                "item": "Unknown Item",
                "row": row,
                "column": column
            })

    # Save processed image with overlays
    # Draw on normalized image first
    output_normalized_path = os.path.join(OUTPUT_DIR, f"output_normalized_{image_id}.jpg")
    results[0].save(filename=output_normalized_path)
    
    # Read the output image and scale it back to original size
    output_normalized = cv2.imread(output_normalized_path)
    output_original = cv2.resize(output_normalized, (original_width, original_height), interpolation=cv2.INTER_LANCZOS4)
    
    # Save the final output at original size
    output_path = os.path.join(OUTPUT_DIR, f"output_{image_id}.jpg")
    cv2.imwrite(output_path, output_original)

    # Check planogram compliance if planogram_id is provided
    compliance_result = None
    if planogram_id:
        logger.debug(f"Loading planogram: {planogram_id}")
        planogram = planogram_service.get_planogram(planogram_id)
        if planogram:
            logger.debug(f"Found planogram: {planogram.dict()}")
            try:
                compliance_result = planogram_service.check_compliance(planogram, detected_products)
                logger.debug(f"Compliance check completed: {compliance_result.dict() if compliance_result else None}")
            except Exception as e:
                logger.error(f"Error during compliance check: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.error(f"Planogram not found: {planogram_id}")
            logger.debug(f"Available planograms: {os.listdir(planogram_service.storage_dir)}")

    response_data = {
        "saved_image_path": f"images/output_{image_id}.jpg",
        "detected_counts": counts,
        "empty_shelf_items": [item["item"] for item in empty_shelf_items],
        "detected_products": detected_products,
        "compliance_result": compliance_result.dict() if compliance_result else None,
        "debug_images": {
            "normalized": f"images/normalized_{image_id}.jpg",
            "output_normalized": f"images/output_normalized_{image_id}.jpg"
        },
        "image_info": {
            "original_width": original_width,
            "original_height": original_height,
            "normalized_width": normalized_width,
            "normalized_height": normalized_height,
            "aspect_ratio": round(original_width / original_height, 2)
        }
    }
    
    logger.debug(f"Sending response: {response_data}")
    return response_data

@app.post("/detect-grid")
async def detect_grid(image: UploadFile = File(...)):
    """
    Detect the number of rows and columns in a shelf image.
    Returns the grid dimensions and optionally the processed image with grid overlay.
    """
    try:
        # Validate the uploaded file
        logger.debug(f"Received file: {image.filename}, content_type: {image.content_type}, size: {image.size}")
        
        if not image.filename:
            raise HTTPException(status_code=400, detail="No file uploaded")
        
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read and validate image data
        image_bytes = await image.read()
        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        logger.debug(f"Successfully read {len(image_bytes)} bytes from uploaded file")
        
        # Save uploaded image with a unique filename
        image_id = str(uuid.uuid4())
        input_path = os.path.join(OUTPUT_DIR, f"grid_input_{image_id}.jpg")
        with open(input_path, "wb") as f:
            f.write(image_bytes)

        logger.debug(f"Saved grid detection input image to: {input_path}")

        # Read image
        img = cv2.imread(input_path)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file.")
        
        original_height, original_width, _ = img.shape
        logger.debug(f"Original image dimensions: {original_width}x{original_height}")

        # Normalize image size while maintaining aspect ratio
        TARGET_WIDTH = 600  # Standard width we'll use for processing
        aspect_ratio = original_width / original_height
        normalized_width = TARGET_WIDTH
        normalized_height = int(TARGET_WIDTH / aspect_ratio)
        
        # Ensure height is reasonable (not too small or large)
        MIN_HEIGHT = 400
        MAX_HEIGHT = 1200
        if normalized_height < MIN_HEIGHT:
            normalized_height = MIN_HEIGHT
            normalized_width = int(MIN_HEIGHT * aspect_ratio)
        elif normalized_height > MAX_HEIGHT:
            normalized_height = MAX_HEIGHT
            normalized_width = int(MAX_HEIGHT * aspect_ratio)
        
        # Resize image to normalized dimensions
        img = cv2.resize(img, (normalized_width, normalized_height), interpolation=cv2.INTER_AREA)
        logger.debug(f"Normalized image dimensions: {normalized_width}x{normalized_height}")

        # Save normalized image for debugging
        normalized_path = os.path.join(OUTPUT_DIR, f"normalized_{image_id}.jpg")
        cv2.imwrite(normalized_path, img)
        logger.debug(f"Saved normalized image to: {normalized_path}")

        height, width, _ = img.shape

        # Conservative shelf detection focused on retail environments
        def detect_grid_structure(image):
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Very conservative approach - only look for strong, obvious shelf separators
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # Use only one moderate edge detection
            edges = cv2.Canny(blurred, 50, 150)
            
            # Save debug image
            debug_path = os.path.join(OUTPUT_DIR, f"debug_edges_{image_id}.jpg")
            cv2.imwrite(debug_path, edges)
            logger.debug(f"Saved edge detection debug image to: {debug_path}")
            
            # Look for strong horizontal lines only (shelf separators)
            # Use conservative kernel size based on normalized dimensions
            h_kernel_size = max(20, width // 15)  # Conservative horizontal line detection
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_size, 1))
            horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
            
            # Find horizontal line contours with strict criteria
            h_contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            shelf_separators = []
            
            for contour in h_contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                
                # Very strict criteria for shelf separators
                # Must span at least 40% of width and have significant area
                if w > width * 0.4 and area > width * 0.3:
                    shelf_separators.append(y + h // 2)
                    logger.debug(f"Found strong horizontal line at y={y + h // 2}, width={w}, area={area}")
            
            # Look for vertical lines (product separators) with relaxed criteria
            v_kernel_size = max(15, height // 20)
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kernel_size))
            vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
            
            v_contours, _ = cv2.findContours(vertical_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            product_separators = []
            
            for contour in v_contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                
                # More lenient criteria for product separators
                if h > height * 0.25 and area > height * 0.15:
                    product_separators.append(x + w // 2)
                    logger.debug(f"Found vertical line at x={x + w // 2}, height={h}, area={area}")
            
            logger.debug(f"Strong shelf separators found: {len(shelf_separators)}")
            logger.debug(f"Product separators found: {len(product_separators)}")
            
            # Remove duplicates and sort
            shelf_separators = sorted(set(shelf_separators))
            product_separators = sorted(set(product_separators))
            
            # Filter out lines that are too close together
            def filter_close_lines(lines, min_distance):
                if not lines:
                    return []
                
                filtered = [lines[0]]
                for line in lines[1:]:
                    if line - filtered[-1] >= min_distance:
                        filtered.append(line)
                return filtered
            
            # Filter shelf separators (minimum 15% of height apart)
            shelf_separators = filter_close_lines(shelf_separators, height * 0.15)
            
            # Filter product separators (minimum 8% of width apart)
            product_separators = filter_close_lines(product_separators, width * 0.08)
            
            logger.debug(f"Filtered shelf separators: {shelf_separators}")
            logger.debug(f"Filtered product separators: {product_separators}")
            
            # Create final grid lines
            h_lines = [0] + shelf_separators + [height]
            v_lines = [0] + product_separators + [width]
            
            # Remove duplicates and sort
            h_lines = sorted(set(h_lines))
            v_lines = sorted(set(v_lines))
            
            rows = len(h_lines) - 1
            cols = len(v_lines) - 1
            
            logger.debug(f"Final conservative grid: {rows} rows x {cols} columns")
            logger.debug(f"H lines: {h_lines}")
            logger.debug(f"V lines: {v_lines}")
            
            # Additional validation - if we detect too many rows, it's likely noise
            if rows > 6:  # More than 6 rows is unlikely for retail shelves
                logger.warning(f"Detected {rows} rows, likely noise. Using fallback.")
                raise ValueError("Too many rows detected, likely false positives")
            
            return max(1, rows), max(1, cols), h_lines, v_lines

        # Try intelligent grid detection first
        detection_method = "computer_vision"
        try:
            num_rows, num_cols, h_lines, v_lines = detect_grid_structure(img)
            logger.debug(f"Computer vision detection result: {num_rows} rows, {num_cols} columns")
            
            # Validate the detection results with reasonable bounds
            if (num_rows < 1 or num_rows > 6 or num_cols < 1 or num_cols > 8 or 
                (num_rows == 1 and num_cols <= 2) or  # Single row with <=2 cols is unrealistic
                (num_cols == 1 and num_rows <= 2)):   # Single column with <=2 rows is unrealistic
                logger.warning(f"Detected grid ({num_rows}x{num_cols}) outside reasonable bounds or unrealistic, using fallback")
                raise ValueError("Grid detection outside reasonable bounds or unrealistic")
                
        except Exception as e:
            logger.warning(f"Computer vision detection failed: {e}, using intelligent fallback")
            detection_method = "intelligent_fallback"
            
            # Intelligent fallback based on image characteristics
            aspect_ratio = width / height
            logger.debug(f"Image aspect ratio: {aspect_ratio:.2f}")
            
            if aspect_ratio > 2.5:  # Very wide - likely single shelf
                num_rows = 1
                num_cols = min(6, max(3, int(width / 150)))
            elif aspect_ratio > 1.8:  # Wide - likely 2 shelves  
                num_rows = 2
                num_cols = min(6, max(3, int(width / 120)))
            elif aspect_ratio > 1.2:  # Moderate - likely 2-3 shelves
                num_rows = 2 if height < 500 else 3
                num_cols = min(5, max(3, int(width / 100)))
            elif aspect_ratio > 0.8:  # Square - likely 3 shelves
                num_rows = 3
                num_cols = min(4, max(2, int(width / 150)))
            else:  # Tall - likely 3-4 shelves
                num_rows = min(4, max(3, int(height / 150)))
                num_cols = min(3, max(2, int(width / 200)))
            
            logger.debug(f"Intelligent fallback result: {num_rows} rows x {num_cols} columns")
            
            # Create evenly spaced grid lines
            h_lines = [int(i * height / num_rows) for i in range(num_rows + 1)]
            v_lines = [int(i * width / num_cols) for i in range(num_cols + 1)]

        # Create debug visualization showing detected lines
        debug_lines_img = img.copy()
        
        # Draw detected grid lines in different colors
        for i, y in enumerate(h_lines):
            color = (0, 255, 0) if i == 0 or i == len(h_lines)-1 else (0, 200, 255)  # Green for boundaries, orange for detected
            cv2.line(debug_lines_img, (0, y), (width, y), color, 2)
            # Add text label
            cv2.putText(debug_lines_img, f"H{i}", (10, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        for i, x in enumerate(v_lines):
            color = (0, 255, 0) if i == 0 or i == len(v_lines)-1 else (255, 100, 0)  # Green for boundaries, blue for detected  
            cv2.line(debug_lines_img, (x, 0), (x, height), color, 2)
            # Add text label
            cv2.putText(debug_lines_img, f"V{i}", (x+5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Save debug image
        debug_lines_path = os.path.join(OUTPUT_DIR, f"debug_lines_{image_id}.jpg")
        cv2.imwrite(debug_lines_path, debug_lines_img)
        logger.debug(f"Saved line detection debug image to: {debug_lines_path}")
        
        # Create final visualization with detected grid
        grid_img = img.copy()
        
        # Draw final grid lines in green
        for y in h_lines:
            cv2.line(grid_img, (0, y), (width, y), (0, 255, 0), 2)
        for x in v_lines:
            cv2.line(grid_img, (x, 0), (x, height), (0, 255, 0), 2)
        
        # Add grid cell numbers
        for row in range(num_rows):
            for col in range(num_cols):
                y1, y2 = h_lines[row], h_lines[row + 1]
                x1, x2 = v_lines[col], v_lines[col + 1]
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                
                # Add semi-transparent overlay
                overlay = grid_img.copy()
                cv2.rectangle(overlay, (x1 + 2, y1 + 2), (x2 - 2, y2 - 2), (255, 255, 255), -1)
                grid_img = cv2.addWeighted(grid_img, 0.9, overlay, 0.1, 0)
                
                # Add text
                text = f"R{row+1}C{col+1}"
                font_scale = min(0.6, (x2 - x1) / 100)
                cv2.putText(grid_img, text, (center_x - 25, center_y + 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1)

        # Save the grid detection result
        output_path = os.path.join(OUTPUT_DIR, f"grid_detection_{image_id}.jpg")
        cv2.imwrite(output_path, grid_img)
        logger.debug(f"Saved grid detection result to: {output_path}")

        # Calculate cell coordinates for overlay
        # Scale the coordinates back to original image size
        scale_x = original_width / width
        scale_y = original_height / height
        cells = []
        for row in range(num_rows):
            for col in range(num_cols):
                y1, y2 = h_lines[row], h_lines[row + 1]
                x1, x2 = v_lines[col], v_lines[col + 1]
                # Scale coordinates back to original image size
                cells.append({
                    "row": row,
                    "column": col,
                    "bbox": [
                        int(x1 * scale_x), 
                        int(y1 * scale_y), 
                        int(x2 * scale_x), 
                        int(y2 * scale_y)
                    ]
                })

        response = {
            "grid_dimensions": {
                "rows": num_rows,
                "columns": num_cols
            },
            "cells": cells,
            "detection_image": f"images/grid_detection_{image_id}.jpg",
            "debug_images": {
                "normalized": f"images/normalized_{image_id}.jpg",
                "edges": f"images/debug_edges_{image_id}.jpg",
                "lines": f"images/debug_lines_{image_id}.jpg"
            },
            "detection_method": detection_method,
            "image_info": {
                "original_width": original_width,
                "original_height": original_height,
                "normalized_width": width,
                "normalized_height": height,
                "aspect_ratio": round(width / height, 2)
            },
            "success": True,
            "message": f"Successfully detected {num_rows}×{num_cols} grid using {detection_method.replace('_', ' ')}"
        }
        
        logger.debug(f"Grid detection response: {response}")
        return response

    except HTTPException as he:
        # Re-raise HTTP exceptions (validation errors, etc.)
        raise he
    except Exception as e:
        logger.error(f"Error in grid detection: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Grid detection failed: {str(e)}")

# Simple test endpoint for file upload debugging
@app.post("/test-upload")
async def test_upload(file: UploadFile = File(...)):
    """Simple endpoint to test file upload functionality"""
    try:
        logger.debug(f"Test upload - filename: {file.filename}, content_type: {file.content_type}, size: {file.size}")
        content = await file.read()
        logger.debug(f"Test upload - read {len(content)} bytes")
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Test upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
