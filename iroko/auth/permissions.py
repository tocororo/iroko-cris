from fastapi import Depends, HTTPException, status
from typing import List
from .router import get_current_user
from .schemas import TokenUser

def require_permission(permission: str):
    async def permission_checker(
        current_user: TokenUser = Depends(get_current_user)
    ):
        # Superuser has all permissions
        if current_user.is_superuser:
            return current_user
        
        # Check if user has the required permission in any of their roles
        has_perm = False
        
        # You might want to check against a role-permission mapping
        # For now, we'll assume the permission is the same as role name for simplicity
        if permission in current_user.roles:
            has_perm = True
        elif "*" in current_user.roles:  # Wildcard for all permissions
            has_perm = True
        
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: {permission} required"
            )
        return current_user
    return permission_checker

async def require_edit_permission(current_user: TokenUser = Depends(get_current_user)):
    """Require admin or curator role for edit operations"""
    allowed_roles = {"admin", "curator"}
    
    # Superuser has all permissions
    if current_user.is_superuser:
        return current_user
    
    # Check if user has any of the allowed roles
    if not any(role in allowed_roles for role in current_user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: admin or curator role required"
        )
    return current_user


# Update specific permission checkers to use token roles
require_read = require_permission("read")
require_write = require_permission("write") 
require_export = require_permission("export")
require_curator = require_permission("curator")
require_admin = require_permission("admin")  # Check for admin role