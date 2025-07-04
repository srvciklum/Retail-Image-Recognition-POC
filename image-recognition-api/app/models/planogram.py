from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PlanogramSection(BaseModel):
    column: int
    expected_product: str
    allowed_variants: List[str]
    min_quantity: int = 1
    max_quantity: int = 1

class PlanogramShelf(BaseModel):
    row: int
    sections: List[PlanogramSection]

class PlanogramCreate(BaseModel):
    name: str
    description: Optional[str] = None
    shelves: List[PlanogramShelf]

class Planogram(PlanogramCreate):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None 