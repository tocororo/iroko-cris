import logging
from typing import Dict, Any
import asyncio

from iroko.tasks.task import CrawlerTask
from iroko.tasks.schemas import TaskExecution

logger = logging.getLogger('iroko-cris.tasks')

class DummyTask(CrawlerTask):
    """A simple dummy task that demonstrates basic task functionality"""
    
    async def execute(self, execution: TaskExecution) -> Dict[str, Any]:
        """Execute the dummy task"""
        execution.execution_log.append("Starting dummy task")
        logger.info("🟡 Dummy task started - Hello!")
        
        # Simulate some work with delays
        execution.execution_log.append("Step 1: Processing...")
        logger.info("🔵 Dummy task step 1")
        await asyncio.sleep(1)
        
        execution.execution_log.append("Step 2: More processing...")
        logger.info("🔵 Dummy task step 2")
        await asyncio.sleep(1)
        
        execution.execution_log.append("Step 3: Finalizing...")
        logger.info("🔵 Dummy task step 3")
        await asyncio.sleep(1)
        
        execution.execution_log.append("Task completed successfully")
        logger.info("🟢 Dummy task completed - Goodbye!")
        
        return {
            "message": "Hello from dummy task!",
            "steps_completed": 3,
            "execution_time_seconds": 3
        }
    
    def validate_config(self) -> bool:
        """Dummy task doesn't require any specific configuration"""
        logger.debug("✅ Dummy task configuration validated")
        return True  # Always valid
    
    def get_dependencies(self) -> list:
        """This task has no dependencies"""
        return []