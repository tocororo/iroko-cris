from fastapi import APIRouter, HTTPException, Depends
from neo4j import AsyncSession
from api.schemas import CypherQuery
from api.utils import validate_cypher_query
from iroko.storage import neo4j_db
from api.utils import logger

router = APIRouter()


async def get_db_session():
    """Async generator for Neo4j sessions"""
    session = await neo4j_db.get_session()
    try:
        yield session
    finally:
        await session.close()

@router.post("/query", summary="Execute a read-only Cypher query")
async def execute_cypher(
    query_data: CypherQuery,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Execute a safe Cypher query with parameters.
    
    - **query**: Valid Cypher read-only query
    - **parameters**: Optional query parameters
    - **readonly**: Enforce read-only mode (default: True)
    """
    try:
        # Validate query safety
        validate_cypher_query(query_data.query, query_data.readonly)
        
        # Execute query
        result = await session.run(
            query_data.query,
            parameters=query_data.parameters or {}
        )
        
        # Format results
        records = await result.data()
        logger.info(records)
        return records
        
    except Exception as e:
        logger.error(f"Cypher query failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Query execution failed: {str(e)}"
        )