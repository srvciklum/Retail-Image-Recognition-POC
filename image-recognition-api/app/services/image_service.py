import os
import uuid
import logging
import cv2
import numpy as np
from fastapi import UploadFile, HTTPException
from ultralytics import YOLO
import easyocr
from typing import Dict, Any, List, Tuple
from .planogram_service import PlanogramService
import torch.serialization

# Add safe globals for PyTorch model loading
torch.serialization.add_safe_globals(['ultralytics.nn.tasks.DetectionModel'])

logger = logging.getLogger(__name__)

class ImageService:
    def __init__(self):
        self.output_dir = "saved_images"
        os.makedirs(self.output_dir, exist_ok=True)
        try:
            self.model = YOLO("best.pt")
        except Exception as e:
            logger.error(f"Error loading YOLO model: {e}")
            # Fallback to loading with weights_only=False if trusted source
            try:
                self.model = YOLO("best.pt", task='detect')
            except Exception as e2:
                logger.error(f"Failed to load model with fallback: {e2}")
                raise RuntimeError("Failed to initialize YOLO model. Please ensure the model file exists and is valid.")
        self.reader = easyocr.Reader(['en'])
        self.planogram_service = PlanogramService()

    async def analyze_image(self, image: UploadFile, planogram_id: str = None) -> Dict[str, Any]:
        """Analyze an image and detect products"""
        try:
            # Save uploaded image
            image_bytes = await image.read()
            image_id = str(uuid.uuid4())
            input_path = os.path.join(self.output_dir, f"input_{image_id}.jpg")
            with open(input_path, "wb") as f:
                f.write(image_bytes)

            logger.debug(f"Saved input image to: {input_path}")

            # Read image with OpenCV
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                raise HTTPException(status_code=400, detail="Invalid image file.")
            
            original_height, original_width = image.shape[:2]
            logger.debug(f"Original image dimensions: {original_width}x{original_height}")

            # Normalize image
            normalized_image, normalized_width, normalized_height = self._normalize_image(image)
            logger.debug(f"Normalized image dimensions: {normalized_width}x{normalized_height}")

            # Save normalized image for debugging
            normalized_path = os.path.join(self.output_dir, f"normalized_{image_id}.jpg")
            cv2.imwrite(normalized_path, normalized_image)
            logger.debug(f"Saved normalized image to: {normalized_path}")

            # Run YOLO on the normalized image
            results = self.model.predict(source=normalized_path, show=False, save=False, conf=0.1, line_width=2)

            # Get coordinate assignment function
            assign_coordinates = self._detect_shelf_layout(normalized_path)

            # Process detection results
            detected_products = []
            counts = {}
            empty_shelf_items = []
            boxes = results[0].boxes
            names = self.model.names
            empty_shelf_boxes = []

            # Scale factor for coordinate conversion
            scale_x = original_width / normalized_width
            scale_y = original_height / normalized_height

            # Process each detected object
            for box in boxes:
                cls = int(box.cls[0])
                label = names[cls]
                
                # Get coordinates
                row, column = assign_coordinates(box)
                
                logger.debug(f"Detected {label} at row {row}, column {column}")
                
                # Update counts
                counts[label] = counts.get(label, 0) + 1
                
                # Add to detected products
                detected_products.append({
                    "label": label,
                    "row": row,
                    "column": column,
                    "quantity": 1
                })

                if label.lower() in ['empty_shelf', 'empty', 'empty_space', 'emptyspace']:
                    empty_shelf_boxes.append((box, row, column))

            # Process empty shelf areas
            for box, row, column in empty_shelf_boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                roi = normalized_image[y2:min(y2 + 120, normalized_height), x1:x2]
                ocr_result = self.reader.readtext(roi)
                
                found = False
                for _, text, conf in ocr_result:
                    if conf > 0.7:
                        cleaned = text.strip().title()
                        empty_shelf_items.append({
                            "item": cleaned,
                            "row": row,
                            "column": column
                        })
                        found = True
                        break
                
                if not found:
                    empty_shelf_items.append({
                        "item": "Unknown Item",
                        "row": row,
                        "column": column
                    })

            # Save processed image
            output_normalized_path = os.path.join(self.output_dir, f"output_normalized_{image_id}.jpg")
            results[0].save(filename=output_normalized_path)
            
            output_normalized = cv2.imread(output_normalized_path)
            output_original = cv2.resize(output_normalized, (original_width, original_height), 
                                      interpolation=cv2.INTER_LANCZOS4)
            
            output_path = os.path.join(self.output_dir, f"output_{image_id}.jpg")
            cv2.imwrite(output_path, output_original)

            # Check planogram compliance
            compliance_result = None
            if planogram_id:
                logger.debug(f"Loading planogram: {planogram_id}")
                planogram = self.planogram_service.get_planogram(planogram_id)
                if planogram:
                    logger.debug(f"Found planogram: {planogram.dict()}")
                    try:
                        compliance_result = self.planogram_service.check_compliance(planogram, detected_products)
                        logger.debug(f"Compliance check completed: {compliance_result.dict() if compliance_result else None}")
                    except Exception as e:
                        logger.error(f"Error during compliance check: {str(e)}")
                        import traceback
                        logger.error(traceback.format_exc())
                else:
                    logger.error(f"Planogram not found: {planogram_id}")

            return {
                "saved_image_path": f"images/output_{image_id}.jpg",
                "detected_counts": counts,
                "empty_shelf_items": [item["item"] for item in empty_shelf_items],
                "detected_products": detected_products,
                "compliance_result": compliance_result.dict() if compliance_result else None,
                "debug_images": {
                    "normalized": f"images/normalized_{image_id}.jpg",
                    "output_normalized": f"images/output_normalized_{image_id}.jpg"
                },
                "image_info": {
                    "original_width": original_width,
                    "original_height": original_height,
                    "normalized_width": normalized_width,
                    "normalized_height": normalized_height,
                    "aspect_ratio": round(original_width / original_height, 2)
                }
            }

        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e))

    def _normalize_image(self, image: np.ndarray, target_width: int = 600, buffer: int = 50) -> Tuple[np.ndarray, int, int]:
        """Normalize image size while maintaining aspect ratio"""
        height, width = image.shape[:2]
        
        if (abs(width - target_width) <= buffer) or (abs(height - target_width) <= buffer):
            logger.debug(f"Skipping normalization as image dimension(s) {width}x{height} already near target {target_width}px")
            return image.copy(), width, height
        
        aspect_ratio = width / height
        if width > height:
            new_width = target_width
            new_height = int(target_width / aspect_ratio)
        else:
            new_height = target_width
            new_width = int(target_width * aspect_ratio)
        
        min_height, max_height = 400, 1200
        if new_height < min_height:
            new_height = min_height
            new_width = int(min_height * aspect_ratio)
        elif new_height > max_height:
            new_height = max_height
            new_width = int(max_height * aspect_ratio)
        
        logger.debug(f"Normalizing image from {width}x{height} to {new_width}x{new_height}")
        return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA), new_width, new_height

    def _detect_shelf_layout(self, image_path: str):
        """Detect shelf layout and assign row/column coordinates"""
        image = cv2.imread(image_path)
        height, width, _ = image.shape
        
        def detect_dynamic_grid(img):
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            edges = cv2.Canny(blurred, 50, 150)
            
            h_kernel_size = max(20, width // 15)
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_size, 1))
            horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
            
            h_contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            shelf_separators = []
            
            for contour in h_contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                if w > width * 0.4 and area > width * 0.3:
                    shelf_separators.append(y + h // 2)
            
            v_kernel_size = max(15, height // 20)
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kernel_size))
            vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
            
            v_contours, _ = cv2.findContours(vertical_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            product_separators = []
            
            for contour in v_contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                if h > height * 0.25 and area > height * 0.15:
                    product_separators.append(x + w // 2)
            
            def filter_close_lines(lines, min_distance):
                if not lines:
                    return []
                filtered = [lines[0]]
                for line in sorted(lines)[1:]:
                    if line - filtered[-1] >= min_distance:
                        filtered.append(line)
                return filtered
            
            shelf_separators = filter_close_lines(shelf_separators, height * 0.15)
            product_separators = filter_close_lines(product_separators, width * 0.08)
            
            h_lines = [0] + shelf_separators + [height]
            v_lines = [0] + product_separators + [width]
            
            h_lines = sorted(set(h_lines))
            v_lines = sorted(set(v_lines))
            
            rows = len(h_lines) - 1
            cols = len(v_lines) - 1
            
            if (rows > 6 or cols > 8 or rows < 1 or cols < 1 or 
                (rows == 1 and cols <= 2) or
                (cols == 1 and rows <= 2)):
                raise ValueError("Grid detection failed validation")
                
            return rows, cols, h_lines, v_lines
        
        try:
            num_rows, num_cols, h_lines, v_lines = detect_dynamic_grid(image)
            logger.debug(f"Dynamic grid detection: {num_rows} rows x {num_cols} columns")
        except Exception as e:
            logger.warning(f"Dynamic grid detection failed: {e}, using intelligent fallback")
            
            aspect_ratio = width / height
            
            if aspect_ratio > 2.5:
                num_rows = 1
                num_cols = min(6, max(3, int(width / 150)))
            elif aspect_ratio > 1.8:
                num_rows = 2
                num_cols = min(6, max(3, int(width / 120)))
            elif aspect_ratio > 1.2:
                num_rows = 2 if height < 500 else 3
                num_cols = min(5, max(3, int(width / 100)))
            elif aspect_ratio > 0.8:
                num_rows = 3
                num_cols = min(4, max(2, int(width / 150)))
            else:
                num_rows = min(4, max(3, int(height / 150)))
                num_cols = min(3, max(2, int(width / 200)))
            
            logger.debug(f"Fallback grid: {num_rows} rows x {num_cols} columns")
            
            h_lines = [int(i * height / num_rows) for i in range(num_rows + 1)]
            v_lines = [int(i * width / num_cols) for i in range(num_cols + 1)]
        
        def assign_coordinates(box):
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            center_y = (y1 + y2) // 2
            center_x = (x1 + x2) // 2
            
            row = 0
            for i, h_line in enumerate(h_lines[1:]):
                if center_y <= h_line:
                    row = i
                    break
            else:
                row = num_rows - 1
                
            column = 0
            for i, v_line in enumerate(v_lines[1:]):
                if center_x <= v_line:
                    column = i
                    break
            else:
                column = num_cols - 1
                
            row = max(0, min(num_rows - 1, row))
            column = max(0, min(num_cols - 1, column))
            
            return row, column

        return assign_coordinates

    async def detect_grid(self, image: UploadFile) -> Dict[str, Any]:
        """Detect grid layout in an image"""
        try:
            logger.debug(f"Received file: {image.filename}, content_type: {image.content_type}, size: {image.size}")
            
            if not image.filename:
                raise HTTPException(status_code=400, detail="No file uploaded")
            
            if not image.content_type or not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="File must be an image")
            
            image_bytes = await image.read()
            if not image_bytes:
                raise HTTPException(status_code=400, detail="Empty file")
                
            detection_id = str(uuid.uuid4())
            
            input_path = os.path.join(self.output_dir, f"grid_input_{detection_id}.jpg")
            with open(input_path, "wb") as f:
                f.write(image_bytes)
            
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                raise HTTPException(status_code=400, detail="Invalid image data")
            
            original_height, original_width = image.shape[:2]
            normalized_image, normalized_width, normalized_height = self._normalize_image(image)
            
            normalized_path = os.path.join(self.output_dir, f"normalized_{detection_id}.jpg")
            cv2.imwrite(normalized_path, normalized_image)

            height, width, _ = normalized_image.shape
            detection_method = "computer_vision"

            try:
                num_rows, num_cols, h_lines, v_lines = self._detect_grid_structure(normalized_image)
            except Exception as e:
                logger.warning(f"Computer vision detection failed: {e}, using intelligent fallback")
                detection_method = "intelligent_fallback"
                
                aspect_ratio = width / height
                logger.debug(f"Image aspect ratio: {aspect_ratio:.2f}")
                
                if aspect_ratio > 2.5:
                    num_rows = 1
                    num_cols = min(6, max(3, int(width / 150)))
                elif aspect_ratio > 1.8:
                    num_rows = 2
                    num_cols = min(6, max(3, int(width / 120)))
                elif aspect_ratio > 1.2:
                    num_rows = 2 if height < 500 else 3
                    num_cols = min(5, max(3, int(width / 100)))
                elif aspect_ratio > 0.8:
                    num_rows = 3
                    num_cols = min(4, max(2, int(width / 150)))
                else:
                    num_rows = min(4, max(3, int(height / 150)))
                    num_cols = min(3, max(2, int(width / 200)))
                
                h_lines = [int(i * height / num_rows) for i in range(num_rows + 1)]
                v_lines = [int(i * width / num_cols) for i in range(num_cols + 1)]

            # Create visualizations and process results
            debug_lines_img = normalized_image.copy()
            grid_img = normalized_image.copy()
            
            # Draw grid lines
            for i, y in enumerate(h_lines):
                color = (0, 255, 0) if i == 0 or i == len(h_lines)-1 else (0, 200, 255)
                cv2.line(debug_lines_img, (0, y), (width, y), color, 2)
                cv2.putText(debug_lines_img, f"H{i}", (10, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                cv2.line(grid_img, (0, y), (width, y), (0, 255, 0), 2)
            
            for i, x in enumerate(v_lines):
                color = (0, 255, 0) if i == 0 or i == len(v_lines)-1 else (255, 100, 0)
                cv2.line(debug_lines_img, (x, 0), (x, height), color, 2)
                cv2.putText(debug_lines_img, f"V{i}", (x+5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                cv2.line(grid_img, (x, 0), (x, height), (0, 255, 0), 2)

            # Add cell numbers
            for row in range(num_rows):
                for col in range(num_cols):
                    y1, y2 = h_lines[row], h_lines[row + 1]
                    x1, x2 = v_lines[col], v_lines[col + 1]
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    
                    overlay = grid_img.copy()
                    cv2.rectangle(overlay, (x1 + 2, y1 + 2), (x2 - 2, y2 - 2), (255, 255, 255), -1)
                    grid_img = cv2.addWeighted(grid_img, 0.9, overlay, 0.1, 0)
                    
                    text = f"R{row+1}C{col+1}"
                    font_scale = min(0.6, (x2 - x1) / 100)
                    cv2.putText(grid_img, text, (center_x - 25, center_y + 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1)

            # Save debug images
            debug_lines_path = os.path.join(self.output_dir, f"debug_lines_{detection_id}.jpg")
            output_path = os.path.join(self.output_dir, f"grid_detection_{detection_id}.jpg")
            cv2.imwrite(debug_lines_path, debug_lines_img)
            cv2.imwrite(output_path, grid_img)

            # Calculate cell coordinates
            scale_x = original_width / width
            scale_y = original_height / height
            cells = []
            for row in range(num_rows):
                for col in range(num_cols):
                    y1, y2 = h_lines[row], h_lines[row + 1]
                    x1, x2 = v_lines[col], v_lines[col + 1]
                    cells.append({
                        "row": row,
                        "column": col,
                        "bbox": [
                            int(x1 * scale_x), 
                            int(y1 * scale_y), 
                            int(x2 * scale_x), 
                            int(y2 * scale_y)
                        ]
                    })

            return {
                "grid_dimensions": {
                    "rows": num_rows,
                    "columns": num_cols
                },
                "cells": cells,
                "detection_image": f"images/grid_detection_{detection_id}.jpg",
                "debug_images": {
                    "normalized": f"images/normalized_{detection_id}.jpg",
                    "lines": f"images/debug_lines_{detection_id}.jpg"
                },
                "detection_method": detection_method,
                "image_info": {
                    "original_width": original_width,
                    "original_height": original_height,
                    "normalized_width": width,
                    "normalized_height": height,
                    "aspect_ratio": round(width / height, 2)
                },
                "success": True,
                "message": f"Successfully detected {num_rows}×{num_cols} grid using {detection_method.replace('_', ' ')}"
            }

        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error in grid detection: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Grid detection failed: {str(e)}")

    def _detect_grid_structure(self, image: np.ndarray):
        """Detect grid structure using computer vision"""
        height, width, _ = image.shape
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        h_kernel_size = max(20, width // 15)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_size, 1))
        horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
        
        h_contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        shelf_separators = []
        
        for contour in h_contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            if w > width * 0.4 and area > width * 0.3:
                shelf_separators.append(y + h // 2)
        
        v_kernel_size = max(15, height // 20)
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kernel_size))
        vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
        
        v_contours, _ = cv2.findContours(vertical_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        product_separators = []
        
        for contour in v_contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            if h > height * 0.25 and area > height * 0.15:
                product_separators.append(x + w // 2)
        
        def filter_close_lines(lines, min_distance):
            if not lines:
                return []
            filtered = [lines[0]]
            for line in sorted(lines)[1:]:
                if line - filtered[-1] >= min_distance:
                    filtered.append(line)
            return filtered
        
        shelf_separators = filter_close_lines(shelf_separators, height * 0.15)
        product_separators = filter_close_lines(product_separators, width * 0.08)
        
        h_lines = [0] + shelf_separators + [height]
        v_lines = [0] + product_separators + [width]
        
        h_lines = sorted(set(h_lines))
        v_lines = sorted(set(v_lines))
        
        rows = len(h_lines) - 1
        cols = len(v_lines) - 1
        
        if rows > 6:
            raise ValueError("Too many rows detected, likely false positives")
        
        return rows, cols, h_lines, v_lines

    async def test_upload(self, file: UploadFile) -> Dict[str, Any]:
        """Test file upload functionality"""
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