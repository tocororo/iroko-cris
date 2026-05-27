from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, func as sqla_func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from neo4j import AsyncSession as Neo4jSession
from uuid import UUID
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import logging
import uuid

from .models import Node
from .schemas import NodeCreate, NodeUpdate, SyncStatus

logger = logging.getLogger('iroko-cris.nodes')


def _build_label_set_query(iroko_uuid: str, labels: List[str]) -> Tuple[str, dict]:
    """Build a Cypher query to set labels on a node without APOC.

    Memgraph does not support apoc.create.setLabels, so we build
    the SET clause dynamically with label literals.
    """
    all_labels = list(set(labels + ["Node"]))
    label_part = ":".join(all_labels)
    query = f"""
    MATCH (n {{iroko_uuid: $uuid}})
    SET n{":" + label_part if label_part else ""}
    SET n._updated_at = $now
    """
    return query, {"uuid": iroko_uuid, "now": datetime.utcnow().isoformat()}


class NodeService:
    def __init__(self, db: AsyncSession, mg: Neo4jSession):
        self.db = db
        self.mg = mg

    async def _sync_to_memgraph(self, node: Node):
        """
        Syncs Node + Labels + Relationships to Memgraph.
        Uses plain Cypher (no APOC) for Memgraph compatibility.
        """
        try:
            node_uuid = str(node.iroko_uuid)

            # 1. Merge Node base
            merge_query = """
            MERGE (n:Node {iroko_uuid: $uuid})
            SET n.name = $name
            SET n._updated_at = $now
            RETURN n
            """
            await self.mg.run(merge_query, uuid=node_uuid, name=node.name, now=datetime.utcnow().isoformat())

            # 2. Apply Labels (no APOC — dynamic query building)
            label_query, label_params = _build_label_set_query(node_uuid, node.labels)
            await self.mg.run(label_query, label_params)

            # 3. Sync node properties from data JSON
            if node.data:
                set_clauses = []
                data_params = {"uuid": node_uuid}
                for i, (key, value) in enumerate(node.data.items()):
                    sanitized = key.replace('`', '').replace('\\', '')
                    param = f"data_{i}"
                    set_clauses.append(f"n.`{sanitized}` = ${param}")
                    data_params[param] = value
                if set_clauses:
                    prop_query = f"""
                    MATCH (n:Node {{iroko_uuid: $uuid}})
                    SET {', '.join(set_clauses)}
                    """
                    await self.mg.run(prop_query, data_params)

            # 4. Sync Relationships (reset approach) — only when non-empty
            if node.relationships:
                delete_rels_query = """
                MATCH (n:Node {iroko_uuid: $uuid})-[r]->()
                DELETE r
                """
                await self.mg.run(delete_rels_query, uuid=node_uuid)

                for rel in node.relationships:
                    if not isinstance(rel, dict):
                        rel = rel.model_dump()

                    rel_type = rel['type']
                    edge_query = f"""
                    MATCH (source:Node {{iroko_uuid: $source_uuid}})
                    MERGE (target:Node {{iroko_uuid: $target_uuid}})
                    MERGE (source)-[r:{rel_type}]->(target)
                    SET r += $props
                    """
                    await self.mg.run(edge_query, {
                        "source_uuid": node_uuid,
                        "target_uuid": str(rel['target_uuid']),
                        "props": rel.get('properties', {})
                    })

            logger.debug(f"Synced node {node.iroko_uuid} to Memgraph")

        except Exception as e:
            logger.error(f"Failed to sync node {node.iroko_uuid}: {e}")
            raise e

    async def create_node(self, node_in: NodeCreate) -> Node:
        db_node = Node(
            name=node_in.name,
            labels=node_in.labels,
            data=node_in.data,
            relationships=[r.model_dump() for r in node_in.relationships]
        )
        self.db.add(db_node)
        await self.db.commit()
        await self.db.refresh(db_node)

        try:
            await self._sync_to_memgraph(db_node)
        except Exception as e:
            logger.error("PG saved, MG failed")
            raise e

        return db_node

    async def update_node(self, uuid: UUID, node_in: NodeUpdate) -> Optional[Node]:
        result = await self.db.execute(select(Node).where(Node.iroko_uuid == uuid))
        db_node = result.scalar_one_or_none()

        if not db_node:
            return None

        db_node.name = node_in.name
        db_node.labels = node_in.labels
        db_node.data = node_in.data
        db_node.relationships = [r.model_dump() for r in node_in.relationships]

        await self.db.commit()
        await self.db.refresh(db_node)

        await self._sync_to_memgraph(db_node)
        return db_node

    async def get_node(self, uuid: UUID) -> Optional[Node]:
        result = await self.db.execute(select(Node).where(Node.iroko_uuid == uuid))
        return result.scalar_one_or_none()

    async def search_nodes(self, query_str: str, limit: int = 50) -> List[Node]:
        query = select(Node).where(
            Node.name.ilike(f"%{query_str}%")
        ).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete_node(self, uuid: UUID) -> bool:
        result = await self.db.execute(select(Node).where(Node.iroko_uuid == uuid))
        db_node = result.scalar_one_or_none()

        if not db_node:
            return False

        await self.db.delete(db_node)
        await self.db.commit()

        mg_query = "MATCH (n:Node {iroko_uuid: $uuid}) DETACH DELETE n"
        await self.mg.run(mg_query, uuid=str(uuid))

        return True

    # ------------------------------------------------------------------
    # Sync: PG -> Memgraph (reconstruct graph from nodes table)
    # ------------------------------------------------------------------

    async def sync_all_to_memgraph(self, batch_size: int = 500) -> dict:
        """Full graph reconstruction: iterate all nodes in PG and recreate
        them in Memgraph. Old graph data is DETACH DELETEd first."""
        logger.warning("Starting full PG -> Memgraph sync (graph will be rebuilt)")

        count_result = await self.db.execute(select(sqla_func.count(Node.iroko_uuid)))
        total = count_result.scalar() or 0

        if total == 0:
            return {"status": "success", "nodes_synced": 0, "message": "No nodes in PG"}

        # Clear existing graph
        await self.mg.run("MATCH (n:Node) DETACH DELETE n")

        synced = 0
        offset = 0
        while offset < total:
            result = await self.db.execute(
                select(Node).order_by(Node.iroko_uuid).offset(offset).limit(batch_size)
            )
            batch = result.scalars().all()
            for node in batch:
                try:
                    await self._sync_to_memgraph(node)
                    synced += 1
                except Exception as e:
                    logger.error(f"Failed to sync node {node.iroko_uuid}: {e}")
            offset += batch_size
            logger.info(f"Synced {synced}/{total} nodes to Memgraph")

        return {"status": "success", "nodes_synced": synced, "total_in_pg": total}

    # ------------------------------------------------------------------
    # Sync: Memgraph -> PG (import from graph into nodes table)
    # ------------------------------------------------------------------

    async def _fetch_graph_node(self, mg_uuid: str) -> Optional[dict]:
        """Fetch a single node from Memgraph by iroko_uuid."""
        query = """
        MATCH (n {iroko_uuid: $uuid})
        OPTIONAL MATCH (n)-[r]->(target)
        WHERE target.iroko_uuid IS NOT NULL
        WITH n, r, target
        RETURN
            n.iroko_uuid as uuid,
            n.name as name,
            labels(n) as labels,
            properties(n) as all_props,
            collect(CASE WHEN r IS NOT NULL THEN {
                target_uuid: target.iroko_uuid,
                type: type(r),
                properties: properties(r)
            } ELSE NULL END) as relationships
        """
        result = await self.mg.run(query, uuid=mg_uuid)
        record = await result.single()
        if not record:
            return None
        return self._record_to_row(record)

    async def sync_single_from_memgraph(self, mg_uuid: str) -> Optional[Node]:
        """Import a single node from Memgraph into the nodes table."""
        row = await self._fetch_graph_node(mg_uuid)
        if not row:
            logger.warning(f"Node {mg_uuid} not found in Memgraph")
            return None
        return await self._upsert_node_row(row)

    async def sync_from_memgraph(self, batch_size: int = 500, since: Optional[datetime] = None) -> dict:
        """Bulk import nodes from Memgraph into PostgreSQL nodes table.

        If ``since`` is provided, only nodes with ``_updated_at`` after that
        time are imported (incremental sync).
        """
        if since:
            logger.info(f"Starting incremental Memgraph -> PG sync (since {since.isoformat()})")
            query = """
            MATCH (n)
            WHERE n.iroko_uuid IS NOT NULL
              AND n.name IS NOT NULL
              AND n._updated_at IS NOT NULL
              AND n._updated_at >= $since
            OPTIONAL MATCH (n)-[r]->(target)
            WHERE target.iroko_uuid IS NOT NULL
            WITH n, r, target
            RETURN
                n.iroko_uuid as uuid,
                n.name as name,
                labels(n) as labels,
                properties(n) as all_props,
                collect(CASE WHEN r IS NOT NULL THEN {
                    target_uuid: target.iroko_uuid,
                    type: type(r),
                    properties: properties(r)
                } ELSE NULL END) as relationships
            """
            result = await self.mg.run(query, since=since.isoformat())
        else:
            logger.info("Starting full Memgraph -> PG sync")
            query = """
            MATCH (n)
            WHERE n.iroko_uuid IS NOT NULL AND n.name IS NOT NULL
            OPTIONAL MATCH (n)-[r]->(target)
            WHERE target.iroko_uuid IS NOT NULL
            WITH n, r, target
            RETURN
                n.iroko_uuid as uuid,
                n.name as name,
                labels(n) as labels,
                properties(n) as all_props,
                collect(CASE WHEN r IS NOT NULL THEN {
                    target_uuid: target.iroko_uuid,
                    type: type(r),
                    properties: properties(r)
                } ELSE NULL END) as relationships
            """
            result = await self.mg.run(query)

        processed = 0
        upsert_batch = []

        async for record in result:
            try:
                row = self._record_to_row(record)
                if row:
                    upsert_batch.append(row)
                if len(upsert_batch) >= batch_size:
                    await self._perform_batch_upsert(upsert_batch)
                    processed += len(upsert_batch)
                    upsert_batch = []
                    logger.info(f"Imported {processed} nodes from Memgraph...")
            except Exception as e:
                logger.error(f"Error processing record: {e}")
                continue

        if upsert_batch:
            await self._perform_batch_upsert(upsert_batch)
            processed += len(upsert_batch)

        return {"status": "success", "nodes_imported": processed}

    def _record_to_row(self, record) -> Optional[dict]:
        """Convert a Memgraph record to a nodes table row dict."""
        try:
            uid_str = record.get('uuid')
            name = record.get('name')
            if not uid_str or not name:
                return None

            labels = list(record.get('labels', []))
            all_props = dict(record.get('all_props', {}))
            rels_raw = list(record.get('relationships', []))

            relationships = [r for r in rels_raw if r is not None]
            data_payload = {k: v for k, v in all_props.items()
                            if k not in ('iroko_uuid', 'name', '_updated_at')}

            return {
                "iroko_uuid": uuid.UUID(str(uid_str)),
                "name": name,
                "labels": labels,
                "data": data_payload,
                "relationships": relationships,
            }
        except Exception as e:
            logger.error(f"Error converting record: {e}")
            return None

    async def _upsert_node_row(self, row: dict) -> Node:
        """Upsert a single node row into PG and return the Node."""
        stmt = pg_insert(Node).values(**row)
        update_stmt = stmt.on_conflict_do_update(
            index_elements=['iroko_uuid'],
            set_={
                "name": stmt.excluded.name,
                "labels": stmt.excluded.labels,
                "data": stmt.excluded.data,
                "relationships": stmt.excluded.relationships,
            }
        )
        await self.db.execute(update_stmt)
        await self.db.commit()

        result = await self.db.execute(
            select(Node).where(Node.iroko_uuid == row["iroko_uuid"])
        )
        return result.scalar_one()

    async def _perform_batch_upsert(self, rows: List[dict]):
        if not rows:
            return

        stmt = pg_insert(Node).values(rows)
        update_stmt = stmt.on_conflict_do_update(
            index_elements=['iroko_uuid'],
            set_={
                "name": stmt.excluded.name,
                "labels": stmt.excluded.labels,
                "data": stmt.excluded.data,
                "relationships": stmt.excluded.relationships,
            }
        )
        await self.db.execute(update_stmt)
        await self.db.commit()

    # ------------------------------------------------------------------
    # Sync status
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Write methods: atomic PG + MG operations
    # ------------------------------------------------------------------

    async def merge_node(
        self,
        iroko_uuid: Optional[UUID] = None,
        name: Optional[str] = None,
        labels: Optional[List[str]] = None,
        data: Optional[Dict[str, Any]] = None,
        relationships: Optional[List[Dict[str, Any]]] = None,
    ) -> Node:
        """Upsert a node in PG and sync to MG. Generates UUID if not provided.

        If iroko_uuid is provided and the node exists in MG, the provided
        ``data`` dict is merged with the existing MG properties so that
        PG always holds the complete property set.
        """
        if iroko_uuid and data is not None:
            result = await self.mg.run(
                "MATCH (n {iroko_uuid: $uuid}) RETURN properties(n) as props",
                uuid=str(iroko_uuid))
            rec = await result.single()
            if rec:
                existing = dict(rec["props"])
                for k in list(existing.keys()):
                    if k.startswith('_'):
                        del existing[k]
                merged = existing.copy()
                merged.update(data)
                data = merged

        row = {
            "iroko_uuid": iroko_uuid or uuid.uuid4(),
            "name": name or "",
            "labels": labels or [],
            "data": data or {},
            "relationships": relationships or [],
        }
        node = await self._upsert_node_row(row)
        await self._sync_to_memgraph(node)
        return node

    async def set_node_properties(
        self,
        iroko_uuid: UUID,
        properties: Dict[str, Any],
    ) -> Optional[Node]:
        """Merge properties into a node's data JSON and sync to MG."""
        result = await self.db.execute(select(Node).where(Node.iroko_uuid == iroko_uuid))
        node = result.scalar_one_or_none()
        if not node:
            return None

        current_data = dict(node.data) if node.data else {}
        current_data.update(properties)
        node.data = current_data
        await self.db.commit()
        await self.db.refresh(node)

        await self._sync_to_memgraph(node)
        return node

    async def merge_relationship(
        self,
        from_uuid: UUID,
        to_uuid: UUID,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> tuple[Optional[Node], Optional[Node]]:
        from_node = await self.get_node(from_uuid)
        to_node = await self.get_node(to_uuid)
        if not from_node or not to_node:
            raise ValueError(f"Cannot find nodes: from={from_uuid} to={to_uuid}")

        rel_item = {
            "target_uuid": str(to_uuid),
            "type": rel_type,
            "properties": properties or {},
        }
        current_rels = list(from_node.relationships) if from_node.relationships else []
        existing_idx = None
        for i, rel in enumerate(current_rels):
            d = rel if isinstance(rel, dict) else rel.model_dump() if hasattr(rel, 'model_dump') else {}
            if d.get("target_uuid") == str(to_uuid) and d.get("type") == rel_type:
                existing_idx = i
                break
        if existing_idx is not None:
            current_rels[existing_idx] = rel_item
        else:
            current_rels.append(rel_item)

        from_node.relationships = current_rels
        await self.db.commit()
        await self.db.refresh(from_node)

        mg_query = f"""
        MATCH (source:Node {{iroko_uuid: $from_uuid}})
        MATCH (target:Node {{iroko_uuid: $to_uuid}})
        MERGE (source)-[r:{rel_type}]->(target)
        SET r += $props
        """
        await self.mg.run(mg_query, from_uuid=str(from_uuid), to_uuid=str(to_uuid), props=properties or {})
        return from_node, to_node

    async def delete_relationship(
        self,
        from_uuid: UUID,
        to_uuid: UUID,
        rel_type: str,
    ) -> Optional[Node]:
        from_node = await self.get_node(from_uuid)
        if not from_node:
            return None

        current_rels = list(from_node.relationships) if from_node.relationships else []
        from_node.relationships = [
            rel for rel in current_rels
            if not (
                (rel.get("target_uuid") if isinstance(rel, dict) else str(rel.target_uuid)) == str(to_uuid)
                and (rel.get("type") if isinstance(rel, dict) else rel.type) == rel_type
            )
        ]
        await self.db.commit()
        await self.db.refresh(from_node)

        mg_query = """
        MATCH (source:Node {iroko_uuid: $from_uuid})-[r]->(target:Node {iroko_uuid: $to_uuid})
        WHERE type(r) = $rel_type
        DELETE r
        """
        await self.mg.run(mg_query, from_uuid=str(from_uuid), to_uuid=str(to_uuid), rel_type=rel_type)
        return from_node

    async def bulk_merge_nodes(
        self,
        nodes: List[Dict[str, Any]],
        batch_size: int = 500,
    ) -> dict:
        """Batch upsert nodes in PG and sync each to MG."""
        total = len(nodes)
        synced = 0
        for i in range(0, total, batch_size):
            batch = nodes[i:i + batch_size]
            pg_rows = []
            for nd in batch:
                pg_rows.append({
                    "iroko_uuid": nd.get("iroko_uuid", uuid.uuid4()),
                    "name": nd.get("name", ""),
                    "labels": nd.get("labels", []),
                    "data": nd.get("data", {}),
                    "relationships": nd.get("relationships", []),
                })
            await self._perform_batch_upsert(pg_rows)
            for row in pg_rows:
                node = Node(**row)
                await self._sync_to_memgraph(node)
                synced += 1
        return {"status": "success", "nodes_synced": synced}

    async def get_sync_status(self) -> SyncStatus:
        """Return counts from both stores for monitoring."""
        pg_result = await self.db.execute(select(sqla_func.count(Node.iroko_uuid)))
        pg_count = pg_result.scalar() or 0

        pg_ts_result = await self.db.execute(
            select(sqla_func.max(Node.updated_at))
        )
        pg_updated_at = pg_ts_result.scalar()

        mg_result = await self.mg.run(
            "MATCH (n) RETURN count(n) as cnt, max(n._updated_at) as max_ts"
        )
        mg_record = await mg_result.single()
        mg_count = mg_record["cnt"] if mg_record else 0
        mg_updated_at_raw = mg_record["max_ts"] if mg_record else None
        mg_updated_at: Optional[datetime] = None
        if mg_updated_at_raw:
            try:
                mg_updated_at = datetime.fromisoformat(mg_updated_at_raw)
            except (ValueError, TypeError):
                mg_updated_at = None

        return SyncStatus(
            pg_node_count=pg_count,
            graph_node_count=mg_count,
            pg_updated_at=pg_updated_at,
            graph_updated_at=mg_updated_at,
        )


class LegacySyncService:
    def __init__(self, db: AsyncSession, mg: Neo4jSession):
        self.db = db
        self.mg = mg

    async def get_invalid_nodes(self, limit: int = 100) -> List[dict]:
        query = """
        MATCH (n)
        WHERE n.iroko_uuid IS NULL OR n.name IS NULL
        RETURN id(n) as id, labels(n) as labels, properties(n) as props
        LIMIT $limit
        """
        result = await self.mg.run(query, limit=limit)
        records = await result.data()

        return [{
            "graph_id": r['id'],
            "labels": r['labels'],
            "properties": r['props']
        } for r in records]

    async def import_from_memgraph(self, batch_size: int = 1000) -> dict:
        logger.info("Starting Legacy Import with Labels...")
        query = """
        MATCH (n)
        WHERE n.iroko_uuid IS NOT NULL AND n.name IS NOT NULL

        OPTIONAL MATCH (n)-[r]->(target)
        WHERE target.iroko_uuid IS NOT NULL

        WITH n, r, target

        RETURN
            n.iroko_uuid as uuid,
            n.name as name,
            labels(n) as labels,
            properties(n) as all_props,
            collect(CASE WHEN r IS NOT NULL THEN {
                target_uuid: target.iroko_uuid,
                type: type(r),
                properties: properties(r)
            } ELSE NULL END) as relationships
        """

        result = await self.mg.run(query)

        processed_count = 0
        upsert_batch = []

        async for record in result:
            try:
                uid_str = record['uuid']
                name = record['name']
                labels = list(record['labels'])
                all_props = dict(record['all_props'])
                rels_raw = list(record['relationships'])

                relationships = [r for r in rels_raw if r is not None]
                data_payload = {k: v for k, v in all_props.items()
                                if k not in ('iroko_uuid', 'name', '_updated_at')}

                row = {
                    "iroko_uuid": uuid.UUID(str(uid_str)),
                    "name": name,
                    "labels": labels,
                    "data": data_payload,
                    "relationships": relationships,
                }
                upsert_batch.append(row)

                if len(upsert_batch) >= batch_size:
                    await self._perform_batch_upsert(upsert_batch)
                    processed_count += len(upsert_batch)
                    upsert_batch = []
                    logger.info(f"Imported {processed_count} nodes...")

            except Exception as e:
                logger.error(f"Error processing record: {e}")
                continue

        if upsert_batch:
            await self._perform_batch_upsert(upsert_batch)
            processed_count += len(upsert_batch)

        return {"status": "success", "nodes_processed": processed_count}

    async def _perform_batch_upsert(self, rows: List[dict]):
        if not rows:
            return

        stmt = pg_insert(Node).values(rows)
        update_stmt = stmt.on_conflict_do_update(
            index_elements=['iroko_uuid'],
            set_={
                "name": stmt.excluded.name,
                "labels": stmt.excluded.labels,
                "data": stmt.excluded.data,
                "relationships": stmt.excluded.relationships,
            }
        )
        await self.db.execute(update_stmt)
        await self.db.commit()