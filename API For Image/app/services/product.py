from typing import List, Optional
import json
import os
import logging
from ..models.domain import Product, ProductCreate
from .base import BaseJSONService
from ..config.settings import settings

logger = logging.getLogger(__name__)

class ProductService(BaseJSONService[Product]):
    def __init__(self):
        super().__init__(settings.PRODUCTS_DIR, Product)
        self._load_default_products()
    
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
                            self.create(product)
                    logger.info("Loaded default products successfully")
            except Exception as e:
                logger.error(f"Error loading default products: {e}")
    
    def create_from_product_create(self, product_create: ProductCreate) -> Product:
        """Create a new product from ProductCreate model"""
        product = Product(**product_create.dict())
        return self.create(product)
    
    def search_products(self, query: str) -> List[Product]:
        """Search products by name or description"""
        query = query.lower()
        return [
            product for product in self.list()
            if query in product.name.lower() or 
               (product.description and query in product.description.lower())
        ] 