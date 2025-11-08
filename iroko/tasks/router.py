from fastapi import APIRouter, HTTPException, Depends
from typing import List

from .manager import crawler_manager
from .schemas import CrawlerTaskConfig, TaskExecution, CrawlerStats
from iroko.auth.router import require_superuser

router = APIRouter(prefix="/crawler", tags=["crawler"])

@router.get("/tasks", response_model=List[str], dependencies=[Depends(require_superuser)])
async def list_tasks():
    """List all available crawler tasks"""
    return list(crawler_manager.tasks.keys())

@router.post("/tasks/{task_id}/execute", dependencies=[Depends(require_superuser)])
async def execute_task(task_id: str):
    """Execute a crawler task"""
    try:
        execution = await crawler_manager.execute_task(task_id)
        return {
            "execution_id": str(execution.execution_id),
            "status": execution.status,
            "message": f"Task {task_id} started execution"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{task_id}/status", response_model=TaskExecution, dependencies=[Depends(require_superuser)])
async def get_task_status(task_id: str):
    """Get the status of a task"""
    status = crawler_manager.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"No execution found for task {task_id}")
    return status

@router.post("/tasks/{task_id}/stop", dependencies=[Depends(require_superuser)])
async def stop_task(task_id: str):
    """Stop a running task"""
    try:
        await crawler_manager.stop_task(task_id)
        return {"message": f"Task {task_id} stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=CrawlerStats, dependencies=[Depends(require_superuser)])
async def get_crawler_stats():
    """Get crawler statistics"""
    return crawler_manager.get_stats()

@router.get("/executions", response_model=List[TaskExecution], dependencies=[Depends(require_superuser)])
async def list_executions(limit: int = 10):
    """List recent task executions"""
    executions = list(crawler_manager.executions.values())
    executions.sort(key=lambda x: x.started_at, reverse=True)
    return executions[:limit]