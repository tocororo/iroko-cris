from pydantic import BaseModel, Field, UUID4, field_validator
from typing import List, Dict, Any, Optional
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
        # Basic sanitization for labels
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

    class Config:
        from_attributes = True