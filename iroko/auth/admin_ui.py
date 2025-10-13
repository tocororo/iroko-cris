from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from .router import get_current_user, require_superuser
from .service import UserService, RoleService
from iroko.database import get_db_session
from .models import User
import os

router = APIRouter(prefix="/admin", tags=["admin"])

# Templates directory
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_superuser)
):
    user_service = UserService(db)
    role_service = RoleService(db)
    
    users = await user_service.list_users()
    roles = await role_service.list_roles()
    
    # Convert users to display format
    users_display = []
    for user in users:
        users_display.append({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "roles": [role.name for role in user.roles],
            "created_at": user.created_at
        })
    
    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "users": users_display,
            "roles": roles,
            "current_user": current_user
        }
    )