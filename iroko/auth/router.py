from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import List, Optional
import uuid

import logging
logger = logging.getLogger('iroko-cris.auth')


from .schemas import TokenUser, UserCreate, UserResponse, UserWithRoles, Token, RoleCreate, RoleResponse
from .service import UserService, RoleService
from .models import User
from iroko.config import app_settings as auth_settings
from iroko.database import get_db_session
from .service import pwd_context
from .captcha_router import router as captcha_router  # Add this import


router = APIRouter(prefix="/auth", tags=["authentication"])

# Include CAPTCHA router
router.include_router(captcha_router)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="v1/auth/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=auth_settings.access_token_expire_minutes)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # issued at
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, auth_settings.secret_key, algorithm=auth_settings.algorithm)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session)
) -> TokenUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth_settings.secret_key, algorithms=[auth_settings.algorithm])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        roles: List[str] = payload.get("roles", [])
        is_superuser: bool = payload.get("is_superuser", False)
        
        if user_id is None or email is None:
            raise credentials_exception
            
        return TokenUser(
            id=uuid.UUID(user_id),
            email=email,
            roles=roles,
            is_superuser=is_superuser
        )
        
    except JWTError:
        raise credentials_exception

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def require_superuser(current_user: User = Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions - superuser required"
        )
    return current_user


async def create_user_token(user_id: uuid.UUID, db: AsyncSession) -> Token:
    """Helper function to create token for a user"""
    user_service = UserService(db)
    
    # Get user with roles
    user_with_roles = await user_service.get_user_with_roles(user_id)
    if not user_with_roles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Create token data
    token_data = {
        "sub": str(user_with_roles["id"]),
        "email": user_with_roles["email"],
        "roles": user_with_roles["roles"],
        "is_superuser": user_with_roles["is_superuser"]
    }
    
    access_token = create_access_token(data=token_data)
    
    # Create user response
    user_response = UserResponse(
        id=user_with_roles["id"],
        email=user_with_roles["email"],
        full_name=user_with_roles["full_name"],
        is_active=user_with_roles["is_active"],
        is_superuser=user_with_roles["is_superuser"],
        roles=user_with_roles["roles"],
        created_at=user_with_roles["created_at"],
        updated_at=user_with_roles["updated_at"]
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session)
):
    user_service = UserService(db)
    user = await user_service.get_user_by_email(form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Use helper function to create token
    return await create_user_token(user.id, db)

@router.post("/register", response_model=Token)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session)
):
    user_service = UserService(db)
    
    # Check if user exists
    existing_user = await user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        # Create user
        user = await user_service.create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name
        )
        
        # Assign default role (viewer)
        success = await user_service.assign_role(user.id, "viewer")
        if not success:
            logger.warning(f"Failed to assign 'viewer' role to user {user.email}")
        
        # Use helper function to create token
        return await create_user_token(user.id, db)
        
    except Exception as e:
        logger.error(f"Error during user registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )
    
    
@router.get("/users", response_model=List[UserWithRoles])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_superuser)
):
    user_service = UserService(db)
    users = await user_service.list_users(skip=skip, limit=limit)
    
    result = []
    for user in users:
        # Eagerly load the roles relationship to avoid lazy loading issues
        await db.refresh(user, ['roles'])
        
        user_with_roles = UserWithRoles(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at,
            roles=[role.name for role in user.roles]
        )
        result.append(user_with_roles)
    
    return result

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_superuser)
):
    user_service = UserService(db)
    
    existing_user = await user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = await user_service.create_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name
    )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        updated_at=user.updated_at
    )

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_superuser)
):
    user_service = UserService(db)
    
    # Check if email is taken by another user
    existing_user = await user_service.get_user_by_email(user_data.email)
    if existing_user and existing_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered by another user"
        )
    
    update_data = user_data.dict(exclude_unset=True)
    if 'password' in update_data:
        update_data['hashed_password'] = pwd_context.hash(update_data.pop('password'))
    
    user = await user_service.update_user(user_id, **update_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        updated_at=user.updated_at
    )

@router.post("/users/{user_id}/roles/{role_name}")
async def assign_role_to_user(
    user_id: uuid.UUID,
    role_name: str,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_superuser)
):
    user_service = UserService(db)
    success = await user_service.assign_role(user_id, role_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to assign role - user or role not found"
        )
    
    return {"message": f"Role '{role_name}' assigned successfully"}

@router.delete("/users/{user_id}/roles/{role_name}")
async def remove_role_from_user(
    user_id: uuid.UUID,
    role_name: str,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_superuser)
):
    user_service = UserService(db)
    success = await user_service.remove_role(user_id, role_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to remove role - user or role not found"
        )
    
    return {"message": f"Role '{role_name}' removed successfully"}

# Role management endpoints
@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_superuser)
):
    role_service = RoleService(db)
    roles = await role_service.list_roles()
    return roles

@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_superuser)
):
    role_service = RoleService(db)
    
    existing_role = await role_service.get_role_by_name(role_data.name)
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name already exists"
        )
    
    role = await role_service.create_role(
        name=role_data.name,
        description=role_data.description,
        permissions=role_data.permissions
    )
    
    return role