from fastapi import Depends, HTTPException, status
from typing import List
from .router import get_current_user
from .service import UserService
from .models import User
from .database import get_db_session

async def require_permission(permission: str):
    async def permission_checker(
        user: User = Depends(get_current_user),
        db_session = Depends(get_db_session)
    ):
        user_service = UserService(db_session)
        has_perm = await user_service.has_permission(user.id, permission)
        
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: {permission} required"
            )
        return user
    return permission_checker

# Specific permission checkers
require_read = require_permission("read")
require_write = require_permission("write")
require_export = require_permission("export")
require_admin = require_permission("*")