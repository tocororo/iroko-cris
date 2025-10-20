import asyncio
import json
from iroko.crawler.manager import crawler_manager
from iroko.crawler.schemas import CrawlerTaskConfig

async def main():
    """Main async function to run your crawler tasks"""
    
    # Load task configuration
    task_config = CrawlerTaskConfig(
        task_id="import_organizations",
        name="Import Organizations",
        description="Import organization data from JSON file", 
        config={
            "mapping_file": "docs/schema/organization-v1.0.0-map.json",
            "data_file": ".data-init/organizations.json"
        },
        max_execution_time=1800
    )
    
    # Add task to manager
    await crawler_manager.add_task(task_config, "DataImportTask")
    
    # Execute the task
    execution = await crawler_manager.execute_task("import_organizations")
    print(f"Task execution started: {execution.execution_id}")
    
    # Wait a bit and check status
    await asyncio.sleep(2)
    status = crawler_manager.get_task_status("import_organizations")
    print(f"Task status: {status.status}")

# Run the async function
if __name__ == "__main__":
    asyncio.run(main())