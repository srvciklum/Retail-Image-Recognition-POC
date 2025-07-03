from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Retail Image Recognition API"
    
    # CORS Settings
    BACKEND_CORS_ORIGINS: list[str] = ["*"]  # In production, replace with specific origins
    
    # File Storage Settings
    OUTPUT_DIR: str = "saved_images"
    UPLOAD_DIR: str = "uploads"
    PRODUCTS_DIR: str = "products"
    PLANOGRAMS_DIR: str = "planograms"
    
    # Model Settings
    MODEL_PATH: str = "best.pt"
    OCR_LANGUAGES: list[str] = ["en"]
    
    # Image Processing Settings
    TARGET_WIDTH: int = 600
    SIZE_BUFFER: int = 50
    MIN_HEIGHT: int = 400
    MAX_HEIGHT: int = 1200
    
    # Grid Detection Settings
    MAX_ROWS: int = 6
    MAX_COLS: int = 8
    MIN_SHELF_WIDTH_RATIO: float = 0.4
    MIN_SHELF_AREA_RATIO: float = 0.3
    
    class Config:
        case_sensitive = True
        env_file = ".env"

# Create settings instance
settings = Settings()

# Ensure directories exist
for directory in [settings.OUTPUT_DIR, settings.UPLOAD_DIR, settings.PRODUCTS_DIR, settings.PLANOGRAMS_DIR]:
    os.makedirs(directory, exist_ok=True) 