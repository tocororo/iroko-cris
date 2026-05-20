from fastapi import APIRouter, HTTPException, Depends
from neo4j import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession as SQLAsyncSession
from typing import Dict, Any, List
from datetime import datetime
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

async def get_db_session():
    """Async generator for Neo4j sessions"""
    session = neo4j_db.get_session()
    try:
        yield session
    finally:
        await session.close()


async def _sync_node_to_pg(mg_uuid: str, pg: SQLAsyncSession, mg: AsyncSession):
    """Sync a single node from Memgraph to PostgreSQL after a write."""
    try:
        service = PGNodeService(pg, mg)
        await service.sync_single_from_memgraph(mg_uuid)
    except Exception as e:
        logger.warning(f"Post-write PG sync failed for {mg_uuid}: {e}")

def _sanitize_property_key(key: str) -> str:
    """Sanitize property keys to prevent Cypher injection"""
    # Remove backticks and other potentially dangerous characters
    sanitized = key.replace('`', '').replace('\\', '')
    return f"`{sanitized}`"

async def _node_exists(session: AsyncSession, iroko_uuid: str) -> bool:
    """Check if a node with the given iroko_uuid exists"""
    query = "MATCH (n {iroko_uuid: $iroko_uuid}) RETURN n LIMIT 1"
    result = await session.run(query, iroko_uuid=iroko_uuid)
    record = await result.single()
    return record is not None

async def _relationship_exists(
    session: AsyncSession, 
    from_uuid: str, 
    to_uuid: str, 
    relation_type: str
) -> bool:
    """Check if a relationship exists between two nodes"""
    query = """
    MATCH (a {iroko_uuid: $from_uuid})-[r:%s]->(b {iroko_uuid: $to_uuid})
    RETURN r LIMIT 1
    """ % relation_type
    
    result = await session.run(query, from_uuid=from_uuid, to_uuid=to_uuid)
    record = await result.single()
    return record is not None

