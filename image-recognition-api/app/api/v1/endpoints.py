from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Depends
from typing import List, Optional
from ...services.image_service import ImageService
from ...services.planogram_service import PlanogramService
from ...services.product_service import ProductService
from ...models.planogram import Planogram, PlanogramCreate
from ...models.product import Product, ProductCreate
from ...models.compliance import ComplianceResult

router = APIRouter()

# Initialize services
image_service = ImageService()
planogram_service = PlanogramService()
product_service = ProductService()

# Product management endpoints
@router.post("/products", response_model=Product)
async def create_product(product: ProductCreate):
    try:
        return product_service.create_product(product)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/products", response_model=List[Product])
async def list_products():
    try:
        return product_service.list_products()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/products/search/{query}", response_model=List[Product])
async def search_products(query: str):
    return product_service.search_products(query)

@router.delete("/products/{product_id}")
async def delete_product(product_id: str):
    try:
        if not product_service.delete_product(product_id):
            raise HTTPException(status_code=404, detail="Product not found")
        return {"message": "Product deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Planogram management endpoints
@router.post("/planograms", response_model=Planogram)
async def create_planogram(planogram: PlanogramCreate):
    try:
        return planogram_service.create_planogram(planogram)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/planograms/{planogram_id}", response_model=Planogram)
async def get_planogram(planogram_id: str):
    planogram = planogram_service.get_planogram(planogram_id)
    if not planogram:
        raise HTTPException(status_code=404, detail="Planogram not found")
    return planogram

@router.get("/planograms", response_model=List[Planogram])
async def list_planograms():
    return planogram_service.list_planograms()

@router.put("/planograms/{planogram_id}", response_model=Planogram)
async def update_planogram(planogram_id: str, planogram: PlanogramCreate):
    try:
        updated = planogram_service.update_planogram(planogram_id, planogram)
        if not updated:
            raise HTTPException(status_code=404, detail="Planogram not found")
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/planograms/{planogram_id}")
async def delete_planogram(planogram_id: str):
    if not planogram_service.delete_planogram(planogram_id):
        raise HTTPException(status_code=404, detail="Planogram not found")
    return {"message": "Planogram deleted successfully"}

# Image analysis endpoints
@router.post("/analyze")
async def analyze_image(
    image: UploadFile = File(...),
    planogram_id: str = Form(None)
):
    try:
        return await image_service.analyze_image(image, planogram_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/detect-grid")
async def detect_grid(image: UploadFile = File(...)):
    try:
        return await image_service.detect_grid(image)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-upload")
async def test_upload(file: UploadFile = File(...)):
    """Simple endpoint to test file upload functionality"""
    try:
        return await image_service.test_upload(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 