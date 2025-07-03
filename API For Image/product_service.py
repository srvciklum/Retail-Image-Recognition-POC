import json
import os
from typing import List, Optional
from models import Product, ProductCreate
import logging
import uuid

logger = logging.getLogger(__name__)

class ProductService:
    def __init__(self, storage_dir: str = "products"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self._load_default_products()
        
    def _get_storage_path(self, product_id: str) -> str:
        return os.path.join(self.storage_dir, f"{product_id}.json")
    
    def _load_default_products(self):
        """Load default products if no products exist"""
        if not os.listdir(self.storage_dir):
            try:
                default_products_path = os.path.join(self.storage_dir, "default_products.json")
                if os.path.exists(default_products_path):
                    with open(default_products_path, 'r') as f:
                        data = json.load(f)
                        for product_data in data["products"]:
                            product = Product(**product_data)
                            self.create_product(ProductCreate(**product.dict()))
                    logger.info("Loaded default products successfully")
            except Exception as e:
                logger.error(f"Error loading default products: {e}")

    def create_product(self, product_create: ProductCreate) -> Product:
        """Create a new product with a generated ID"""
        try:
            # Generate a URL-friendly ID from the product name
            product_id = product_create.name.lower().replace(" ", "-")
            # Add a unique suffix to avoid conflicts
            product_id = f"{product_id}-{str(uuid.uuid4())[:8]}"
            
            # Create the full product
            product = Product(
                id=product_id,
                **product_create.dict()
            )
            
            path = self._get_storage_path(product.id)
            with open(path, 'w') as f:
                json.dump(product.dict(), f, indent=2)
            return product
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
            logger.error(f"Error getting product: {e}")
            return None
    
    def list_products(self) -> List[Product]:
        """List all products"""
        products = []
        try:
            for file in os.listdir(self.storage_dir):
                if file.endswith('.json'):
                    product_id = file[:-5]  # Remove .json
                    product = self.get_product(product_id)
                    if product:
                        products.append(product)
        except Exception as e:
            logger.error(f"Error listing products: {e}")
        return products
    
    def update_product(self, product: Product) -> Optional[Product]:
        """Update an existing product"""
        try:
            if not self.get_product(product.id):
                return None
            path = self._get_storage_path(product.id)
            with open(path, 'w') as f:
                json.dump(product.dict(), f, indent=2)
            return product
        except Exception as e:
            logger.error(f"Error updating product: {e}")
            return None
    
    def delete_product(self, product_id: str) -> bool:
        """Delete a product by ID"""
        try:
            path = self._get_storage_path(product_id)
            if os.path.exists(path):
                os.remove(path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            return False
    
    def search_products(self, query: str) -> List[Product]:
        """Search products by name or category"""
        products = self.list_products()
        query = query.lower()
        return [
            product for product in products
            if query in product.name.lower() or 
               (product.category and query in product.category.lower()) or
               any(query in variant.lower() for variant in product.variants)
        ] 