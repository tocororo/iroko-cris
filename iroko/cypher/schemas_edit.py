from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from uuid import UUID

class NodePropertyUpdate(BaseModel):
    iroko_uuid: str
    properties: Dict[str, Any]

class RelationshipUpdate(BaseModel):
    from_uuid: str
    to_uuid: str
    relation_type: str
    properties: Optional[Dict[str, Any]] = None

class NodeEditRequest(BaseModel):
    iroko_uuid: str
    properties: Dict[str, Any]
    relationships: List[RelationshipUpdate]

class RelationshipDeleteRequest(BaseModel):
    from_uuid: str
    to_uuid: str
    relation_type: str

class EditResponse(BaseModel):
    success: bool
    message: str
    updated_properties: Optional[int] = None
    updated_relationships: Optional[int] = None
    deleted_relationships: Optional[int] = None