from venv import logger
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession as SQLAsyncSession
from neo4j import AsyncSession as Neo4jAsyncSession
from typing import List, Optional
import uuid

from iroko.evals.service import eval_service  # Import the global instance
from iroko.evals.schemas import *
from iroko.auth.router import get_current_user
from iroko.auth.models import User
from iroko.storage import neo4j_db
from iroko.database import get_db_session as get_sql_session

router = APIRouter(prefix="/evals", tags=["evaluations"])

async def get_neo4j_session():
    session = await neo4j_db.get_session()
    try:
        yield session
    finally:
        await session.close()

@router.get("/methodologies", response_model=List[Methodology])
async def list_methodologies():
    """List all available evaluation methodologies"""
    return list(eval_service._methodologies.values())

@router.get("/methodologies/{methodology_id}", response_model=Methodology)
async def get_methodology(methodology_id: str):
    """Get a specific methodology"""
    methodology = eval_service._methodologies.get(methodology_id)
    if not methodology:
        raise HTTPException(status_code=404, detail="Methodology not found")
    return methodology

@router.get("/evaluate/{methodology_id}/{node_id}", response_model=EvaluationResult)
async def evaluate_node(
    methodology_id: str,
    node_id: str,
    neo4j_session: Neo4jAsyncSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """Evaluate a node using the specified methodology"""
    try:

        result = await eval_service.create_evaluation_result(
            methodology_id, node_id, neo4j_session, current_user.id
        )
        return result
    except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.post("/evaluate/complete", response_model=EvaluationResult)
async def complete_evaluation(
    evaluation: EvaluationResult,
    neo4j_session: Neo4jAsyncSession = Depends(get_neo4j_session),
    db_session: SQLAsyncSession = Depends(get_sql_session),
    current_user: User = Depends(get_current_user)
):
    """
    Complete an evaluation by providing missing answers and store the result.
    This is the second step where users provide missing answers.
    """
    try:
        
        # Store the completed evaluation
        result = await eval_service.complete_evaluation_result(neo4j_session, evaluation, current_user.id)
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete evaluation: {str(e)}")

@router.post("/evaluate/store", response_model=StoredEvaluation)
async def store_evaluation(
    evaluation: EvaluationResult,
    db_session: SQLAsyncSession = Depends(get_sql_session),
    current_user: User = Depends(get_current_user)
):
    """Store an evaluation result"""
    try:
        stored = await eval_service.store_evaluation(db_session, evaluation, current_user.id)
        return stored
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store evaluation: {str(e)}")

@router.get("/history/{node_id}", response_model=List[StoredEvaluation])
async def get_evaluation_history(
    node_id: str,
    methodology_id: Optional[str] = None,
    db_session: SQLAsyncSession = Depends(get_sql_session)
    # ,
    # current_user: User = Depends(get_current_user)
):
    """Get evaluation history for a node"""
    try:
        history = await eval_service.get_evaluation_history(
            db_session, node_id, methodology_id
        )
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")
