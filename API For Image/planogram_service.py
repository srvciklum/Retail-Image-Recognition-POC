import json
import os
from typing import List, Dict, Optional
from models import Planogram, PlanogramCreate, ComplianceResult, ComplianceIssue
import numpy as np
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class PlanogramService:
    def __init__(self, storage_dir: str = "planograms"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        
    def _get_storage_path(self, planogram_id: str) -> str:
        return os.path.join(self.storage_dir, f"{planogram_id}.json")
    
    def create_planogram(self, planogram_create: PlanogramCreate) -> Planogram:
        """Create a new planogram with a generated ID"""
        try:
            # Generate a URL-friendly ID from the planogram name
            planogram_id = planogram_create.name.lower().replace(" ", "-")
            # Add a unique suffix to avoid conflicts
            planogram_id = f"{planogram_id}-{str(uuid.uuid4())[:8]}"
            
            # Create the full planogram with timestamps
            now = datetime.utcnow().isoformat()
            planogram = Planogram(
                id=planogram_id,
                created_at=now,
                updated_at=now,
                **planogram_create.dict()
            )
            
            path = self._get_storage_path(planogram.id)
            with open(path, 'w') as f:
                json.dump(planogram.dict(), f, indent=2)
            return planogram
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
    
    def update_planogram(self, planogram_id: str, planogram_update: PlanogramCreate) -> Optional[Planogram]:
        """Update an existing planogram or create it if it doesn't exist"""
        try:
            logger.debug(f"Attempting to update planogram with ID: {planogram_id}")
            logger.debug(f"Update data: {planogram_update.dict()}")
            
            path = self._get_storage_path(planogram_id)
            created_at = None
            
            # Try to get existing planogram's creation timestamp
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        existing_data = json.load(f)
                        created_at = existing_data.get('created_at')
                except Exception as e:
                    logger.error(f"Error reading existing planogram: {e}")
                    logger.error(traceback.format_exc())
            
            # Create or update the planogram
            now = datetime.utcnow().isoformat()
            updated = Planogram(
                id=planogram_id,
                created_at=created_at or now,  # Use existing timestamp or create new one
                updated_at=now,
                **planogram_update.dict()
            )
            
            # Save the planogram
            try:
                with open(path, 'w') as f:
                    json.dump(updated.dict(), f, indent=2)
                logger.debug(f"Successfully saved planogram: {planogram_id}")
                return updated
            except Exception as e:
                logger.error(f"Error saving planogram: {e}")
                logger.error(traceback.format_exc())
                return None
                
        except Exception as e:
            logger.error(f"Error updating planogram: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def delete_planogram(self, planogram_id: str) -> bool:
        """Delete a planogram by ID"""
        try:
            path = self._get_storage_path(planogram_id)
            if os.path.exists(path):
                os.remove(path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting planogram: {e}")
            return False

    def check_compliance(self, planogram: Planogram, detected_products: List[Dict]) -> ComplianceResult:
        """Check compliance of detected products against planogram"""
        logger.debug(f"Starting compliance check for planogram {planogram.id}")
        logger.debug(f"Detected products: {detected_products}")
        
        issues = []
        correct_placements = 0
        total_checked_positions = 0  # Only count positions we can actually check
        total_positions = 0
        
        # Track issues by product and shelf
        product_issues = {}
        shelf_issues = {}
        
        try:
            # Create a grid representation of detected products
            product_grid = {}
            empty_spaces = set()  # Track explicitly detected empty spaces
            
            for product in detected_products:
                # Detection system already provides 1-based row numbers
                planogram_row = product['row']
                grid_key = (planogram_row, product['column'])
                
                # Track empty spaces separately
                if product['label'].lower() in ['empty_shelf', 'empty', 'empty_space', 'emptyspace']:
                    empty_spaces.add(grid_key)
                else:
                    if grid_key in product_grid:
                        product_grid[grid_key]['quantity'] += product['quantity']
                    else:
                        product_grid[grid_key] = {
                            'product': product['label'],
                            'quantity': product['quantity']
                        }
                logger.debug(f"Added to grid - row: {planogram_row}, col: {product['column']}, product: {product['label']}")

            logger.debug(f"Final product grid: {product_grid}")
            logger.debug(f"Empty spaces: {empty_spaces}")

            # Check each shelf section against detected products
            for shelf in planogram.shelves:
                shelf_key = f"Shelf {shelf.row}"  # Use planogram's 1-based row number directly
                shelf_issues[shelf_key] = []
                
                for section in shelf.sections:
                    total_positions += 1
                    grid_key = (shelf.row, section.column)
                    
                    # Check if position is explicitly marked as empty
                    if grid_key in empty_spaces:
                        total_checked_positions += 1  # We can check this position
                        issue = ComplianceIssue(
                            row=shelf.row,
                            column=section.column,
                            issue_type="out_of_stock",
                            expected=f"{shelf_key}: {section.expected_product}",
                            found=f"Found empty space where {section.expected_product} should be and needs to be restocked",
                            severity="high"
                        )
                        shelf_issues[shelf_key].append(issue)
                        issues.append(issue)
                        continue
                    
                    # Get detected product at this position
                    detected = product_grid.get(grid_key)
                    
                    # If no product detected and not marked as empty, count as undetected
                    if not detected:
                        total_checked_positions += 1
                        issue = ComplianceIssue(
                            row=shelf.row,
                            column=section.column,
                            issue_type="undetected",
                            expected=f"{shelf_key}: {section.expected_product}",
                            found=f"No product detected where {section.expected_product} should be and needs to be restocked",
                            severity="high"
                        )
                        shelf_issues[shelf_key].append(issue)
                        issues.append(issue)
                        continue
                    
                    # We can check this position since we have a detection
                    total_checked_positions += 1
                    
                    detected_product = detected['product']
                    detected_quantity = detected['quantity']

                    # Normalize product names for comparison
                    expected_normalized = self._normalize_product_name(section.expected_product)
                    detected_normalized = self._normalize_product_name(detected_product)
                    
                    # Check product match
                    product_match = False
                    if detected_normalized == expected_normalized:
                        product_match = True
                    else:
                        for variant in section.allowed_variants:
                            if self._normalize_product_name(variant) == detected_normalized:
                                product_match = True
                                break
                    
                    if not product_match:
                        issue = ComplianceIssue(
                            row=shelf.row,
                            column=section.column,
                            issue_type="wrong_product",
                            expected=f"{shelf_key}: {section.expected_product}",
                            found=f"Found {detected_product} where {section.expected_product} should be",
                            severity="high"
                        )
                        shelf_issues[shelf_key].append(issue)
                        issues.append(issue)
                    else:
                        correct_placements += 1

            # Calculate compliance score based only on positions we could check
            compliance_score = (correct_placements / total_checked_positions) * 100 if total_checked_positions > 0 else 0
            logger.debug(f"Compliance calculation: {correct_placements} correct out of {total_checked_positions} checked positions")

            # Group similar issues
            grouped_issues = []
            for shelf_key, shelf_issue_list in shelf_issues.items():
                if shelf_issue_list:
                    # Group by issue type and product
                    wrong_products = {}
                    out_of_stock = {}
                    undetected = {}
                    
                    for issue in shelf_issue_list:
                        product = issue.expected.split(": ")[-1]  # Extract product name from expected field
                        if issue.issue_type == "wrong_product":
                            wrong_products[product] = wrong_products.get(product, 0) + 1
                        elif issue.issue_type == "out_of_stock":
                            out_of_stock[product] = out_of_stock.get(product, 0) + 1
                        elif issue.issue_type == "undetected":
                            undetected[product] = undetected.get(product, 0) + 1
                    
                    if wrong_products:
                        products_list = ", ".join(wrong_products.keys())
                        grouped_issues.append(ComplianceIssue(
                            row=shelf.row,
                            column=-1,
                            issue_type="wrong_product",
                            expected=f"{shelf_key}",
                            found=f"Incorrect products found where {products_list} should be",
                            severity="high"
                        ))
                    
                    if out_of_stock:
                        products_list = ", ".join(out_of_stock.keys())
                        grouped_issues.append(ComplianceIssue(
                            row=shelf.row,
                            column=-1,
                            issue_type="out_of_stock",
                            expected=f"{shelf_key}",
                            found=f"Found empty spaces where {products_list} should be and needs to be restocked",
                            severity="high"
                        ))
                    
                    if undetected:
                        products_list = ", ".join(undetected.keys())
                        grouped_issues.append(ComplianceIssue(
                            row=shelf.row,
                            column=-1,
                            issue_type="undetected",
                            expected=f"{shelf_key}",
                            found=f"No products detected where {products_list} should be and needs to be restocked",
                            severity="high"
                        ))

            result = ComplianceResult(
                is_compliant=len(issues) == 0,
                compliance_score=compliance_score,
                issues=issues,  # Use original individual position issues instead of grouped_issues
                correct_placements=correct_placements,
                total_positions=total_positions,
                planogram_name=planogram.name
            )
            logger.debug(f"Final compliance result: {result}")
            return result

        except Exception as e:
            logger.error(f"Error during compliance check: {str(e)}")
            raise

    def _normalize_product_name(self, name: str) -> str:
        """Normalize product name for comparison"""
        if not name:
            return 'empty'
        # Convert to lowercase and replace common variations
        normalized = name.lower().strip()
        normalized = normalized.replace('-', ' ').replace('_', ' ')
        # Handle specific product name variations
        if normalized in ['coca cola', 'coke', 'coca-cola', 'cocacola']:
            return 'coca cola'
        if normalized in ['empty shelf', 'empty space', 'empty', 'emptyspace']:
            return 'empty'
        return normalized

    def _create_product_grid(self, detected_products: List[Dict]) -> Dict:
        """Convert detected products list into a grid representation"""
        grid = {}
        try:
            for product in detected_products:
                row = product['row']
                col = product['column']
                current = grid.get((row, col), {'product': 'empty', 'quantity': 0})
                
                # If this is the first product at this location or it's the same product
                if current['product'] == 'empty' or current['product'] == product['label']:
                    grid[(row, col)] = {
                        'product': product['label'],
                        'quantity': current['quantity'] + product.get('quantity', 1)
                    }
                logger.debug(f"Added to grid - row: {row}, col: {col}, product: {product['label']}")
            
            logger.debug(f"Final product grid: {grid}")
            return grid
        except Exception as e:
            logger.error(f"Error creating product grid: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise 