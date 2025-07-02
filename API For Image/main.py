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
