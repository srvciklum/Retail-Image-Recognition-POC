from typing import List, Optional, Dict
import logging
from ..models.domain import (
    Planogram, PlanogramCreate, ComplianceResult,
    ComplianceIssue, DetectedProduct
)
from .base import BaseJSONService
from ..config.settings import settings

logger = logging.getLogger(__name__)

class PlanogramService(BaseJSONService[Planogram]):
    def __init__(self):
        super().__init__(settings.PLANOGRAMS_DIR, Planogram)
    
    def create_from_planogram_create(self, planogram_create: PlanogramCreate) -> Planogram:
        """Create a new planogram from PlanogramCreate model"""
        planogram = Planogram(**planogram_create.dict())
        return self.create(planogram)
    
    def check_compliance(self, planogram: Planogram, detected_products: List[DetectedProduct]) -> ComplianceResult:
        """Check if detected products match the planogram"""
        issues: List[ComplianceIssue] = []
        correct_placements = 0
        total_positions = 0
        
        # Create a map of expected products by position
        expected_products: Dict[tuple[int, int], str] = {}
        for shelf in planogram.shelves:
            for section in shelf.sections:
                expected_products[(shelf.row, section.column)] = section.product_id
                total_positions += 1
        
        # Create a map of detected products by position
        detected_map: Dict[tuple[int, int], str] = {
            (product.row, product.column): product.label
            for product in detected_products
        }
        
        # Check each position in the planogram
        for (row, col), expected_product in expected_products.items():
            detected_product = detected_map.get((row, col))
            
            if not detected_product:
                # No product detected where one was expected
                issues.append(ComplianceIssue(
                    row=row,
                    column=col,
                    issue_type="undetected",
                    expected=f"Shelf {row}, Position {col}: {expected_product}",
                    found="No product detected",
                    severity="high"
                ))
            elif detected_product.lower() != expected_product.lower():
                # Wrong product detected
                issues.append(ComplianceIssue(
                    row=row,
                    column=col,
                    issue_type="wrong_product",
                    expected=f"Shelf {row}, Position {col}: {expected_product}",
                    found=f"Found {detected_product}",
                    severity="high"
                ))
            else:
                correct_placements += 1
        
        # Calculate compliance score
        compliance_score = (correct_placements / total_positions * 100) if total_positions > 0 else 0
        
        return ComplianceResult(
            is_compliant=len(issues) == 0,
            compliance_score=compliance_score,
            issues=issues,
            correct_placements=correct_placements,
            total_positions=total_positions,
            planogram_name=planogram.name
        ) 