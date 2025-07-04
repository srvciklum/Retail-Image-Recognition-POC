import os
import json
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Set, Tuple
from ..models.planogram import Planogram, PlanogramCreate
from ..models.compliance import ComplianceResult, ComplianceIssue

logger = logging.getLogger(__name__)

class PlanogramService:
    def __init__(self):
        self.storage_dir = "planograms"
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_storage_path(self, planogram_id: str) -> str:
        return os.path.join(self.storage_dir, f"{planogram_id}.json")

    def create_planogram(self, planogram: PlanogramCreate) -> Planogram:
        """Create a new planogram"""
        try:
            planogram_id = str(uuid.uuid4())
            planogram_data = planogram.dict()
            planogram_data["id"] = planogram_id
            planogram_data["created_at"] = datetime.utcnow().isoformat()
            planogram_data["updated_at"] = planogram_data["created_at"]
            
            path = self._get_storage_path(planogram_id)
            with open(path, 'w') as f:
                json.dump(planogram_data, f, indent=2)
            
            return Planogram(**planogram_data)
        except Exception as e:
            logger.error(f"Error creating planogram: {e}")
            raise

    def get_planogram(self, planogram_id: str) -> Optional[Planogram]:
        """Get a planogram by ID"""
        try:
            path = self._get_storage_path(planogram_id)
            logger.debug(f"Looking for planogram at path: {path}")
            if not os.path.exists(path):
                logger.error(f"Planogram file not found at: {path}")
                return None
            with open(path, 'r') as f:
                data = json.load(f)
                logger.debug(f"Loaded planogram data: {data}")
            return Planogram(**data)
        except Exception as e:
            logger.error(f"Error loading planogram: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def list_planograms(self) -> List[Planogram]:
        """List all planograms"""
        planograms = []
        try:
            for file in os.listdir(self.storage_dir):
                if file.endswith('.json'):
                    planogram_id = file[:-5]  # Remove .json
                    planogram = self.get_planogram(planogram_id)
                    if planogram:
                        planograms.append(planogram)
        except Exception as e:
            logger.error(f"Error listing planograms: {e}")
        return planograms

    def delete_planogram(self, planogram_id: str) -> bool:
        """Delete a planogram by ID"""
        try:
            path = self._get_storage_path(planogram_id)
            if not os.path.exists(path):
                return False
            os.remove(path)
            return True
        except Exception as e:
            logger.error(f"Error deleting planogram: {e}")
            return False

    def update_planogram(self, planogram_id: str, planogram: PlanogramCreate) -> Optional[Planogram]:
        """Update an existing planogram"""
        try:
            path = self._get_storage_path(planogram_id)
            if not os.path.exists(path):
                return None

            # Read existing planogram to preserve created_at
            with open(path, 'r') as f:
                existing_data = json.load(f)

            # Update planogram data
            planogram_data = planogram.dict()
            planogram_data["id"] = planogram_id
            planogram_data["created_at"] = existing_data["created_at"]
            planogram_data["updated_at"] = datetime.utcnow().isoformat()

            # Save updated planogram
            with open(path, 'w') as f:
                json.dump(planogram_data, f, indent=2)

            return Planogram(**planogram_data)
        except Exception as e:
            logger.error(f"Error updating planogram: {e}")
            return None

    def check_compliance(self, planogram: Planogram, detected_products: List[Dict[str, Any]]) -> ComplianceResult:
        """Check compliance of detected products against planogram"""
        logger.debug(f"Starting compliance check for planogram {planogram.name}")
        logger.debug(f"Detected products: {detected_products}")
        
        issues = []
        correct_placements = 0
        total_positions = sum(len(shelf.sections) for shelf in planogram.shelves)
        
        try:
            # Create a grid representation of detected products
            product_grid: Dict[Tuple[int, int], Dict] = {}
            empty_spaces: Set[Tuple[int, int]] = set()
            
            # Process detected products
            for product in detected_products:
                grid_key = (product['row'], product['column'])
                
                # Handle empty spaces separately
                if product['label'].lower() in ['empty_shelf', 'empty', 'empty_space', 'emptyspace']:
                    empty_spaces.add(grid_key)
                else:
                    if grid_key in product_grid:
                        product_grid[grid_key]['quantity'] += product.get('quantity', 1)
                    else:
                        product_grid[grid_key] = {
                            'product': product['label'],
                            'quantity': product.get('quantity', 1)
                        }
                logger.debug(f"Added to grid - row: {product['row']}, col: {product['column']}, product: {product['label']}")

            logger.debug(f"Final product grid: {product_grid}")
            logger.debug(f"Empty spaces: {empty_spaces}")

            # Check each shelf section against detected products
            for shelf in planogram.shelves:
                shelf_key = f"Shelf {shelf.row}"
                
                for section in shelf.sections:
                    grid_key = (shelf.row, section.column)
                    
                    # Check if position is explicitly marked as empty
                    if grid_key in empty_spaces:
                        issues.append(ComplianceIssue(
                            row=shelf.row,
                            column=section.column,
                            issue_type="out_of_stock",
                            expected=f"{shelf_key}: {section.expected_product}",
                            found=f"Found empty space where {section.expected_product} should be and needs to be restocked",
                            severity="high"
                        ))
                        continue
                    
                    # Get detected product at this position
                    detected = product_grid.get(grid_key)
                    
                    if not detected:
                        # Position is undetected (no product and not marked empty)
                        issues.append(ComplianceIssue(
                            row=shelf.row,
                            column=section.column,
                            issue_type="undetected",
                            expected=f"{shelf_key}: {section.expected_product}",
                            found="Unable to detect product in this position",
                            severity="medium"
                        ))
                        continue
                    
                    # Check if detected product matches expected or variants
                    product_matches = (
                        detected['product'].lower() == section.expected_product.lower() or
                        any(detected['product'].lower() == variant.lower() for variant in section.allowed_variants)
                    )
                    
                    if not product_matches:
                        issues.append(ComplianceIssue(
                            row=shelf.row,
                            column=section.column,
                            issue_type="wrong_product",
                            expected=f"{shelf_key}: {section.expected_product}",
                            found=f"Found {detected['product']} where {section.expected_product} should be",
                            severity="high"
                        ))
                    else:
                        correct_placements += 1

            # Calculate compliance score
            compliance_score = (correct_placements / total_positions * 100) if total_positions > 0 else 0.0

            return ComplianceResult(
                is_compliant=len(issues) == 0,
                compliance_score=compliance_score,
                issues=issues,
                correct_placements=correct_placements,
                total_positions=total_positions,
                planogram_name=planogram.name
            )

        except Exception as e:
            logger.error(f"Error checking compliance: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise 