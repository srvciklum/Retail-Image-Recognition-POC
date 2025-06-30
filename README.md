# 🛒 **AI-Powered Shelf Intelligence**

An end-to-end web application to analyze store shelf images using computer vision.

---

## ✨ **Key Features**
- **Upload a shelf image** to detect drink products.
-  **YOLOv8 model** counts and identifies items from the image.
-  **Detects empty shelf spaces** and low-stock items.
-  **Alerts for low stock** using configurable thresholds.
-  **"Click to Order"** button to reorder products.
-  **FastAPI** used as the backend (Python).
- ☁ **Hosted on Azure VM** with Docker & Docker Compose.

---

## 🚀 **Tech Stack**
- Frontend: **React + Vite + Tailwind CSS**
- Backend: **FastAPI + Ultralytics YOLOv8**
- Deployment: **Docker**, **Azure VM**
- Image Storage: Local (volume mapped folder)

---

## 📂 **Project Structure**

```text
react-image-exchange-main/
├── API For Image/              # FastAPI backend (YOLO processing)
├── react-image-exchange-main/  # React frontend
└── docker-compose.yml
```

---

## ⚙️ **How to Run Locally**
1. Clone the repo  
   `git clone <your-repo-url>`

2. Run with Docker Compose  
   ```bash
   docker compose up --build
