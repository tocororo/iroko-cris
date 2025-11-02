from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import User, Role
from typing import List, Optional
import uuid
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).filter(User.email == email))
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(select(User).filter(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def create_user(self, email: str, password: str, full_name: str = None, is_superuser: bool = False) -> User:
        user = User(
            email=email,
            hashed_password=pwd_context.hash(password),
            full_name=full_name,
            is_superuser=is_superuser
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def update_user(self, user_id: uuid.UUID, **kwargs) -> Optional[User]:
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        for key, value in kwargs.items():
            if hasattr(user, key) and key != 'id':
                setattr(user, key, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        result = await self.db.execute(
            select(User).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def delete_user(self, user_id: uuid.UUID) -> bool:
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        await self.db.delete(user)
        await self.db.commit()
        return True
    
    async def assign_role(self, user_id: uuid.UUID, role_name: str) -> bool:
        # Get role
        result = await self.db.execute(select(Role).filter(Role.name == role_name))
        role = result.scalar_one_or_none()
        
        if not role:
            return False
        
        # Get user
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        # Use direct SQL approach to avoid relationship loading issues
        from sqlalchemy import text
        
        # Check if relationship already exists
        check_query = text("""
            SELECT 1 FROM user_roles 
            WHERE user_id = :user_id AND role_id = :role_id
        """)
        result = await self.db.execute(
            check_query, 
            {"user_id": user_id, "role_id": role.id}
        )
        existing = result.first()
        
        if not existing:
            # Insert the relationship directly
            insert_query = text("""
                INSERT INTO user_roles (user_id, role_id) 
                VALUES (:user_id, :role_id)
            """)
            await self.db.execute(
                insert_query,
                {"user_id": user_id, "role_id": role.id}
            )
            await self.db.commit()
            return True
        
        return True  # Relationship already exists

    async def remove_role(self, user_id: uuid.UUID, role_name: str) -> bool:
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        # Find and remove role
        role_to_remove = None
        for role in user.roles:
            if role.name == role_name:
                role_to_remove = role
                break
        
        if role_to_remove:
            user.roles.remove(role_to_remove)
            await self.db.commit()
            return True
        
        return False
    
    async def has_permission(self, user_id: uuid.UUID, permission: str) -> bool:
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        # Superuser has all permissions
        if user.is_superuser:
            return True
        
        for role in user.roles:
            if role.permissions and permission in role.permissions:
                return True
            if role.permissions and "*" in role.permissions:
                return True
        
        return False
    async def get_user_with_roles(self, user_id: uuid.UUID) -> Optional[dict]:
        """Get user with their roles loaded"""
        from sqlalchemy.orm import selectinload
        
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.roles))
            .filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "roles": [role.name for role in user.roles]
        }
    
    async def get_user_roles(self, user_id: uuid.UUID) -> List[str]:
        """Get just the role names for a user"""
        from sqlalchemy.orm import selectinload
        
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.roles))
            .filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return []
        
        return [role.name for role in user.roles]
    
    
class RoleService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_role(self, name: str, description: str, permissions: List[str]) -> Role:
        role = Role(
            name=name,
            description=description,
            permissions=permissions
        )
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role
    
    async def get_role(self, role_id: uuid.UUID) -> Optional[Role]:
        result = await self.db.execute(select(Role).filter(Role.id == role_id))
        return result.scalar_one_or_none()
    
    async def get_role_by_name(self, name: str) -> Optional[Role]:
        result = await self.db.execute(select(Role).filter(Role.name == name))
        return result.scalar_one_or_none()
    
    async def list_roles(self) -> List[Role]:
        result = await self.db.execute(select(Role))
        return result.scalars().all()
    
    async def update_role(self, role_id: uuid.UUID, **kwargs) -> Optional[Role]:
        role = await self.get_role(role_id)
        if not role:
            return None
        
        for key, value in kwargs.items():
            if hasattr(role, key) and key != 'id':
                setattr(role, key, value)
        
        await self.db.commit()
        await self.db.refresh(role)
        return role
    
    async def delete_role(self, role_id: uuid.UUID) -> bool:
        role = await self.get_role(role_id)
        if not role:
            return False
        
        await self.db.delete(role)
        await self.db.commit()
        return True
    
    async def initialize_default_roles(self):
        default_roles = [
            {
                "name": "admin",
                "description": "System Administrator",
                "permissions": ["*"]  # Wildcard for all permissions
            },
            {
                "name": "editor",
                "description": "Content Editor",
                "permissions": ["read", "write", "export"]
            },
            {
                "name": "editor", 
                "description": "Content Editor",
                "permissions": ["read", "write", "export"]
            },
            {
                "name": "viewer",
                "description": "Data Viewer", 
                "permissions": ["read", "export"]
            },
            {
                "name": "api_user",
                "description": "API User",
                "permissions": ["read"]
            }
        ]
        
        for role_data in default_roles:
            existing_role = await self.get_role_by_name(role_data["name"])
            if not existing_role:
                await self.create_role(**role_data)