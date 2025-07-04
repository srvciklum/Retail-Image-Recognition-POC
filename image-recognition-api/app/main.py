from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from .api.v1.endpoints import router as api_v1_router

# Set up output directory for saved images
OUTPUT_DIR = "saved_images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(title="Image Recognition API")

# Allow React frontend to access this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify ["http://localhost:3000"] for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes first
app.include_router(api_v1_router, prefix="/api/v1")

# Serve saved images as static files under the API prefix
app.mount("/api/v1/images", StaticFiles(directory=OUTPUT_DIR), name="images") 