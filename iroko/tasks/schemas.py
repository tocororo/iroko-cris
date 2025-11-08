from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime
from uuid import UUID

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CrawlerTaskConfig(BaseModel):
    """Configuration for a crawler task"""
    task_id: str
    name: str
    description: Optional[str] = None
    schedule: Optional[str] = None  # cron expression
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
    max_execution_time: Optional[int] = None  # None means no limit

class TaskExecution(BaseModel):
    """Record of a task execution"""
    execution_id: UUID
    task_id: str
    status: TaskStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    execution_log: List[str] = Field(default_factory=list)
    results: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True

class CrawlerStats(BaseModel):
    """Crawler statistics"""
    total_tasks: int
    active_tasks: int
    successful_executions: int
    failed_executions: int
    last_execution: Optional[datetime] = None

    class Config:
        from_attributes = True