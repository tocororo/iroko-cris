"""
Crawler module for Iroko CRIS - Task-based crawling system
"""

from .manager import CrawlerManager, crawler_manager
from .task import CrawlerTask
from .schemas import CrawlerTaskConfig, TaskStatus

__all__ = [
    'CrawlerManager',
    'crawler_manager', 
    'CrawlerTask',
    'CrawlerTaskConfig',
    'TaskStatus'
]