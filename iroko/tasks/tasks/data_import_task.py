import json
import logging
from typing import Dict, Any, List
from pathlib import Path

from iroko.tasks.task import CrawlerTask
from iroko.tasks.schemas import TaskExecution
from iroko.hd2neo4j.services import RepositoryService, MapperService

logger = logging.getLogger('iroko-cris.tasks')

class DataImportTask(CrawlerTask):
    """Task for importing data using mapping configurations"""

    async def execute(self, execution: TaskExecution) -> Dict[str, Any]:
        """Execute data import task"""
        execution.execution_log.append("Starting data import task")

        try:
            # Get configuration
            mapping_file = self.config.get("mapping_file")
            data_file = self.config.get("data_file")

            if not mapping_file or not data_file:
                raise ValueError("mapping_file and data_file are required")

            execution.execution_log.append(f"Loading mapping from: {mapping_file}")
            execution.execution_log.append(f"Loading data from: {data_file}")

            # Load mapping configuration
            with open(mapping_file, 'r') as f:
                mapping_config = json.load(f)

            # Load data
            with open(data_file, 'r') as f:
                data = json.load(f)

            # Initialize services - task manages its own dependencies
            from iroko.config import app_settings
            repo_service = RepositoryService(
                app_settings.neo4j_uri,
                app_settings.neo4j_username,
                app_settings.neo4j_password,
                app_settings.neo4j_database
            )

            mapper_service = MapperService(
                mapping_config=mapping_config,
                data_to_map=data,
                repository_service=repo_service
            )

            execution.execution_log.append("Starting mapping process")
            mapper_service.start_mapping()
            execution.execution_log.append("Mapping completed successfully")

            return {
                "imported_records": len(data) if isinstance(data, list) else 1,
                "mapping_file": mapping_file,
                "data_file": data_file
            }

        except Exception as e:
            logger.error(f"Data import failed: {e}")
            execution.execution_log.append(f"Error: {str(e)}")
            raise

    def validate_config(self) -> bool:
        """Validate task configuration"""
        required = ["mapping_file", "data_file"]
        for key in required:
            if key not in self.config:
                return False

        # Check if files exist
        mapping_file = Path(self.config["mapping_file"])
        data_file = Path(self.config["data_file"])

        return mapping_file.exists() and data_file.exists()

    def get_dependencies(self) -> List[str]:
        """This task has no dependencies"""
        return []