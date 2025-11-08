import asyncio
import logging
import importlib
import pkgutil
import traceback
from typing import Dict, List, Optional, Type
from uuid import uuid4
from datetime import datetime

from .schemas import CrawlerTaskConfig, TaskExecution, TaskStatus, CrawlerStats
from .task import CrawlerTask

logger = logging.getLogger('iroko-cris.tasks')

class CrawlerManager:
    """Manager for crawler tasks"""

    def __init__(self):
        self.tasks: Dict[str, CrawlerTask] = {}
        self.task_configs: Dict[str, CrawlerTaskConfig] = {}
        self.executions: Dict[str, TaskExecution] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self._task_registry: Dict[str, Type[CrawlerTask]] = {}

    async def auto_discover_tasks(self):
        """Automatically discover and register all tasks in the tasks package"""
        try:
            from iroko.tasks import tasks
            package = tasks
            
            for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
                if ispkg:
                    continue
                    
                try:
                    module = importlib.import_module(f"{package.__name__}.{modname}")
                    
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, CrawlerTask) and 
                            attr != CrawlerTask):
                            
                            # Use class name as task type
                            task_type = attr.__name__
                            self.register_task_type(task_type, attr)
                            logger.info(f"Auto-discovered task type: {task_type}")
                            
                except Exception as e:
                    logger.error(f"Failed to load task module {modname}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to auto-discover tasks: {e}")

    def register_task_type(self, task_type: str, task_class: Type[CrawlerTask]):
        """Register a new type of crawler task"""
        self._task_registry[task_type] = task_class
        logger.info(f"Registered task type: {task_type}")

    def create_task(self, task_config: CrawlerTaskConfig, task_type: str) -> CrawlerTask:
        """Create a task instance from configuration"""
        if task_type not in self._task_registry:
            raise ValueError(f"Unknown task type: {task_type}")

        task_class = self._task_registry[task_type]
        task = task_class(
            task_id=task_config.task_id,
            name=task_config.name,
            config=task_config.config
        )

        if not task.validate_config():
            raise ValueError(f"Invalid configuration for task: {task_config.task_id}")

        return task

    async def add_task(self, task_config: CrawlerTaskConfig, task_type: str):
        """Add a new task to the manager"""
        if task_config.task_id in self.tasks:
            raise ValueError(f"Task already exists: {task_config.task_id}")

        task = self.create_task(task_config, task_type)
        self.tasks[task_config.task_id] = task
        self.task_configs[task_config.task_id] = task_config
        logger.info(f"Added task: {task_config.task_id}")

    async def execute_task(self, task_id: str) -> TaskExecution:
        """Execute a specific task"""
        if task_id not in self.tasks:
            raise ValueError(f"Task not found: {task_id}")

        if task_id in self.running_tasks:
            raise ValueError(f"Task already running: {task_id}")

        # Check dependencies
        task = self.tasks[task_id]
        for dep_id in task.get_dependencies():
            if dep_id not in self.tasks:
                raise ValueError(f"Dependency task not found: {dep_id}")

        # Create execution record
        execution = TaskExecution(
            execution_id=uuid4(),
            task_id=task_id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now()
        )
        self.executions[str(execution.execution_id)] = execution

        # Execute task with optional timeout
        async def _execute_wrapper():
            try:
                if self.task_configs[task_id].max_execution_time:
                    async with asyncio.timeout(self.task_configs[task_id].max_execution_time):
                        results = await task.execute(execution)
                        execution.status = TaskStatus.COMPLETED
                        execution.results = results
                else:
                    # No timeout
                    results = await task.execute(execution)
                    execution.status = TaskStatus.COMPLETED
                    execution.results = results
                    
            except asyncio.TimeoutError:
                print(traceback.format_exc())
                logger.error(f"Task {task_id} timed out")
                execution.status = TaskStatus.FAILED
                execution.error_message = "Task execution timed out"
            except Exception as e:
                print(traceback.format_exc())
                logger.error(f"Task {task_id} failed: {e}")
                execution.status = TaskStatus.FAILED
                execution.error_message = str(e)
            finally:
                execution.completed_at = datetime.now()
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

        # Start execution
        self.running_tasks[task_id] = asyncio.create_task(_execute_wrapper())
        return execution

    async def stop_task(self, task_id: str):
        """Stop a running task"""
        if task_id not in self.running_tasks:
            return

        task = self.running_tasks[task_id]
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"Task {task_id} cancelled")

        # Update execution record
        for execution in self.executions.values():
            if execution.task_id == task_id and execution.status == TaskStatus.RUNNING:
                execution.status = TaskStatus.CANCELLED
                execution.completed_at = datetime.now()

    def get_task_status(self, task_id: str) -> Optional[TaskExecution]:
        """Get the status of a task"""
        for execution in reversed(list(self.executions.values())):
            if execution.task_id == task_id:
                return execution
        return None

    def get_stats(self) -> CrawlerStats:
        """Get crawler statistics"""
        successful = sum(1 for e in self.executions.values()
                        if e.status == TaskStatus.COMPLETED)
        failed = sum(1 for e in self.executions.values()
                    if e.status == TaskStatus.FAILED)

        last_execution = None
        if self.executions:
            last_execution = max(e.started_at for e in self.executions.values())

        return CrawlerStats(
            total_tasks=len(self.tasks),
            active_tasks=len(self.running_tasks),
            successful_executions=successful,
            failed_executions=failed,
            last_execution=last_execution
        )

    async def shutdown(self):
        """Shutdown the crawler manager"""
        # Stop all running tasks
        for task_id in list(self.running_tasks.keys()):
            await self.stop_task(task_id)

# Global crawler manager instance
crawler_manager = CrawlerManager()