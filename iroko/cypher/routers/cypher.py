from datetime import datetime
from traceback import print_tb
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from neo4j import AsyncSession
from iroko.cypher.schemas import CypherQuery, FullTextCypherQuery
from iroko.storage import neo4j_db
from iroko.cypher.utils import validate_cypher_query
import csv
import io
import logging

import ast 
logger = logging.getLogger('iroko-cris')

router = APIRouter(prefix="/cypher", tags=["cypher"])

# Constants
MAX_EXPORT_ROWS = 100000
CSV_FILENAME_FORMAT = "export_%Y%m%d_%H%M%S.csv"


async def get_db_session():
    """Async generator for Neo4j sessions"""
    session = await neo4j_db.get_session()
    try:
        yield session
    finally:
        await session.close()


def _log_query_details(operation: str, **details):
    """Helper function to log query details"""
    logger.debug(f"{operation} details:")
    separator = "-" * 40
    logger.debug(separator)
    for key, value in details.items():
        logger.debug(f"{key}: {value}")
        logger.debug("-" * 20)
    logger.debug(separator)


async def _execute_query(session: AsyncSession, query: str, parameters: dict):
    """Execute a Cypher query and return result object"""
    return await session.run(query, parameters=parameters or {})


async def _query(session: AsyncSession, query_data: CypherQuery):
    """Execute a validated Cypher query"""
    _log_query_details(
        "Cypher Query", 
        query=query_data.query, 
        parameters=query_data.parameters
    )

    # Validate query safety
    validate_cypher_query(query_data.query, query_data.readonly)

    return await _execute_query(
        session, 
        query_data.query, 
        query_data.parameters or {}
    )


async def _fulltext(session: AsyncSession, query_data: FullTextCypherQuery):
    """Execute a full-text search query"""
    _log_query_details(
        "Full-text Search",
        searchIndex=query_data.searchIndex,
        searchTerm=query_data.searchTerm,
        whereClause=query_data.whereClause,
        parameters=query_data.parameters
    )

    if query_data.countTotal:
        query = f"""
            CALL db.index.fulltext.queryNodes('{query_data.searchIndex}', $searchTerm) 
            YIELD node, score
            WITH node AS n, score
            {query_data.whereClause}
            RETURN count(n) AS count
            """
    else:
        query = f"""
            CALL db.index.fulltext.queryNodes('{query_data.searchIndex}', $searchTerm) 
            YIELD node, score
            WITH node AS n, score
            {query_data.whereClause}
            {query_data.returnClause}
            {query_data.orderClause}
            SKIP $offset
            LIMIT $limit
            """
    
    logger.debug(f"Generated full-text query:\n{query}")

    # Merge default parameters with user-provided ones
    params = (query_data.parameters or {}).copy()
    params["searchTerm"] = query_data.searchTerm
    
    # Add offset/limit if not counting
    if not query_data.countTotal:
        params.setdefault("offset", 0)
        params.setdefault("limit", 10)
    
    _log_query_details("Final Parameters", parameters=params)

    return await _execute_query(session, query, params)


async def _export_csv(result):
    records = await result.data()
    
    if not records:
        raise HTTPException(status_code=404, detail="No data found to export")

    # Parse records if they are string representations of dicts
    parsed_records = []
    for r in records:
        if len(r.keys()) != 1:
            print('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
        parsed_records.append(r.get('n'))
        # if isinstance(r, str):
        #     try:
        #         parsed = ast.literal_eval(r)
        #         parsed_records.append(parsed)
        #     except Exception:
        #         raise HTTPException(status_code=500, detail=f"Invalid record format: {r}")
        # else:
        #     parsed_records.append(r)

    records = parsed_records

    def generate_csv():
        if not records:
            return

        # Determine all possible keys (union of all record keys)
        all_keys = set()
        for r in records:
            all_keys.update(r.keys())
        all_keys = sorted(all_keys)  # for consistent order

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=all_keys, extrasaction='ignore')
        
        # Write header
        writer.writeheader()
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Write rows
        for record in records:
            # Ensure all values are strings
            safe_record = {}
            for k, v in record.items():
                if v is None:
                    safe_record[k] = ''
                elif isinstance(v, (list, dict)):
                    safe_record[k] = str(v)  # or use json.dumps(v)
                else:
                    safe_record[k] = str(v)
            writer.writerow(safe_record)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )



async def _handle_query_execution(session: AsyncSession, query_data: CypherQuery, export: bool = False):
    """Common handler for query execution with optional export"""
    result = await _query(session, query_data=query_data)
    
    if export:
        return await _export_csv(result)
    else:
        records = await result.data()
        logger.debug(f"Query returned {len(records)} records")
        return records


async def _handle_fulltext_execution(session: AsyncSession, query_data: FullTextCypherQuery, export: bool = False):
    """Common handler for full-text query execution with optional export"""
    result = await _fulltext(session, query_data)
    
    if export:
        return await _export_csv(result)
    else:
        records = await result.data()
        logger.debug(f"Full-text query returned {len(records)} records")
        return records


@router.post("/query", summary="Execute a read-only Cypher query")
async def execute_query(
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
        return await _handle_query_execution(session, query_data, export=False)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cypher query failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Query execution failed: {str(e)}"
        )


@router.post("/query/export/csv", summary="Export query results to CSV")
async def query_export_to_csv(
    query_data: CypherQuery,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Export complete query results as CSV download.
    """
    try:
        # Validate query safety
        validate_cypher_query(query_data.query, query_data.readonly)

        # Add hard limit for exports if not present
        if "LIMIT" not in query_data.query.upper():
            query_data.query = f"{query_data.query} LIMIT {MAX_EXPORT_ROWS}"

        return await _handle_query_execution(session, query_data, export=True)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV export failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Export failed: {str(e)}"
        )


@router.post("/fulltext", summary="Execute a full-text index search")
async def execute_fulltext_query(
    query_data: FullTextCypherQuery,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Execute a full-text index search query.
    
    - **searchIndex**: The full-text index to use
    - **searchTerm**: The term to search for
    - **whereClause**: Additional WHERE clause for filtering
    - **returnClause**: RETURN clause for results
    - **orderClause**: ORDER BY clause for sorting
    - **parameters**: Optional query parameters
    - **countTotal**: Whether to return only the count
    """
    try:
        return await _handle_fulltext_execution(session, query_data, export=False)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Full-text query failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Query execution failed: {str(e)}"
        )


@router.post("/fulltext/export/csv", summary="Export fulltext index search results to CSV")
async def fulltext_export_to_csv(
    query_data: FullTextCypherQuery,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Export full-text search results as CSV download.
    
    - **searchIndex**: The full-text index to use
    - **searchTerm**: The term to search for
    - **whereClause**: Additional WHERE clause for filtering
    - **returnClause**: RETURN clause for results
    - **orderClause**: ORDER BY clause for sorting
    - **parameters**: Optional query parameters
    - **countTotal**: Whether to return only the count
    """
    try:
        return await _handle_fulltext_execution(session, query_data, export=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Full-text CSV export failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Export failed: {str(e)}"
        )