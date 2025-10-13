from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
import logging
from iroko.config import app_settings

logger = logging.getLogger('iroko-cris')

# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

class Base(DeclarativeBase):
    """Base class for all database models"""
    metadata = MetaData(naming_convention=convention)
    __abstract__ = True

    def to_dict(self, show=None, hide=None, path=None, show_all=None):
        """Return a dictionary representation of this model."""
        if not show:
            show = []
        if not hide:
            hide = []
        ret_data = {}

        if not path:
            path = self.__tablename__.lower()

        # Utility function to handle nested paths
        def prepend_path(item):
            item = item.lower()
            if item.split('.', 1)[0] == path:
                return item
            if item[0] != '.':
                item = '.%s' % item
            return '%s%s' % (path, item)

        show = [prepend_path(x) for x in show]
        hide = [prepend_path(x) for x in hide]

        columns = self.__table__.columns.keys()
        relationships = self.__mapper__.relationships.keys()

        # Handle columns
        for key in columns:
            check = '%s.%s' % (path, key)
            if check in hide:
                continue
            if show_all or check in show:
                ret_data[key] = getattr(self, key)

        # Handle relationships - this is where eager loading helps
        for key in relationships:
            check = '%s.%s' % (path, key)
            if check in hide:
                continue
            
            relationship_obj = getattr(self, key)
            
            # For to-many relationships (lists)
            if isinstance(relationship_obj, list):
                ret_data[key] = []
                for item in relationship_obj:
                    ret_data[key].append(item.to_dict(
                        show=show,
                        hide=hide,
                        path=('%s.%s' % (path, key.lower())),
                        show_all=show_all,
                    ))
            # For to-one relationships (single objects)
            elif hasattr(relationship_obj, 'to_dict'):
                ret_data[key] = relationship_obj.to_dict(
                    show=show,
                    hide=hide,
                    path=('%s.%s' % (path, key.lower())),
                    show_all=show_all,
                )
            else:
                # For simple relationships
                ret_data[key] = relationship_obj

        return ret_data

# Create async engine
engine = create_async_engine(
    app_settings.database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db_session():
    """Dependency for getting async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
        finally:
            await session.close()

async def init_db():
    """Initialize all database tables"""
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they are registered
            from iroko.auth import models as auth_models
            from iroko.evals import models as evals_models
            # Future: Import other module models here
            
            await conn.run_sync(Base.metadata.create_all)
        logger.info("All database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

async def close_db():
    """Close database connections"""
    await engine.dispose()