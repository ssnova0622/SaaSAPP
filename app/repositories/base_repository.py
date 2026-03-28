# app/repositories/base_repository.py
from typing import Any, Dict, List, Optional, TypeVar, Generic, Type
from pymongo.collection import Collection
from pydantic import BaseModel
from app.services.db import get_db

T = TypeVar("T", bound=BaseModel)

class BaseRepository(Generic[T]):
    def __init__(self, collection_name: str, model_class: Type[T]):
        self.collection_name = collection_name
        self.model_class = model_class

    def get_collection(self) -> Collection:
        return get_db().get_collection(self.collection_name)

    def find_one(self, query: Dict[str, Any]) -> Optional[T]:
        doc = self.get_collection().find_one(query)
        if doc:
            doc.pop("_id", None)
            return self.model_class(**doc)
        return None

    def find_many(self, query: Dict[str, Any], limit: int = 100, skip: int = 0) -> List[T]:
        cursor = self.get_collection().find(query).skip(skip).limit(limit)
        results = []
        for doc in cursor:
            doc.pop("_id", None)
            results.append(self.model_class(**doc))
        return results

    def insert_one(self, model: T) -> T:
        doc = model.model_dump() if hasattr(model, "model_dump") else model.dict()
        self.get_collection().insert_one(doc)
        return model

    def update_one_raw(self, query: Dict[str, Any], update_data: Dict[str, Any], upsert: bool = False) -> bool:
        result = self.get_collection().update_one(query, update_data, upsert=upsert)
        return result.modified_count > 0 or (upsert and result.upserted_id is not None)

    def find_one_raw(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        doc = self.get_collection().find_one(query)
        if doc:
            doc.pop("_id", None)
            return doc
        return None

    def find_many_raw(self, query: Dict[str, Any], limit: int = 100, skip: int = 0, sort: Optional[List] = None) -> List[Dict[str, Any]]:
        cursor = self.get_collection().find(query).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
        results = []
        for doc in cursor:
            doc.pop("_id", None)
            results.append(doc)
        return results

    def count_documents(self, query: Dict[str, Any]) -> int:
        return self.get_collection().count_documents(query)

    def aggregate(self, pipeline: List[Dict[str, Any]]):
        return self.get_collection().aggregate(pipeline)

    def update_one(self, query: Dict[str, Any], update_data: Dict[str, Any]) -> bool:
        result = self.get_collection().update_one(query, {"$set": update_data})
        return result.modified_count > 0

    def delete_one(self, query: Dict[str, Any]) -> bool:
        result = self.get_collection().delete_one(query)
        return result.deleted_count > 0
