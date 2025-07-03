from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
import uuid
import os
import cv2
import numpy as np
import logging
from ...models.domain import (
    Product, ProductCreate, Planogram, PlanogramCreate,
    AnalysisResponse, GridDetectionResponse, ImageInfo
)
from ...services.product import ProductService
from ...services.planogram import PlanogramService
from ...services.image import ImageService
from ...config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency injection
def get_product_service() -> ProductService:
    return ProductService()

def get_planogram_service() -> PlanogramService:
    return PlanogramService()

def get_image_service() -> ImageService:
    return ImageService()

# Product management endpoints
@router.post("/products", response_model=Product)
async def create_product(
    product: ProductCreate,
    service: ProductService = Depends(get_product_service)
):
    try:
        return service.create_from_product_create(product)
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/products", response_model=List[Product])
async def list_products(service: ProductService = Depends(get_product_service)):
    return service.list()

@router.get("/products/search/{query}", response_model=List[Product])
async def search_products(
    query: str,
    service: ProductService = Depends(get_product_service)
):
    return service.search_products(query)

# Planogram management endpoints
@router.post("/planograms", response_model=Planogram)
async def create_planogram(
    planogram: PlanogramCreate,
    service: PlanogramService = Depends(get_planogram_service)
):
    try:
        return service.create_from_planogram_create(planogram)
    except Exception as e:
        logger.error(f"Error creating planogram: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/planograms", response_model=List[Planogram])
async def list_planograms(service: PlanogramService = Depends(get_planogram_service)):
    return service.list()

# Image analysis endpoints
@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_image(
    image: UploadFile = File(...),
    planogram_id: str = Form(None),
    image_service: ImageService = Depends(get_image_service),
    planogram_service: PlanogramService = Depends(get_planogram_service)
):
    logger.debug(f"Analyzing image with planogram_id: {planogram_id}")
    
    try:
        # Save uploaded image
        image_bytes = await image.read()
        image_id = str(uuid.uuid4())
        input_path = os.path.join(settings.OUTPUT_DIR, f"input_{image_id}.jpg")
        with open(input_path, "wb") as f:
            f.write(image_bytes)
        
        # Read and normalize image
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file.")
        
        original_height, original_width = image.shape[:2]
        normalized_image, normalized_width, normalized_height = image_service.normalize_image(image)
        
        # Save normalized image
        normalized_path = os.path.join(settings.OUTPUT_DIR, f"normalized_{image_id}.jpg")
        cv2.imwrite(normalized_path, normalized_image)
        
        # Detect grid
        try:
            grid_info = image_service.detect_grid(normalized_image)
        except ValueError as e:
            logger.warning(f"Grid detection failed: {e}, using fallback")
            aspect_ratio = normalized_width / normalized_height
            
            # Fallback grid detection based on aspect ratio
            if aspect_ratio > 2.5:
                rows, cols = 1, min(6, max(3, int(normalized_width / 150)))
            elif aspect_ratio > 1.8:
                rows, cols = 2, min(6, max(3, int(normalized_width / 120)))
            elif aspect_ratio > 1.2:
                rows, cols = 2 if normalized_height < 500 else 3, min(5, max(3, int(normalized_width / 100)))
            elif aspect_ratio > 0.8:
                rows, cols = 3, min(4, max(2, int(normalized_width / 150)))
            else:
                rows, cols = min(4, max(3, int(normalized_height / 150))), min(3, max(2, int(normalized_width / 200)))
            
            h_lines = [int(i * normalized_height / rows) for i in range(rows + 1)]
            v_lines = [int(i * normalized_width / cols) for i in range(cols + 1)]
            grid_info = (GridDimensions(rows=rows, columns=cols), h_lines, v_lines)
        
        # Detect products
        detected_products, counts, empty_shelf_items = image_service.detect_products(normalized_path, grid_info)
        
        # Check planogram compliance if provided
        compliance_result = None
        if planogram_id:
            logger.debug(f"Loading planogram: {planogram_id}")
            planogram = planogram_service.get(planogram_id)
            if planogram:
                logger.debug(f"Found planogram: {planogram.dict()}")
                try:
                    compliance_result = planogram_service.check_compliance(planogram, detected_products)
                    logger.debug(f"Compliance check completed: {compliance_result.dict() if compliance_result else None}")
                except Exception as e:
                    logger.error(f"Error during compliance check: {str(e)}")
                    logger.error(traceback.format_exc())
            else:
                logger.error(f"Planogram not found: {planogram_id}")
        
        # Save output image
        output_path = os.path.join(settings.OUTPUT_DIR, f"output_{image_id}.jpg")
        cv2.imwrite(output_path, normalized_image)
        
        return AnalysisResponse(
            saved_image_path=f"images/output_{image_id}.jpg",
            detected_counts=counts,
            empty_shelf_items=[item.item for item in empty_shelf_items],
            detected_products=detected_products,
            compliance_result=compliance_result,
            debug_images={
                "normalized": f"images/normalized_{image_id}.jpg",
                "output": f"images/output_{image_id}.jpg"
            },
            image_info=ImageInfo(
                original_width=original_width,
                original_height=original_height,
                normalized_width=normalized_width,
                normalized_height=normalized_height,
                aspect_ratio=round(original_width / original_height, 2)
            )
        )
        
    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Simple test endpoint for file upload debugging
@router.post("/test-upload")
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