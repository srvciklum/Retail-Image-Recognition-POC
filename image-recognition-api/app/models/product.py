from pydantic import BaseModel, Field
from typing import Optional, List

class ProductCreate(BaseModel):
    name: str = Field(..., description="Name of the product")
    variants: List[str] = Field(default_factory=list, description="List of variant names for this product")
    image_url: Optional[str] = Field(None, description="URL to the product image")
    category: Optional[str] = Field(None, description="Product category")
    description: Optional[str] = Field(None, description="Product description")
    brand: Optional[str] = Field(None, description="Product brand")

class Product(ProductCreate):
    id: str = Field(..., description="Unique identifier for the product") 