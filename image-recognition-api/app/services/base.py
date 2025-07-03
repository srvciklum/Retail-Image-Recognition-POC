import json
import os
from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class BaseJSONService(Generic[T]):
    def __init__(self, storage_dir: str, model_class: type[T]):
        self.storage_dir = storage_dir
        self.model_class = model_class
        os.makedirs(storage_dir, exist_ok=True)
        
    def _get_storage_path(self, item_id: str) -> str:
        return os.path.join(self.storage_dir, f"{item_id}.json")
    
    def create(self, item: T) -> T:
        try:
            path = self._get_storage_path(item.id)
            with open(path, 'w') as f:
                json.dump(item.dict(), f, indent=2)
            return item
        except Exception as e:
            logger.error(f"Error creating item: {e}")
            raise
    
    def get(self, item_id: str) -> Optional[T]:
        try:
            path = self._get_storage_path(item_id)
            if not os.path.exists(path):
                return None
            with open(path, 'r') as f:
                data = json.load(f)
                return self.model_class(**data)
        except Exception as e:
            logger.error(f"Error getting item {item_id}: {e}")
            return None
    
    def list(self) -> List[T]:
        items = []
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json') and filename != 'default_products.json':
                    path = os.path.join(self.storage_dir, filename)
                    with open(path, 'r') as f:
                        data = json.load(f)
                        items.append(self.model_class(**data))
            return items
        except Exception as e:
            logger.error(f"Error listing items: {e}")
            return []
    
    def update(self, item_id: str, item: T) -> Optional[T]:
        try:
            path = self._get_storage_path(item_id)
            if not os.path.exists(path):
                return None
            with open(path, 'w') as f:
                json.dump(item.dict(), f, indent=2)
            return item
        except Exception as e:
            logger.error(f"Error updating item {item_id}: {e}")
            return None
    
    def delete(self, item_id: str) -> bool:
        try:
            path = self._get_storage_path(item_id)
            if not os.path.exists(path):
                return False
            os.remove(path)
            return True
        except Exception as e:
            logger.error(f"Error deleting item {item_id}: {e}")
            return False 