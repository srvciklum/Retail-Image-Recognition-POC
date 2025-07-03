import cv2
import numpy as np
import logging
import os
from typing import Tuple, List, Dict
from ultralytics import YOLO
import easyocr
from ..config.settings import settings
from ..models.domain import (
    GridDimensions, GridCell, ImageInfo, 
    DetectedProduct, EmptyShelfItem
)

logger = logging.getLogger(__name__)

class ImageService:
    def __init__(self):
        self.model = YOLO(settings.MODEL_PATH)
        self.reader = easyocr.Reader(settings.OCR_LANGUAGES)
    
    def normalize_image(self, image: np.ndarray) -> Tuple[np.ndarray, int, int]:
        """Normalize image size while maintaining aspect ratio"""
        height, width = image.shape[:2]
        
        # Check if either dimension is already close to target size
        if (abs(width - settings.TARGET_WIDTH) <= settings.SIZE_BUFFER or 
            abs(height - settings.TARGET_WIDTH) <= settings.SIZE_BUFFER):
            logger.debug(f"Skipping normalization as image dimension(s) {width}x{height} already near target")
            return image.copy(), width, height
        
        # Calculate new dimensions
        aspect_ratio = width / height
        if width > height:
            new_width = settings.TARGET_WIDTH
            new_height = int(settings.TARGET_WIDTH / aspect_ratio)
        else:
            new_height = settings.TARGET_WIDTH
            new_width = int(settings.TARGET_WIDTH * aspect_ratio)
        
        # Enforce minimum and maximum height constraints
        if new_height < settings.MIN_HEIGHT:
            new_height = settings.MIN_HEIGHT
            new_width = int(settings.MIN_HEIGHT * aspect_ratio)
        elif new_height > settings.MAX_HEIGHT:
            new_height = settings.MAX_HEIGHT
            new_width = int(settings.MAX_HEIGHT * aspect_ratio)
        
        logger.debug(f"Normalizing image from {width}x{height} to {new_width}x{new_height}")
        return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA), new_width, new_height
    
    def detect_grid(self, image: np.ndarray) -> Tuple[GridDimensions, List[int], List[int]]:
        """Detect shelf grid in image"""
        height, width = image.shape[:2]
        
        # Convert to grayscale and detect edges
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        # Detect horizontal lines (shelf separators)
        h_kernel_size = max(20, width // 15)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_size, 1))
        horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
        
        h_contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        shelf_separators = []
        
        for contour in h_contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            if w > width * settings.MIN_SHELF_WIDTH_RATIO and area > width * settings.MIN_SHELF_AREA_RATIO:
                shelf_separators.append(y + h // 2)
        
        # Detect vertical lines (product separators)
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
        
        # Filter close lines
        def filter_close_lines(lines: List[int], min_distance: float) -> List[int]:
            if not lines:
                return []
            filtered = [lines[0]]
            for line in sorted(lines)[1:]:
                if line - filtered[-1] >= min_distance:
                    filtered.append(line)
            return filtered
        
        shelf_separators = filter_close_lines(shelf_separators, height * 0.15)
        product_separators = filter_close_lines(product_separators, width * 0.08)
        
        # Create grid lines
        h_lines = [0] + shelf_separators + [height]
        v_lines = [0] + product_separators + [width]
        
        h_lines = sorted(set(h_lines))
        v_lines = sorted(set(v_lines))
        
        rows = len(h_lines) - 1
        cols = len(v_lines) - 1
        
        # Validate grid dimensions
        if (rows > settings.MAX_ROWS or cols > settings.MAX_COLS or 
            rows < 1 or cols < 1 or 
            (rows == 1 and cols <= 2) or
            (cols == 1 and rows <= 2)):
            raise ValueError("Grid detection failed validation")
        
        return GridDimensions(rows=rows, columns=cols), h_lines, v_lines
    
    def detect_products(self, image_path: str, grid_info: Tuple[GridDimensions, List[int], List[int]]) -> Tuple[List[DetectedProduct], Dict[str, int], List[EmptyShelfItem]]:
        """Detect products in image using YOLO model"""
        results = self.model.predict(source=image_path, show=False, save=False, conf=0.1)
        grid_dims, h_lines, v_lines = grid_info
        
        detected_products = []
        counts: Dict[str, int] = {}
        empty_shelf_items = []
        
        def assign_coordinates(box) -> Tuple[int, int]:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            center_y = (y1 + y2) // 2
            center_x = (x1 + x2) // 2
            
            # Assign row based on vertical position
            row = 0
            for i, h_line in enumerate(h_lines[1:]):
                if center_y <= h_line:
                    row = i
                    break
            else:
                row = grid_dims.rows - 1
            
            # Assign column based on horizontal position
            column = 0
            for i, v_line in enumerate(v_lines[1:]):
                if center_x <= v_line:
                    column = i
                    break
            else:
                column = grid_dims.columns - 1
            
            return max(0, min(grid_dims.rows - 1, row)), max(0, min(grid_dims.columns - 1, column))
        
        boxes = results[0].boxes
        names = self.model.names
        empty_shelf_boxes = []
        
        # Process each detected object
        for box in boxes:
            cls = int(box.cls[0])
            label = names[cls]
            row, column = assign_coordinates(box)
            
            logger.debug(f"Detected {label} at row {row}, column {column}")
            
            counts[label] = counts.get(label, 0) + 1
            detected_products.append(DetectedProduct(
                label=label,
                row=row,
                column=column,
                quantity=1
            ))
            
            if label.lower() in ['empty_shelf', 'empty', 'empty_space', 'emptyspace']:
                empty_shelf_boxes.append((box, row, column))
        
        # Process empty shelf areas with OCR
        for box, row, column in empty_shelf_boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            image = cv2.imread(image_path)
            roi = image[y2:min(y2 + 120, image.shape[0]), x1:x2]
            
            ocr_result = self.reader.readtext(roi)
            found = False
            
            for _, text, conf in ocr_result:
                if conf > 0.7:
                    cleaned = text.strip().title()
                    empty_shelf_items.append(EmptyShelfItem(
                        item=cleaned,
                        row=row,
                        column=column
                    ))
                    found = True
                    break
            
            if not found:
                empty_shelf_items.append(EmptyShelfItem(
                    item="Unknown Item",
                    row=row,
                    column=column
                ))
        
        return detected_products, counts, empty_shelf_items 