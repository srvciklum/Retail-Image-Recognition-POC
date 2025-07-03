from typing import List, Optional
from pydantic import BaseModel, Field
from .base import BaseModelWithID

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class Product(ProductBase, BaseModelWithID):
    pass

class PlanogramShelfSection(BaseModel):
    row: int
    column: int
    product_id: str
    quantity: int = 1

class PlanogramShelf(BaseModel):
    row: int
    sections: List[PlanogramShelfSection]

class PlanogramBase(BaseModel):
    name: str
    description: Optional[str] = None
    shelves: List[PlanogramShelf]

class PlanogramCreate(PlanogramBase):
    pass

class Planogram(PlanogramBase, BaseModelWithID):
    pass

class ComplianceIssue(BaseModel):
    row: int
    column: int
    issue_type: str
    expected: str
    found: str
    severity: str = "medium"

class ComplianceResult(BaseModel):
    is_compliant: bool
    compliance_score: float
    issues: List[ComplianceIssue]
    correct_placements: int
    total_positions: int
    planogram_name: str

class DetectedProduct(BaseModel):
    label: str
    row: int
    column: int
    quantity: int = 1

class EmptyShelfItem(BaseModel):
    item: str
    row: int
    column: int

class GridDimensions(BaseModel):
    rows: int
    columns: int

class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

class GridCell(BaseModel):
    row: int
    column: int
    bbox: List[int]

class ImageInfo(BaseModel):
    original_width: int
    original_height: int
    normalized_width: int
    normalized_height: int
    aspect_ratio: float

class AnalysisResponse(BaseModel):
    saved_image_path: str
    detected_counts: dict[str, int]
    empty_shelf_items: List[str]
    detected_products: List[DetectedProduct]
    compliance_result: Optional[ComplianceResult] = None
    debug_images: dict[str, str]
    image_info: ImageInfo

class GridDetectionResponse(BaseModel):
    grid_dimensions: GridDimensions
    cells: List[GridCell]
    detection_image: str
    debug_images: dict[str, str]
    detection_method: str
    image_info: ImageInfo
    success: bool
    message: str 