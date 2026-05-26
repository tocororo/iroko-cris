from fastapi import APIRouter, HTTPException, Depends
from neo4j import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession as SQLAsyncSession
from typing import Dict, Any, List
from uuid import UUID
import logging

from iroko.cypher.schemas_edit import (
    NodePropertyUpdate,
    RelationshipUpdate,
    NodeEditRequest,
    RelationshipDeleteRequest,
    EditResponse
)
from iroko.storage import neo4j_db
from iroko.database import get_db_session as get_pg_session
from iroko.nodes.service import NodeService as PGNodeService
from iroko.auth.permissions import require_edit_permission
from iroko.auth.schemas import TokenUser

logger = logging.getLogger('iroko-cris.cypher')

router = APIRouter(prefix="/edit", tags=["cypher-edit"])


async def get_mg_session():
    session = neo4j_db.get_session()
    try:
        yield session
    finally:
        await session.close()


async def _node_exists(mg: AsyncSession, iroko_uuid: str) -> bool:
    result = await mg.run(
        "MATCH (n {iroko_uuid: $uuid}) RETURN n LIMIT 1",
        uuid=iroko_uuid)
    return await result.single() is not None


async def _read_node_from_mg(mg: AsyncSession, iroko_uuid: str) -> tuple[dict, list[str]]:
    result = await mg.run(
        "MATCH (n {iroko_uuid: $uuid}) RETURN properties(n) as props, labels(n) as labels",
        uuid=iroko_uuid)
    rec = await result.single()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Node {iroko_uuid} not found in graph")
    props = dict(rec["props"])
    labels = list(rec["labels"])
    # Strip internal keys
    for k in list(props.keys()):
        if k.startswith('_'):
            del props[k]
    if "Node" in labels:
        labels.remove("Node")
    return props, labels


@router.patch("/node/properties", response_model=EditResponse)
async def update_node_properties(
    update: NodePropertyUpdate,
    session: AsyncSession = Depends(get_mg_session),
    pg: SQLAsyncSession = Depends(get_pg_session),
    current_user: TokenUser = Depends(require_edit_permission)
):
    try:
        if not await _node_exists(session, update.iroko_uuid):
            raise HTTPException(status_code=404, detail=f"Node '{update.iroko_uuid}' not found")

        if not update.properties:
            return EditResponse(success=True, message="No properties to update")

        props, labels = await _read_node_from_mg(session, update.iroko_uuid)
        props.update(update.properties)

        service = PGNodeService(pg, session)
        await service.merge_node(
            iroko_uuid=UUID(update.iroko_uuid),
            labels=labels,
            data=props)

        logger.info(f"User {current_user.email} updated properties for node {update.iroko_uuid}")
        return EditResponse(
            success=True,
            message=f"Updated {len(update.properties)} properties",
            updated_properties=len(update.properties))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating node properties: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relationships", response_model=EditResponse)
async def create_or_update_relationship(
    relationship: RelationshipUpdate,
    session: AsyncSession = Depends(get_mg_session),
    pg: SQLAsyncSession = Depends(get_pg_session),
    current_user: TokenUser = Depends(require_edit_permission)
):
    try:
        if not await _node_exists(session, relationship.from_uuid):
            raise HTTPException(status_code=404, detail=f"Source node '{relationship.from_uuid}' not found")
        if not await _node_exists(session, relationship.to_uuid):
            raise HTTPException(status_code=404, detail=f"Target node '{relationship.to_uuid}' not found")

        service = PGNodeService(pg, session)
        await service.merge_relationship(
            UUID(relationship.from_uuid),
            UUID(relationship.to_uuid),
            relationship.relation_type,
            relationship.properties)

        logger.info(f"User {current_user.email} created/updated relationship {relationship.relation_type}")
        return EditResponse(
            success=True,
            message=f"Relationship {relationship.relation_type} created/updated",
            updated_relationships=1)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/relationships", response_model=EditResponse)
async def delete_relationship(
    delete_request: RelationshipDeleteRequest,
    session: AsyncSession = Depends(get_mg_session),
    pg: SQLAsyncSession = Depends(get_pg_session),
    current_user: TokenUser = Depends(require_edit_permission)
):
    try:
        service = PGNodeService(pg, session)
        result = await service.delete_relationship(
            UUID(delete_request.from_uuid),
            UUID(delete_request.to_uuid),
            delete_request.relation_type)

        if result is None:
            raise HTTPException(status_code=404, detail="Source node not found")

        logger.info(f"User {current_user.email} deleted relationship {delete_request.relation_type}")
        return EditResponse(
            success=True,
            message=f"Relationship {delete_request.relation_type} deleted",
            deleted_relationships=1)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/node/full", response_model=EditResponse)
async def full_node_edit(
    edit_request: NodeEditRequest,
    session: AsyncSession = Depends(get_mg_session),
    pg: SQLAsyncSession = Depends(get_pg_session),
    current_user: TokenUser = Depends(require_edit_permission)
):
    try:
        if not await _node_exists(session, edit_request.iroko_uuid):
            raise HTTPException(status_code=404, detail=f"Node '{edit_request.iroko_uuid}' not found")

        service = PGNodeService(pg, session)
        props, labels = await _read_node_from_mg(session, edit_request.iroko_uuid)

        if edit_request.properties:
            props.update(edit_request.properties)

        await service.merge_node(
            iroko_uuid=UUID(edit_request.iroko_uuid),
            labels=labels,
            data=props)

        for rel in edit_request.relationships:
            if not await _node_exists(session, rel.to_uuid):
                logger.warning(f"Target node {rel.to_uuid} not found, skipping relationship")
                continue
            await service.merge_relationship(
                UUID(edit_request.iroko_uuid),
                UUID(rel.to_uuid),
                rel.relation_type,
                rel.properties)

        logger.info(f"User {current_user.email} performed full edit on node {edit_request.iroko_uuid}")
        return EditResponse(
            success=True,
            message="Full node edit complete",
            updated_properties=len(edit_request.properties),
            updated_relationships=len(edit_request.relationships))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in full node edit: {e}")
        raise HTTPException(status_code=500, detail=str(e))
