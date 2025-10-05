from pydantic import BaseModel
from typing import Optional, Dict, Any

class CypherQuery(BaseModel):
    query: str
    parameters: Optional[Dict[str, Any]] = None
    readonly: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "query": "MATCH (n:Person) WHERE n.name = $name RETURN n LIMIT 10",
                "parameters": {"name": "Alice"},
                "readonly": True
            }
        }


class FullTextCypherQuery(BaseModel):
    searchIndex: str
    searchTerm: str
    whereClause:str = ''
    orderClause: str = ''
    returnClause: str = ''
    parameters: Optional[Dict[str, Any]] = None
    countTotal: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "searchIndex": "OrganizationSearch",
                "searchTerm": "Pinar",
                "whereClause": "WHERE n.status = $status RETURN n LIMIT 10",
                "parameters": {"status": "active"},
                "readonly": True
            }
        }