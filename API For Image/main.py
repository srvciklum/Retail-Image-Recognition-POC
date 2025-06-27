from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from ultralytics import YOLO
import easyocr
import cv2
import uuid
import os

app = FastAPI()

# Allow React frontend to access this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify ["http://localhost:3000"] for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory to save processed images
OUTPUT_DIR = "saved_images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Serve saved images as static files
app.mount("/images", StaticFiles(directory=OUTPUT_DIR), name="images")

# Load YOLO model and OCR reader
model = YOLO("best.pt")
reader = easyocr.Reader(['en'])

@app.post("/analyze")
async def analyze_image(image: UploadFile = File(...)):
    # Save uploaded image with a unique filename
    image_bytes = await image.read()
    image_id = str(uuid.uuid4())
    input_path = os.path.join(OUTPUT_DIR, f"input_{image_id}.jpg")
    with open(input_path, "wb") as f:
        f.write(image_bytes)

    # Run YOLO on the image
    #results = model.predict(source=input_path, save=False, conf=0.1)
    results = model.predict(source=input_path, show=False, save=False, conf=0.1, line_width=2)
    image = cv2.imread(input_path)
    height, width, _ = image.shape

    counts = {}
    empty_shelf_items = []
    boxes = results[0].boxes
    names = model.names
    empty_shelf_boxes = []

    for box in boxes:
        cls = int(box.cls[0])
        label = names[cls]
        counts[label] = counts.get(label, 0) + 1

        if label.lower() in ['empty_shelf', 'empty', 'empty_space', 'emptyspace']:
            empty_shelf_boxes.append(box)

    for idx, box in enumerate(empty_shelf_boxes):
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        roi = image[y2:min(y2 + 120, height), x1:x2]

        ocr_result = reader.readtext(roi)

        found = False
        for _, text, conf in ocr_result:
            if conf > 0.8:
                cleaned = text.strip().title()
                empty_shelf_items.append(cleaned)
                found = True
                break

        if not found:
            empty_shelf_items.append("Unknown Item")

    # Save processed image with overlays (optional)
    output_path = os.path.join(OUTPUT_DIR, f"output_{image_id}.jpg")
    results[0].save(filename=output_path)

    return {
        "saved_image_path": f"images/output_{image_id}.jpg",  # relative URL served statically
        "detected_counts": counts,
        "empty_shelf_items": empty_shelf_items
    }
