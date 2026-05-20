from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from neo4j import AsyncSession as Neo4jSession
from typing import List
from uuid import UUID

from iroko.database import get_db_session
from iroko.storage import neo4j_db
from iroko.auth.permissions import require_write, require_read
from .schemas import NodeCreate, NodeUpdate, NodeResponse
from .service import NodeService, LegacySyncService

router = APIRouter(prefix="/nodes", tags=["nodes"])

async def get_mg_session():
    session = neo4j_db.get_session()
    try:
        yield session
    finally:
        await session.close()

# @router.post("/", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
# async def create_node(
#     node: NodeCreate,
#     db: AsyncSession = Depends(get_db_session),
#     mg: Neo4jSession = Depends(get_mg_session),
#     _ = Depends(require_write)
# ):
#     service = NodeService(db, mg)
#     try:
#         return await service.create_node(node)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to create node: {str(e)}")

# @router.get("/search", response_model=List[NodeResponse])
# async def search_nodes(
#     q: str = Query(..., min_length=1),
#     limit: int = 10,
#     db: AsyncSession = Depends(get_db_session),
#     mg: Neo4jSession = Depends(get_mg_session),
#     _ = Depends(require_read)
# ):
#     service = NodeService(db, mg)
#     return await service.search_nodes(q, limit)

# @router.get("/{node_id}", response_model=NodeResponse)
# async def get_node(
#     node_id: UUID,
#     db: AsyncSession = Depends(get_db_session),
#     mg: Neo4jSession = Depends(get_mg_session),
#     _ = Depends(require_read)
# ):
#     service = NodeService(db, mg)
#     node = await service.get_node(node_id)
#     if not node:
#         raise HTTPException(status_code=404, detail="Node not found")
#     return node

# @router.put("/{node_id}", response_model=NodeResponse)
# async def update_node(
#     node_id: UUID,
#     node_in: NodeUpdate,
#     db: AsyncSession = Depends(get_db_session),
#     mg: Neo4jSession = Depends(get_mg_session),
#     _ = Depends(require_write)
# ):
#     service = NodeService(db, mg)
#     try:
#         updated_node = await service.update_node(node_id, node_in)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to update node: {str(e)}")
        
#     if not updated_node:
#         raise HTTPException(status_code=404, detail="Node not found")
#     return updated_node

# @router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_node(
#     node_id: UUID,
#     db: AsyncSession = Depends(get_db_session),
#     mg: Neo4jSession = Depends(get_mg_session),
#     _ = Depends(require_write)
# ):
#     service = NodeService(db, mg)
#     success = await service.delete_node(node_id)
#     if not success:
#         raise HTTPException(status_code=404, detail="Node not found")

# @router.get("/admin/invalid-nodes", dependencies=[Depends(require_write)])
# async def check_invalid_legacy_nodes(
#     limit: int = 100,
#     mg: Neo4jSession = Depends(get_mg_session),
#     db: AsyncSession = Depends(get_db_session) 
# ):
#     service = LegacySyncService(db, mg)
#     return await service.get_invalid_nodes(limit)

# @router.post("/admin/import-legacy", dependencies=[Depends(require_write)])
# async def import_legacy_graph(
#     db: AsyncSession = Depends(get_db_session),
#     mg: Neo4jSession = Depends(get_mg_session),
# ):
#     service = LegacySyncService(db, mg)
#     try:
#         result = await service.import_from_memgraph()
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")