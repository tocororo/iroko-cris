from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging

from .schemas import TaskExecution

logger = logging.getLogger('iroko-cris')

http_task_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }


class CrawlerTask(ABC):
    """Abstract base class for all crawler tasks"""

    def __init__(self, task_id: str, name: str, config: Dict[str, Any] = None):
        self.task_id = task_id
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f'iroko-cris.tasks.{task_id}')

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