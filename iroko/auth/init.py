import logging
from iroko.database import get_db_session  # Use central database session
from .service import UserService, RoleService
from iroko.config import app_settings as auth_settings

logger = logging.getLogger('iroko-cris')

async def initialize_auth_system():
    """Initialize the authentication system with default roles and admin user"""
    try:
        # Database tables are now initialized in main.py via init_db()
        
        # Create default roles and admin user
        async for db in get_db_session():
            role_service = RoleService(db)
            user_service = UserService(db)
            
            # Create default roles
            await role_service.initialize_default_roles()
            logger.info("Default roles initialized")
            
            # Create admin user if specified in config
            if auth_settings.admin_email and auth_settings.admin_password:
                existing_admin = await user_service.get_user_by_email(auth_settings.admin_email)
                if not existing_admin:
                    admin_user = await user_service.create_user(
                        email=auth_settings.admin_email,
                        password=auth_settings.admin_password,
                        full_name=auth_settings.admin_full_name,
                        is_superuser=True
                    )
                    # Assign admin role
                    await user_service.assign_role(admin_user.id, "admin")
                    logger.info(f"Admin user created: {auth_settings.admin_email}")
                else:
                    logger.info("Admin user already exists")
            
            break  # Only run once
        
        logger.info("Authentication system initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing auth system: {e}")
        raise