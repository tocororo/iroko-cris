from pydantic import BaseModel, Field, UUID4, field_validator
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

class RelationshipItem(BaseModel):
    target_uuid: UUID4
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('type')
    def validate_type(cls, v):
        if not re.match(r'^[A-Z0-9_]+$', v.upper()):
            raise ValueError('Relationship type must be alphanumeric and uppercase')
        return v.upper()

class NodeBase(BaseModel):
    name: str
    labels: List[str] = Field(default_factory=list, description="Graph labels (e.g., Person, Organization)")
    data: Dict[str, Any] = Field(default_factory=dict, description="Full payload of the node")
    relationships: List[RelationshipItem] = Field(default_factory=list, description="Outgoing relationships")

    @field_validator('labels')
    def validate_labels(cls, v):
        for label in v:
            if not label.isalnum():
                raise ValueError(f"Label '{label}' must be alphanumeric")
        return v

class NodeCreate(NodeBase):
    pass

class NodeUpdate(NodeBase):
    pass

class NodeResponse(NodeBase):
    iroko_uuid: UUID4
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SyncStatus(BaseModel):
    pg_node_count: int
    graph_node_count: int
    pg_updated_at: Optional[datetime] = None
    graph_updated_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    last_sync_direction: Optional[str] = None

class NodeMerge(BaseModel):
    """Schema for merge_node operation — same as NodeCreate but with optional iroko_uuid."""
    iroko_uuid: Optional[UUID4] = None
    name: str
    labels: List[str] = Field(default_factory=list)
    data: Dict[str, Any] = Field(default_factory=dict)
    relationships: List[RelationshipItem] = Field(default_factory=list)

class RelationshipMerge(BaseModel):
    """Schema for merge_relationship operation."""
    from_uuid: UUID4
    to_uuid: UUID4
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('type')
    def validate_type(cls, v):
        if not re.match(r'^[A-Z0-9_]+$', v.upper()):
            raise ValueError('Relationship type must be alphanumeric and uppercase')
        return v.upper()

class SyncRequest(BaseModel):
    direction: str = Field(..., pattern=r"^(to-graph|from-graph)$")
    batch_size: int = Field(default=500, ge=1, le=5000)
    since: Optional[datetime] = None