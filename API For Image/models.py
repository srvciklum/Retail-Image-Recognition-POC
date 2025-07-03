from pydantic import BaseModel, Field
from typing import List, Optional

class ProductCreate(BaseModel):
    name: str = Field(..., description="Name of the product")
    variants: List[str] = Field(default_factory=list, description="List of variant names for this product")
    image_url: Optional[str] = Field(None, description="URL to the product image")
    category: Optional[str] = Field(None, description="Product category")
    description: Optional[str] = Field(None, description="Product description")

class Product(BaseModel):
    id: str = Field(..., description="Unique identifier for the product")
    name: str = Field(..., description="Name of the product")
    variants: List[str] = Field(default_factory=list, description="List of variant names for this product")
    image_url: Optional[str] = Field(None, description="URL to the product image")
    category: Optional[str] = Field(None, description="Product category")
    description: Optional[str] = Field(None, description="Product description")

class PlanogramSection(BaseModel):
    column: int = Field(..., description="Column position in the shelf (0-based)")
    expected_product: str = Field(..., description="Expected product name/type")
    allowed_variants: List[str] = Field(default_factory=list, description="List of allowed product variants")
    min_quantity: int = Field(default=1, description="Minimum required quantity")
    max_quantity: int = Field(default=1, description="Maximum allowed quantity")

class PlanogramShelf(BaseModel):
    row: int = Field(..., description="Shelf row number (0-based)")
    sections: List[PlanogramSection] = Field(..., description="Sections in this shelf")

class PlanogramCreate(BaseModel):
    name: str = Field(..., description="Display name for the planogram")
    shelves: List[PlanogramShelf] = Field(..., description="Shelves in the planogram")

class Planogram(BaseModel):
    id: str = Field(..., description="Unique identifier for the planogram")
    name: str = Field(..., description="Display name for the planogram")
    shelves: List[PlanogramShelf] = Field(..., description="Shelves in the planogram")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

class ComplianceIssue(BaseModel):
    row: int = Field(..., description="Shelf row where issue was found")
    column: int = Field(..., description="Column position where issue was found")
    issue_type: str = Field(..., description="Type of compliance issue")
    expected: str = Field(..., description="Expected product/state")
    found: str = Field(..., description="Actually found product/state")
    severity: str = Field(..., description="Issue severity (high/medium/low)")

class ComplianceResult(BaseModel):
    is_compliant: bool = Field(..., description="Overall compliance status")
    compliance_score: float = Field(..., description="Compliance score (0-100)")
    issues: List[ComplianceIssue] = Field(default_factory=list, description="List of compliance issues found")
    correct_placements: int = Field(..., description="Number of correctly placed products")
    total_positions: int = Field(..., description="Total number of positions checked")
    planogram_name: str = Field(..., description="Name of the planogram used for compliance check") 