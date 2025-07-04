from pydantic import BaseModel
from typing import Optional

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None

class Product(ProductCreate):
    id: str 