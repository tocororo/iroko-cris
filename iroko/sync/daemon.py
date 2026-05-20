import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

from iroko.tasks.schemas import TaskExecution
from iroko.tasks.task import CrawlerTask
from iroko.storage import neo4j_db
from iroko.database import AsyncSessionLocal
from iroko.nodes.service import NodeService
from .config import sync_settings

logger = logging.getLogger('iroko-cris.sync')

class GraphReconstructDaemon(CrawlerTask):
    """
    Background daemon that periodically reconstructs Memgraph from
    the PostgreSQL nodes table (PG -> MG).

    This runs on each server and ensures that after PostgreSQL replication
    (Phase 2), the local Memgraph is kept in sync.
    """

    async def execute(self, execution: TaskExecution) -> Dict[str, Any]:
        if not sync_settings.sync_enabled:
            logger.info("Sync daemon disabled (SYNC_ENABLED=false)")
            return {"status": "disabled"}

        logger.info(
            f"GraphReconstructDaemon started (interval={sync_settings.sync_interval_seconds}s)"
        )

        cycles = 0
        while True:
            try:
                async with AsyncSessionLocal() as pg_session:
                    mg_session = neo4j_db.get_session()
                    try:
                        service = NodeService(pg_session, mg_session)
                        result = await service.sync_all_to_memgraph()
                        cycles += 1
                        logger.info(
                            f"Sync cycle #{cycles}: {result.get('nodes_synced', 0)} "
                            f"nodes synced to Memgraph"
                        )
                    finally:
                        await mg_session.close()
            except asyncio.CancelledError:
                logger.info("GraphReconstructDaemon cancelled")
                break
            except Exception as e:
                logger.error(f"GraphReconstructDaemon error: {e}")

            await asyncio.sleep(sync_settings.sync_interval_seconds)

        return {
            "status": "completed",
            "cycles": cycles,
            "stopped_at": datetime.utcnow().isoformat(),
        }

    def validate_config(self) -> bool:
        return True
