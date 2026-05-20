from sqlalchemy import Column, String, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid
from iroko.database import Base

class Node(Base):
    __tablename__ = "nodes"

    iroko_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True, nullable=False)
    labels = Column(ARRAY(String), nullable=False, default=list)
    data = Column(JSON, nullable=False)
    relationships = Column(JSON, nullable=False, default=list)
    # identifiers = Column()

    def __repr__(self):
        return f"<Node(id={self.iroko_uuid}, name={self.name}, labels={self.labels})>"