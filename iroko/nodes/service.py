from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from neo4j import AsyncSession as Neo4jSession
from uuid import UUID
from typing import List, Optional
import logging
import uuid

from .models import Node
from .schemas import NodeCreate, NodeUpdate

logger = logging.getLogger('iroko-cris.nodes')

class NodeService:
    def __init__(self, db: AsyncSession, mg: Neo4jSession):
        self.db = db
        self.mg = mg

    async def _sync_to_memgraph(self, node: Node):
        """
        Syncs Node + Labels + Relationships to Memgraph.
        """
        try:
            # 1. Merge Node (Idempotent creation base)
            # We use a base label :Node for easy retrieval by UUID, 
            # specific labels are applied next.
            merge_query = """
            MERGE (n:Node {iroko_uuid: $uuid})
            SET n.name = $name
            RETURN n
            """
            await self.mg.run(merge_query, uuid=str(node.iroko_uuid), name=node.name)

            # 2. Apply Labels
            # We use APOC to dynamically overwrite labels.
            # This ensures if we remove a label in Postgres, it's removed in Graph.
            # We always keep the 'Node' label for system indexing.
            all_labels = list(set(node.labels + ["Node"]))
            
            label_query = """
            MATCH (n:Node {iroko_uuid: $uuid})
            CALL apoc.create.setLabels(n, $labels) YIELD node
            RETURN node
            """
            await self.mg.run(label_query, uuid=str(node.iroko_uuid), labels=all_labels)

            # 3. Sync Relationships (Reset approach)
            # Remove all outgoing edges
            delete_rels_query = """
            MATCH (n:Node {iroko_uuid: $uuid})-[r]->()
            DELETE r
            """
            await self.mg.run(delete_rels_query, uuid=str(node.iroko_uuid))

            # Recreate edges from JSON blueprint
            if node.relationships:
                for rel in node.relationships:
                    if not isinstance(rel, dict):
                        rel = rel.model_dump()

                    rel_type = rel['type']
                    # Note: target must exist (or be created as ghost node)
                    edge_query = f"""
                    MATCH (source:Node {{iroko_uuid: $source_uuid}})
                    MERGE (target:Node {{iroko_uuid: $target_uuid}})
                    MERGE (source)-[r:{rel_type}]->(target)
                    SET r += $props
                    """
                    await self.mg.run(edge_query, {
                        "source_uuid": str(node.iroko_uuid),
                        "target_uuid": str(rel['target_uuid']),
                        "props": rel.get('properties', {})
                    })

            # TODO: add node properties based on a config depending on label.
            # 4. add sync node properties depending on label config. 



            logger.debug(f"Synced node {node.iroko_uuid} to Memgraph")

        except Exception as e:
            logger.error(f"Failed to sync node {node.iroko_uuid}: {e}")
            raise e

    async def create_node(self, node_in: NodeCreate) -> Node:
        # 1. Save to Postgres
        db_node = Node(
            name=node_in.name,
            labels=node_in.labels,
            data=node_in.data,
            relationships=[r.model_dump() for r in node_in.relationships]
        )
        self.db.add(db_node)
        await self.db.commit()
        await self.db.refresh(db_node)

        # 2. Sync to Memgraph
        try:
            await self._sync_to_memgraph(db_node)
        except Exception as e:
            # Basic rollback logic could go here
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


class LegacySyncService:
    def __init__(self, db: AsyncSession, mg: Neo4jSession):
        self.db = db
        self.mg = mg

    async def get_invalid_nodes(self, limit: int = 100) -> List[dict]:
        """
        Nodes missing iroko_uuid or name.
        """
        query = """
        MATCH (n)
        WHERE n.iroko_uuid IS NULL OR n.name IS NULL
        RETURN elementId(n) as id, labels(n) as labels, properties(n) as props
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
        """
        Hydrate PG from Memgraph. 
        Now includes extracting labels(n) and storing them in the labels column.
        """
        # We fetch labels(n) in the query
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

        logger.info("Starting Legacy Import with Labels...")
        result = await self.mg.run(query)
        
        processed_count = 0
        upsert_batch = []
        
        async for record in result:
            try:
                uid_str = record['uuid']
                name = record['name']
                labels = record['labels'] # List of strings from Memgraph
                all_props = record['all_props']
                rels_raw = record['relationships']

                # Clean relationships
                relationships = [r for r in rels_raw if r is not None]

                # Data payload = props - (uuid, name). 
                # Labels are stored in their own column, not in 'data'.
                data_payload = {k: v for k, v in all_props.items() if k not in ['iroko_uuid', 'name']}

                row = {
                    "iroko_uuid": uuid.UUID(str(uid_str)),
                    "name": name,
                    "labels": labels, # Save labels to Postgres
                    "data": data_payload,
                    "relationships": relationships
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
                "labels": stmt.excluded.labels, # Update labels if they changed
                "data": stmt.excluded.data,
                "relationships": stmt.excluded.relationships
            }
        )

        await self.db.execute(update_stmt)
        await self.db.commit()