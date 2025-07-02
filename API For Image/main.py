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
    """Detect shelf layout and assign row/column coordinates to detected products"""
    image = cv2.imread(image_path)
    height, width, _ = image.shape
    
    # Simple shelf detection - divide image into rows
    # In a real implementation, this would use more sophisticated shelf detection
    num_rows = 3  # Assuming 3 shelves
    row_height = height // num_rows
    
    def assign_coordinates(box):
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        center_y = (y1 + y2) // 2
        center_x = (x1 + x2) // 2
        
        # Assign row based on vertical position (0-based)
        row = center_y // row_height
        
        # Assign column based on horizontal position (divide width into 6 sections)
        num_cols = 6
        col_width = width // num_cols
        column = center_x // col_width
        
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

    # Run YOLO on the image
    results = model.predict(source=input_path, show=False, save=False, conf=0.1, line_width=2)
    image = cv2.imread(input_path)
    height, width, _ = image.shape

    # Get coordinate assignment function
    assign_coordinates = detect_shelf_layout(input_path)

    # Process detection results
    detected_products = []
    counts = {}
    empty_shelf_items = []
    boxes = results[0].boxes
    names = model.names
    empty_shelf_boxes = []

    # Process each detected object
    for box in boxes:
        cls = int(box.cls[0])
        label = names[cls]
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
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        roi = image[y2:min(y2 + 120, height), x1:x2]
        
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
    output_path = os.path.join(OUTPUT_DIR, f"output_{image_id}.jpg")
    results[0].save(filename=output_path)

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
        "compliance_result": compliance_result.dict() if compliance_result else None
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
        
        height, width, _ = img.shape
        logger.debug(f"Image dimensions: {width}x{height}")

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
            # Use conservative kernel size
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
            v_kernel_size = max(15, height // 20)  # Conservative vertical line detection
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

        # Try advanced detection first
        detection_method = "computer_vision"
        try:
            num_rows, num_cols, h_lines, v_lines = detect_grid_structure(img)
            logger.debug(f"Advanced detection result: {num_rows} rows, {num_cols} columns")
            
            # Validate detected grid with more intelligent bounds checking
            valid_detection = True
            
            # Check if grid is reasonable for retail shelves
            if num_rows < 1 or num_rows > 8:
                logger.warning(f"Detected rows ({num_rows}) outside reasonable bounds (1-8)")
                valid_detection = False
            
            if num_cols < 1 or num_cols > 12:
                logger.warning(f"Detected columns ({num_cols}) outside reasonable bounds (1-12)")
                valid_detection = False
            
            # Check if the grid cells would be too small or too large
            avg_cell_height = height / num_rows if num_rows > 0 else 0
            avg_cell_width = width / num_cols if num_cols > 0 else 0
            
            if avg_cell_height < 30:  # Too small - likely over-segmented
                logger.warning(f"Average cell height ({avg_cell_height:.1f}px) too small, likely over-segmented")
                valid_detection = False
            
            if avg_cell_width < 40:  # Too small - likely over-segmented
                logger.warning(f"Average cell width ({avg_cell_width:.1f}px) too small, likely over-segmented")
                valid_detection = False
            
            if avg_cell_height > height * 0.8:  # Too large - likely under-segmented
                logger.warning(f"Average cell height ({avg_cell_height:.1f}px) too large, likely under-segmented")
                valid_detection = False
            
            if avg_cell_width > width * 0.7:  # Too large - likely under-segmented
                logger.warning(f"Average cell width ({avg_cell_width:.1f}px) too large, likely under-segmented")
                valid_detection = False
            
            # If detection seems invalid, force fallback
            if not valid_detection:
                raise ValueError("Detected grid failed validation checks")
                
        except Exception as e:
            logger.warning(f"Advanced grid detection failed: {e}, falling back to intelligent heuristic")
            detection_method = "heuristic_fallback"
            # Very conservative fallback for retail shelf characteristics
            aspect_ratio = width / height
            
            logger.debug(f"Image aspect ratio: {aspect_ratio:.2f}")
            
            # Be extremely conservative - default to common scenarios
            if aspect_ratio > 3.0:  # Very wide image, likely single row shelf
                num_rows = 1 
                num_cols = max(2, min(6, int(aspect_ratio)))
                logger.debug(f"Very wide image detected, assuming single row with {num_cols} columns")
            elif aspect_ratio > 2.0:  # Wide shelf display - typical 2-shelf scenario
                num_rows = 2  # Conservative: assume 2 shelves for wide images
                num_cols = max(2, min(4, int(width / 150)))  # Conservative column estimate
                logger.debug(f"Wide shelf detected (2-shelf scenario): {num_rows} rows x {num_cols} columns")
            elif aspect_ratio > 1.5:  # Moderately wide - still likely 2-3 shelves
                if height < 400:  # Smaller image, be very conservative
                    num_rows = 2
                    num_cols = 2
                else:
                    num_rows = 2  # Default to 2 for this range
                    num_cols = 3
                logger.debug(f"Moderate width detected: {num_rows} rows x {num_cols} columns")
            elif aspect_ratio > 1.0:  # Standard shelf view
                # Default to 3 rows only for more square images
                num_rows = 3
                num_cols = max(2, min(4, int(width / 120)))
                logger.debug(f"Standard shelf detected: {num_rows} rows x {num_cols} columns")
            elif aspect_ratio > 0.7:  # Square-ish, could be 3-4 shelves
                num_rows = 3
                num_cols = 2
                logger.debug(f"Square shelf detected: {num_rows} rows x {num_cols} columns")
            else:  # Tall image, likely multiple vertical shelves
                num_rows = 4
                num_cols = 2
                logger.debug(f"Tall shelf detected: {num_rows} rows x {num_cols} columns")
            
            # Final conservative limits - much more restrictive
            num_rows = max(1, min(5, num_rows))  # Max 5 rows instead of 8
            num_cols = max(1, min(6, num_cols))  # Max 6 columns instead of 12
            
            logger.debug(f"Final heuristic result: {num_rows} rows x {num_cols} columns")
            
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
        cells = []
        for row in range(num_rows):
            for col in range(num_cols):
                y1, y2 = h_lines[row], h_lines[row + 1]
                x1, x2 = v_lines[col], v_lines[col + 1]
                cells.append({
                    "row": row,
                    "column": col,
                    "bbox": [int(x1), int(y1), int(x2), int(y2)]
                })

        response = {
            "grid_dimensions": {
                "rows": num_rows,
                "columns": num_cols
            },
            "cells": cells,
            "detection_image": f"images/grid_detection_{image_id}.jpg",
            "debug_images": {
                "edges": f"images/debug_edges_{image_id}.jpg",
                "lines": f"images/debug_lines_{image_id}.jpg"
            },
            "detection_method": detection_method,
            "image_info": {
                "width": width,
                "height": height,
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
