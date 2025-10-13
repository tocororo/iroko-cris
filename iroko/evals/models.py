from sqlalchemy import Column, ForeignKey, Index, String, DateTime, JSON, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from sqlalchemy.sql import func
import uuid

from iroko.database import Base 


class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id = Column(String(255), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)  
    methodology_id = Column(String(100), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    evaluation_data = Column(JSON, nullable=False)
    is_complete = Column(Boolean, default=False)
    entity_type = Column(String(50), nullable=False)  # Source, Organization, etc.
    

    # Relationship to User model
    user = relationship("User", backref="evaluations", foreign_keys=[user_id], lazy="selectin")

    # Composite index for querying evaluations by node and methodology
    __table_args__ = (
        Index('ix_node_methodology', 'node_id', 'methodology_id'),
    )