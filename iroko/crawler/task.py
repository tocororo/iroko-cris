from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging

from .schemas import TaskExecution

logger = logging.getLogger('iroko-cris')

class CrawlerTask(ABC):
    """Abstract base class for all crawler tasks"""

    def __init__(self, task_id: str, name: str, config: Dict[str, Any] = None):
        self.task_id = task_id
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f'iroko-cris.crawler.{task_id}')

    @abstractmethod
    async def execute(self, execution: TaskExecution) -> Dict[str, Any]:
        """
        Execute the crawler task
        
        Args:
            execution: Task execution record for tracking progress
            
        Returns:
            Dictionary with execution results
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate task configuration
        
        Returns:
            True if configuration is valid
        """
        pass

    def get_dependencies(self) -> List[str]:
        """
        Get list of task IDs that this task depends on
        
        Returns:
            List of task IDs
        """
        return []