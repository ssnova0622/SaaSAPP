# app/repositories/user_repository.py
from typing import Optional, List
from app.models.users import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__("users", User)

    def find_by_email(self, email: str) -> Optional[User]:
        return self.find_one({"email": email.lower().strip()})

    def find_by_id(self, user_id: str) -> Optional[User]:
        return self.find_one({"id": user_id})

    def list_by_tenant(self, tenant: Optional[str], role: Optional[str] = None) -> List[User]:
        query = {}
        if tenant:
            query["tenant"] = tenant
        if role:
            query["role"] = role
        return self.find_many(query)
