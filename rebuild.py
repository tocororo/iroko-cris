#!/usr/bin/env python3
"""
Complete rebuild script for iroko-cris.

Drops all data from both databases, re-imports everything from source
files, runs all enrichment crawler tasks, and syncs PG with Memgraph.
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("rebuild")

# ---------------------------------------------------------------------------
# 1. Drop all data
# ---------------------------------------------------------------------------

async def drop_databases():
    logger.info("=" * 60)
    logger.info("STEP 1: Dropping all data from both databases")
    logger.info("=" * 60)

    # Drop Memgraph
    from neo4j import AsyncGraphDatabase
    from iroko.config import app_settings

    driver = AsyncGraphDatabase.driver(
        app_settings.neo4j_uri,
        auth=(app_settings.neo4j_username, app_settings.neo4j_password),
        database=app_settings.neo4j_database,
    )
    async with driver.session() as s:
        await s.run("MATCH (a)-[r]->() DELETE r WITH DISTINCT a DELETE a")
        await s.run("MATCH (a) DELETE a")
        logger.info("  Memgraph: all nodes and relationships deleted")
    await driver.close()

    # Drop PostgreSQL tables
    from iroko.database import engine, Base, close_db
    from iroko.database import AsyncSessionLocal

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("  PostgreSQL: all tables dropped")

    await close_db()

    logger.info("  Both databases cleared.\n")


# ---------------------------------------------------------------------------
# 2. Recreate PG schema
# ---------------------------------------------------------------------------

async def init_databases():
    logger.info("=" * 60)
    logger.info("STEP 2: Initializing databases (PG tables + auth system)")
    logger.info("=" * 60)

    from iroko.database import init_db, engine, Base, AsyncSessionLocal
    from iroko.auth.init import initialize_auth_system

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("  PG tables created")

    await initialize_auth_system()
    logger.info("  Auth system initialized (admin user + default roles)\n")


# ---------------------------------------------------------------------------
# 3. Import bulk seed data using MapperService (sync)
# ---------------------------------------------------------------------------

def import_bulk_data():
    logger.info("=" * 60)
    logger.info("STEP 3: Importing bulk seed data")
    logger.info("=" * 60)

    from iroko.hd2neo4j.services import RepositoryService, MapperService
    from iroko.config import app_settings

    r_service = RepositoryService(
        app_settings.neo4j_uri,
        app_settings.neo4j_username,
        app_settings.neo4j_password,
        app_settings.neo4j_database,
        pg_url=app_settings.database_url,
    )

    datasets = [
        ("organizations", "docs/schema/organization-v1.0.0-map.json", ".data-init/organizations.json"),
        ("sources", "docs/schema/source-v1.0.0-map.json", ".data-init/sources.json"),
        ("persons", "docs/schema/person-v1.0.0-map.json", ".data-init/persons.json"),
        ("outputs", "docs/schema/output-v1.0.0-map.json", ".data-init/outputs.json"),
    ]

    for name, map_path, data_path in datasets:
        logger.info(f"  Importing {name}...")
        try:
            with open(map_path) as f:
                config = json.load(f)
            with open(data_path) as f:
                data = json.load(f)

            m_service = MapperService(
                mapping_config=config,
                repository_service=r_service,
                data_to_map=data,
            )
            m_service.start_mapping()
            logger.info(f"  ✓ {name} imported")
        except Exception as e:
            logger.error(f"  ✗ {name} failed: {e}")

    r_service.repository.close()
    logger.info("  Bulk import complete.\n")


# ---------------------------------------------------------------------------
# 4. Run enrichment / crawler tasks (async)
# ---------------------------------------------------------------------------

async def run_task(task_type, config):
    from iroko.tasks.manager import crawler_manager
    from iroko.tasks.schemas import CrawlerTaskConfig

    task_id = config.get("task_id", task_type.lower())
    cfg = CrawlerTaskConfig(task_id=task_id, name=task_type, config=config)
    await crawler_manager.add_task(cfg, task_type)
    execution = await crawler_manager.execute_task(task_id)

    logger.info(f"  Task {task_type} started (id={execution.execution_id})")
    while True:
        status = crawler_manager.get_task_status(task_id)
        if not status:
            break
        if status.status in ("completed", "failed", "cancelled"):
            if status.status == "completed":
                logger.info(f"  ✓ {task_type} completed: {status.results}")
            else:
                logger.error(f"  ✗ {task_type} {status.status}: {status.error_message}")
            break
        await asyncio.sleep(2)


async def run_crawler_tasks():
    logger.info("=" * 60)
    logger.info("STEP 4: Running enrichment crawler tasks")
    logger.info("=" * 60)

    from iroko.tasks.manager import crawler_manager
    await crawler_manager.auto_discover_tasks()

    task_queue = [
        # MIAR fixes
        ("FixMiarIndexs", {"task_id": "fix_miar_db", "data_file": ".data-init/miar-db-2019.json"}),
        # MIAR index collection
        ("ColectMiarIndexes", {
            "task_id": "collect_miar_db",
            "input": ".data-init/miar-db-2025.json",
            "output": ".data-init/miar-db-2025-procesed.json",
        }),
        # MIAR journal harvesting from web
        ("MiarCubaJournalsCrawler", {
            "task_id": "collect_journals",
            "output": ".data-init/miar-journals-2025.json",
        }),
        # Process harvested MIAR journals
        ("MiarJournalsProcessingTask", {
            "task_id": "process_collected_journals",
            "input_json_path": ".data-init/miar-journals-2025.json",
            "output_json_path": ".data-init/miar-journals-2025-process.json",
        }),
        # SciELO
        ("ScieloProcessingTask", {
            "task_id": "process_scielo",
            "input": ".data-init/scielo-2025.json",
            "output_json_path": ".data-init/scielo-2025-process.json",
        }),
        # OJS
        ("OjsProcessingTask", {
            "task_id": "ojs_tasks",
            "output_json_path": ".data-init/ojs-tasks-2025.json",
        }),
        # Organizations enrichment from DIUNE/ROR
        ("OrganizationsProcessingTask", {
            "task_id": "organizations_tasks",
            "codepa": ".data-init/orgs-onei-codepa.xlsx",
            "diune": ".data-init/orgs-onei-duine-septiembre-2025-fix.xlsx",
            "ror": ".data-init/orgs-ror-cuban-records.json",
            "output": ".data-init/orgs-tasks-2025.json",
        }),
        # # ORCID dump processing (identify Cubans)
        # ("OrcidDumpProcessingTask", {
        #     "task_id": "orcid_dump_task",
        #     "orcid_dump_path": ".data/orcid/orcid_de_cubanos",
        #     "output_json": ".data/orcid/cuban_researchers/output.json",
        #     "output_dir": ".data/orcid/cuban_researchers",
        # }),
        # ORCID mapping to Iroko schema
        ("OrcidMappingTask", {
            "task_id": "orcid_mapping_task",
            "input_folder": ".data-init/orcid/cuban_researchers",
            "output_folder": ".data-init/orcid/cuban_researchers_out",
            "diune_path": ".data-init/orgs-onei-duine-septiembre-2025-fix.xlsx",
            "person_schema_path": "docs/schema/person-v1.0.0.json",
        }),
        # Identifier fixes
        ("IdentifierFixTask", {
            "task_id": "identifiers_task",
        }),
    ]

    for task_type, config in task_queue:
        try:
            await run_task(task_type, config)
        except Exception as e:
            logger.error(f"  Task {task_type} failed with exception: {e}")
            logger.info("  Continuing to next task...")

    logger.info("  All crawler tasks complete.\n")


# ---------------------------------------------------------------------------
# 5. Verify
# ---------------------------------------------------------------------------

async def verify():
    logger.info("=" * 60)
    logger.info("STEP 5: Verification")
    logger.info("=" * 60)

    from iroko.storage import neo4j_db
    from iroko.database import AsyncSessionLocal
    from iroko.nodes.service import NodeService

    async with AsyncSessionLocal() as pg_session:
        mg_session = neo4j_db.get_session()
        try:
            service = NodeService(pg_session, mg_session)
            status = await service.get_sync_status()
            logger.info(f"  Memgraph nodes:  {status.graph_node_count}")
            logger.info(f"  PostgreSQL nodes: {status.pg_node_count}")
            if status.graph_node_count == status.pg_node_count:
                logger.info("  ✓ Databases are in sync!")
            else:
                logger.warning(
                    f"  Difference: {abs(status.graph_node_count - status.pg_node_count)} nodes"
                )
        finally:
            await mg_session.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    start = time.time()

    await drop_databases()
    await init_databases()

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, import_bulk_data)

    # Bulk import and crawler tasks both write atomically to PG+MG,
    # so no post-sync step is needed.
    await run_crawler_tasks()

    await verify()

    elapsed = time.time() - start
    logger.info(f"\nRebuild complete in {elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