@router.patch("/node/properties", response_model=EditResponse)
async def update_node_properties(
    update: NodePropertyUpdate,
    session: AsyncSession = Depends(get_db_session),
    pg: SQLAsyncSession = Depends(get_pg_session),
    current_user: TokenUser = Depends(require_edit_permission)
):
    """
    Update properties of a node by iroko_uuid
    """
    try:
        if not await _node_exists(session, update.iroko_uuid):
            raise HTTPException(status_code=404, detail=f"Node with iroko_uuid '{update.iroko_uuid}' not found")

        set_clauses = []
        parameters = {"iroko_uuid": update.iroko_uuid}

        for i, (key, value) in enumerate(update.properties.items()):
            sanitized_key = _sanitize_property_key(key)
            param_name = f"prop_{i}"
            set_clauses.append(f"n.{sanitized_key} = ${param_name}")
            parameters[param_name] = value

        if not set_clauses:
            return EditResponse(success=True, message="No properties to update")

        set_clause = "SET " + ", ".join(set_clauses)

        query = f"""
        MATCH (n {{iroko_uuid: $iroko_uuid}})
        {set_clause}
        SET n._updated_at = $now
        RETURN count(n) as updated_count
        """
        parameters["now"] = datetime.utcnow().isoformat()

        result = await session.run(query, **parameters)
        record = await result.single()
        updated_count = record["updated_count"] if record else 0

        logger.info(f"User {current_user.email} updated properties for node {update.iroko_uuid}")

        await _sync_node_to_pg(update.iroko_uuid, pg, session)

        return EditResponse(
            success=True,
            message=f"Successfully updated {updated_count} node(s)",
            updated_properties=updated_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating node properties: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update node: {str(e)}")

@router.post("/relationships", response_model=EditResponse)
async def create_or_update_relationship(
    relationship: RelationshipUpdate,
    session: AsyncSession = Depends(get_db_session),
    pg: SQLAsyncSession = Depends(get_pg_session),
    current_user: TokenUser = Depends(require_edit_permission)
):
    """
    Create or update a relationship between two nodes
    """
    try:
        if not await _node_exists(session, relationship.from_uuid):
            raise HTTPException(status_code=404, detail=f"Source node with iroko_uuid '{relationship.from_uuid}' not found")

        if not await _node_exists(session, relationship.to_uuid):
            raise HTTPException(status_code=404, detail=f"Target node with iroko_uuid '{relationship.to_uuid}' not found")

        if not relationship.relation_type.replace('_', '').isalnum():
            raise HTTPException(status_code=400, detail="Invalid relationship type")

        if relationship.properties:
            set_clauses = []
            parameters = {
                "from_uuid": relationship.from_uuid,
                "to_uuid": relationship.to_uuid
            }

            for i, (key, value) in enumerate(relationship.properties.items()):
                sanitized_key = _sanitize_property_key(key)
                param_name = f"rel_prop_{i}"
                set_clauses.append(f"r.{sanitized_key} = ${param_name}")
                parameters[param_name] = value

            set_clause = "SET " + ", ".join(set_clauses)
        else:
            set_clause = ""
            parameters = {
                "from_uuid": relationship.from_uuid,
                "to_uuid": relationship.to_uuid
            }

        query = f"""
        MATCH (a {{iroko_uuid: $from_uuid}}), (b {{iroko_uuid: $to_uuid}})
        MERGE (a)-[r:{relationship.relation_type}]->(b)
        {set_clause}
        SET a._updated_at = $now, b._updated_at = $now
        RETURN count(r) as relationship_count
        """
        parameters["now"] = datetime.utcnow().isoformat()

        result = await session.run(query, **parameters)
        record = await result.single()
        relationship_count = record["relationship_count"] if record else 0

        logger.info(f"User {current_user.email} created/updated relationship {relationship.relation_type} between {relationship.from_uuid} and {relationship.to_uuid}")

        await _sync_node_to_pg(relationship.from_uuid, pg, session)
        await _sync_node_to_pg(relationship.to_uuid, pg, session)

        return EditResponse(
            success=True,
            message=f"Successfully created/updated relationship",
            updated_relationships=relationship_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating relationship: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create relationship: {str(e)}")

@router.delete("/relationships", response_model=EditResponse)
async def delete_relationship(
    delete_request: RelationshipDeleteRequest,
    session: AsyncSession = Depends(get_db_session),
    pg: SQLAsyncSession = Depends(get_pg_session),
    current_user: TokenUser = Depends(require_edit_permission)
):
    """
    Delete a relationship between two nodes
    """
    try:
        if not await _relationship_exists(
            session,
            delete_request.from_uuid,
            delete_request.to_uuid,
            delete_request.relation_type
        ):
            raise HTTPException(
                status_code=404,
                detail=f"Relationship {delete_request.relation_type} between {delete_request.from_uuid} and {delete_request.to_uuid} not found"
            )

        query = f"""
        MATCH (a {{iroko_uuid: $from_uuid}})-[r:{delete_request.relation_type}]->(b {{iroko_uuid: $to_uuid}})
        SET a._updated_at = $now, b._updated_at = $now
        DELETE r
        RETURN count(r) as deleted_count
        """
        now_val = datetime.utcnow().isoformat()
        result = await session.run(query,
                                 from_uuid=delete_request.from_uuid,
                                 to_uuid=delete_request.to_uuid,
                                 now=now_val)
        record = await result.single()
        deleted_count = record["deleted_count"] if record else 0

        logger.info(f"User {current_user.email} deleted relationship {delete_request.relation_type} between {delete_request.from_uuid} and {delete_request.to_uuid}")

        await _sync_node_to_pg(delete_request.from_uuid, pg, session)
        await _sync_node_to_pg(delete_request.to_uuid, pg, session)

        return EditResponse(
            success=True,
            message=f"Successfully deleted relationship",
            deleted_relationships=deleted_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting relationship: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete relationship: {str(e)}")

@router.put("/node/full", response_model=EditResponse)
async def full_node_edit(
    edit_request: NodeEditRequest,
    session: AsyncSession = Depends(get_db_session),
    pg: SQLAsyncSession = Depends(get_pg_session),
    current_user: TokenUser = Depends(require_edit_permission)
):
    """
    Comprehensive node edit: update properties and relationships in a single transaction
    """
    try:
        if not await _node_exists(session, edit_request.iroko_uuid):
            raise HTTPException(status_code=404, detail=f"Node with iroko_uuid '{edit_request.iroko_uuid}' not found")

        queries = []
        parameters = {"iroko_uuid": edit_request.iroko_uuid, "now": datetime.utcnow().isoformat()}

        # Update properties + _updated_at
        if edit_request.properties:
            set_clauses = ["n._updated_at = $now"]
            for i, (key, value) in enumerate(edit_request.properties.items()):
                sanitized_key = _sanitize_property_key(key)
                param_name = f"prop_{i}"
                set_clauses.append(f"n.{sanitized_key} = ${param_name}")
                parameters[param_name] = value

            if set_clauses:
                property_query = f"""
                MATCH (n {{iroko_uuid: $iroko_uuid}})
                SET {', '.join(set_clauses)}
                """
                queries.append(property_query)

        # Process relationships
        for i, rel in enumerate(edit_request.relationships):
            if not await _node_exists(session, rel.to_uuid):
                logger.warning(f"Target node {rel.to_uuid} for relationship not found, skipping")
                continue

            if not rel.relation_type.replace('_', '').isalnum():
                logger.warning(f"Invalid relationship type {rel.relation_type}, skipping")
                continue

            rel_params = {}
            set_clauses = ["a._updated_at = $now"]

            if rel.properties:
                for j, (key, value) in enumerate(rel.properties.items()):
                    sanitized_key = _sanitize_property_key(key)
                    param_name = f"rel_{i}_prop_{j}"
                    set_clauses.append(f"r.{sanitized_key} = ${param_name}")
                    rel_params[param_name] = value

            set_clause = "SET " + ", ".join(set_clauses) if set_clauses else ""

            rel_query = f"""
            MATCH (a {{iroko_uuid: $iroko_uuid}}), (b {{iroko_uuid: $to_uuid_{i}}})
            MERGE (a)-[r:{rel.relation_type}]->(b)
            {set_clause}
            """

            queries.append(rel_query)
            parameters[f"to_uuid_{i}"] = rel.to_uuid
            parameters.update(rel_params)

        for query in queries:
            result = await session.run(query, **parameters)
            await result.consume()

        logger.info(f"User {current_user.email} performed full edit on node {edit_request.iroko_uuid}")

        await _sync_node_to_pg(edit_request.iroko_uuid, pg, session)

        return EditResponse(
            success=True,
            message=f"Successfully updated node and relationships",
            updated_properties=len(edit_request.properties),
            updated_relationships=len(edit_request.relationships)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in full node edit: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update node: {str(e)}")