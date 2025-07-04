import os
import json
import uuid
import logging
from typing import List, Optional
from ..models.product import Product, ProductCreate

logger = logging.getLogger(__name__)

class ProductService:
    def __init__(self):
        self.storage_dir = "products"
        os.makedirs(self.storage_dir, exist_ok=True)
        self._load_default_products()

    def _get_storage_path(self, product_id: str) -> str:
        return os.path.join(self.storage_dir, f"{product_id}.json")

    def _load_default_products(self):
        """Load default products if they don't exist"""
        default_file = os.path.join(self.storage_dir, "default_products.json")
        if not os.path.exists(default_file):
            default_products = [
                {"name": "Coca-Cola", "category": "Beverages", "brand": "Coca-Cola"},
                {"name": "Sprite", "category": "Beverages", "brand": "Coca-Cola"},
                {"name": "Fanta", "category": "Beverages", "brand": "Coca-Cola"}
            ]
            for product in default_products:
                self.create_product(ProductCreate(**product))

    def create_product(self, product: ProductCreate) -> Product:
        """Create a new product"""
        try:
            product_id = str(uuid.uuid4())
            product_data = product.dict()
            product_data["id"] = product_id
            
            path = self._get_storage_path(product_id)
            with open(path, 'w') as f:
                json.dump(product_data, f, indent=2)
            
            return Product(**product_data)
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            raise

    def get_product(self, product_id: str) -> Optional[Product]:
        """Get a product by ID"""
        try:
            path = self._get_storage_path(product_id)
            if not os.path.exists(path):
                return None
            with open(path, 'r') as f:
                data = json.load(f)
            return Product(**data)
        except Exception as e:
            logger.error(f"Error loading product: {e}")
            return None

    def list_products(self) -> List[Product]:
        """List all products"""
        products = []
        try:
            for file in os.listdir(self.storage_dir):
                if file.endswith('.json') and file != "default_products.json":
                    product_id = file[:-5]  # Remove .json
                    product = self.get_product(product_id)
                    if product:
                        products.append(product)
        except Exception as e:
            logger.error(f"Error listing products: {e}")
        return products

    def search_products(self, query: str) -> List[Product]:
        """Search products by name or category"""
        query = query.lower()
        return [
            product for product in self.list_products()
            if query in product.name.lower() or 
               (product.category and query in product.category.lower()) or
               (product.brand and query in product.brand.lower())
        ]

    def delete_product(self, product_id: str) -> bool:
        """Delete a product by ID"""
        try:
            path = self._get_storage_path(product_id)
            if not os.path.exists(path):
                return False
            os.remove(path)
            return True
        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            return False 