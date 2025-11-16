#!/usr/bin/env python3
import asyncio
import logging
import sys
from pathlib import Path

from iroko.tasks.tasks.fixes import IdentifierFixTask, RemoveNotUsedPublications
from iroko.tasks.tasks.ojs import OjsProcessingTask
from iroko.tasks.tasks.orcid import OrcidDumpProcessingTask, OrcidMappingTask
from iroko.tasks.tasks.organizations import OrganizationsProcessingTask
from iroko.tasks.tasks.scielo import ScieloProcessingTask

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from iroko.tasks.manager import crawler_manager
from iroko.tasks.schemas import CrawlerTaskConfig
from iroko.tasks.tasks.dummy_task import DummyTask
from iroko.tasks.tasks.miar import ColectMiarIndexes, FixMiarIndexs, MiarCubaJournalsCrawler, MiarJournalsProcessingTask


# Setup logging to see the output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)


async def add_execute(task_config: CrawlerTaskConfig, task_type: str):
    
    # Add task to manager
    await crawler_manager.add_task(task_config, task_type)
    print(f"✅ {task_type} task added to manager")
    
    # Execute the task
    execution = await crawler_manager.execute_task(task_config.task_id)
    print(f"✅ Task execution started: {execution.execution_id}")
    
    # Monitor the task
    print("📊 Monitoring task execution...")
    while True:
        status = crawler_manager.get_task_status(task_config.task_id)
        if not status:
            print("❌ Task status not found")
            break
            
        print(f"Status: {status.status}")
        
        if status.status in ["completed", "failed", "cancelled"]:
            if status.status == "completed":
                print("🎉 Task completed successfully!")
                print(f"Results: {status.results}")
            elif status.status == "failed":
                print(f"❌ Task failed: {status.error_message}")
            
            # Show execution log
            print("\nExecution Log:")
            for log_entry in status.execution_log:
                print(f"  - {log_entry}")
            break
        
        await asyncio.sleep(1)


if __name__ == "__main__":
    
    # crawler_manager.register_task_type("FixMiarIndexs", FixMiarIndexs)
    # asyncio.run(
    #     add_execute( CrawlerTaskConfig(
    #         task_id="fix_miar_db",
    #         name="Fix dbs",
    #         config={
    #             "data_file": ".data-init/miar-db-2019.json"
    #         },
    #     ), "FixMiarIndexs")
    # )

    # crawler_manager.register_task_type("ColectMiarIndexes", ColectMiarIndexes)
    # asyncio.run(
    #     add_execute(CrawlerTaskConfig(
    #         task_id="collect_miar_db",
    #         name="Collect dbs",
    #         config={
    #             "output": ".data-init/miar-db-2025-procesed.json",
    #             "input": ".data-init/miar-db-2025.json",
    #         },
    #     ), "ColectMiarIndexes")
    # )

    # crawler_manager.register_task_type("MiarCubaJournalsCrawler", MiarCubaJournalsCrawler)
    # asyncio.run(
    #      add_execute( CrawlerTaskConfig(
    #         task_id="collect_journals",
    #         name="Collect cuban journals",
    #         description="Collect cuban journals from miar",
    #         config={
    #             "output": ".data-init/miar-journals-2025.json",
    #         },
    #     ), "MiarCubaJournalsCrawler")
    # )

    # crawler_manager.register_task_type("MiarJournalsProcessingTask", MiarJournalsProcessingTask)
    # asyncio.run(
    #     add_execute(CrawlerTaskConfig(
    #         task_id="process_collected_journals",
    #         name="Process collected cuban journals",
    #         config={
    #             "output_json_path": ".data-init/miar-journals-2025-process.json",
    #             "input_json_path": ".data-init/miar-journals-2025.json",
    #         },
    #     ), "MiarJournalsProcessingTask")
    # )

    # crawler_manager.register_task_type("ScieloProcessingTask", ScieloProcessingTask)
    # asyncio.run(
    #     add_execute(CrawlerTaskConfig(
    #         task_id="process_scielo",
    #         name="process scielo dbs",
    #         config={
    #             "output_json_path": ".data-init/scielo-2025-process.json",
    #             "input": ".data-init/scielo-2025.json",
    #         },
    #     ), "ScieloProcessingTask")
    # )

    # crawler_manager.register_task_type("OjsProcessingTask", OjsProcessingTask)
    # asyncio.run(add_execute(CrawlerTaskConfig(
    #         task_id="ojs_tasks",
    #         name="Process urls and ojs tasks",
    #         config={
    #             "output_json_path": ".data-init/ojs-tasks-2025.json"
    #         },
    #     ), "OjsProcessingTask")
    # )

    # crawler_manager.register_task_type("OrganizationsProcessingTask", OrganizationsProcessingTask)
    # asyncio.run(
    #     add_execute(CrawlerTaskConfig(
    #         task_id="organizations_tasks",
    #         name="Process organizations tasks",
    #         config={
    #             "codepa": ".data-init/orgs-onei-codepa.xlsx", 
    #             "diune": ".data-init/orgs-onei-duine-septiembre-2025-fix.xlsx", 
    #             "ror": ".data-init/orgs-ror-cuban-records.json",
    #             "output": ".data-init/orgs-tasks-2025.json"
    #         },
    #     ), "OrganizationsProcessingTask")
    # )

    
    # crawler_manager.register_task_type("OrcidDumpProcessingTask", OrcidDumpProcessingTask)
    # asyncio.run(
    #     add_execute(CrawlerTaskConfig(
    #         task_id="orcid_dump_task",
    #         name="Orcid Dump processing tasks",
    #         config={
    #             'orcid_dump_path': '.data/orcid/orcid_de_cubanos',
    #             'output_json': '.data/orcid/cuban_researchers/output.json',
    #             'output_dir': '.data/orcid/cuban_researchers'
    #         },
    #     ), "OrcidDumpProcessingTask")
    # )

    # crawler_manager.register_task_type("IdentifierFixTask", IdentifierFixTask)
    # asyncio.run(
    #     add_execute(CrawlerTaskConfig(
    #         task_id="identifiers_task",
    #         name="Identifiers tasks",
    #         config={},
    #     ), "IdentifierFixTask")
    # )


    # crawler_manager.register_task_type("RemoveNotUsedPublications", RemoveNotUsedPublications)
    # asyncio.run(
    #     add_execute(CrawlerTaskConfig(
    #         task_id="identifiers_task",
    #         name="Identifiers tasks",
    #         config={ 
    #             'output_file': '.data-init/unused_publications.json',
    #         },
    #     ), "RemoveNotUsedPublications")
    # )
    
    # crawler_manager.register_task_type("OrcidMappingTask", OrcidMappingTask)
    # asyncio.run(
    #     add_execute(CrawlerTaskConfig(
    #         task_id="orcid_mapping_task",
    #         name="Orcid Mapping processing tasks",
    #         config={
    #             'input_folder': '.data-init/cuban_researchers',
    #             'output_folder': '.data-init/cuban_researchers_out',
    #             'diune_path':'.data-init/orgs-onei-duine-septiembre-2025-fix.xlsx',
    #             'person_schema_path': 'docs/schema/person-v1.0.0.json'
    #         },
    #     ), "OrcidMappingTask")
    # )


        


    print("🎊 All tasks completed!")