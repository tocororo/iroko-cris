import json
import uuid as uuid_pkg
from datetime import datetime
from neo4j import GraphDatabase
from sqlalchemy import create_engine, text
from iroko.hd2neo4j.types.mapper_types import Node, Relation


class RepositorySingleton:
    _instance = None

    def __new__(cls, url, user, password, db="neo4j", pg_url=None):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.url = url
            cls._instance.user = user
            cls._instance.password = password
            cls._instance.db = db
            cls._instance.pg_url = pg_url
        return cls._instance


class Neo4jRepository(RepositorySingleton):
    def __init__(self, uri, user, password, db="neo4j", pg_url=None):
        if not hasattr(self, '_driver'):
            self._driver = GraphDatabase.driver(uri, auth=(user, password), database=db)
        if pg_url and not hasattr(self, '_pg_engine'):
            sync_url = pg_url.replace("+asyncpg", "+psycopg2")
            self._pg_engine = create_engine(sync_url, pool_pre_ping=True)
        if not hasattr(self, '_pg_engine'):
            self._pg_engine = None

    # ------------------------------------------------------------------
    # Cypher literal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cypher_literal(value):
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int) or isinstance(value, float):
            return str(value)
        if isinstance(value, list):
            items = ", ".join(Neo4jRepository._cypher_literal(v) for v in value)
            return f"[{items}]"
        if value is None:
            return "null"
        escaped = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ").replace("\t", " ")
        return f'"{escaped}"'

    def _process_node_properties(self, properties: dict):
        if not bool(properties):
            return
        parts = []
        for key in properties:
            parts.append(f"`{key}`: {self._cypher_literal(properties[key])}")
        return " {" + ", ".join(parts) + "}"

    # ------------------------------------------------------------------
    # PG upsert helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_pg_row(iroko_uuid: str, label: str, properties: dict):
        name = properties.get("name") or label
        data = {k: v for k, v in properties.items() if k not in ("iroko_uuid", "name", "_updated_at")}
        return {
            "iroko_uuid": iroko_uuid,
            "name": name,
            "labels": [label],
            "data": json.dumps(data, default=str),
            "relationships": "[]",
        }

    def _pg_upsert_node(self, row: dict):
        if not self._pg_engine:
            return
        stmt = text("""
            INSERT INTO nodes (iroko_uuid, name, labels, data, relationships)
            VALUES (:iroko_uuid, :name, CAST(:labels AS text[]), CAST(:data AS json), CAST(:relationships AS json))
            ON CONFLICT (iroko_uuid) DO UPDATE SET
                name = EXCLUDED.name,
                labels = EXCLUDED.labels,
                data = EXCLUDED.data
        """)
        with self._pg_engine.begin() as conn:
            conn.execute(stmt, row)

    def _pg_append_relationship(self, from_uuid: str, to_uuid: str, rel_type: str, rel_props: dict):
        if not self._pg_engine:
            return
        rel_item = json.dumps({"target_uuid": to_uuid, "type": rel_type, "properties": rel_props}, default=str)
        stmt = text(f"""
            UPDATE nodes
            SET relationships = CAST(relationships AS jsonb) || '{rel_item}'::jsonb
            WHERE iroko_uuid = :from_uuid
              AND NOT CAST(relationships AS jsonb) @> '[{{"target_uuid": "{to_uuid}", "type": "{rel_type}"}}]'::jsonb
        """)
        with self._pg_engine.begin() as conn:
            conn.execute(stmt, {"from_uuid": from_uuid})

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def add_node(self, node: Node):
        iroko_uuid = str(uuid_pkg.uuid4())
        now = datetime.utcnow().isoformat()
        node.properties.setdefault("iroko_uuid", iroko_uuid)
        node.properties.setdefault("_updated_at", now)

        query = f"MERGE (:{node.label} {self._process_node_properties(node.properties)})"
        result = self._driver.execute_query(query)
        if self._pg_engine:
            row = self._extract_pg_row(iroko_uuid, node.label, node.properties)
            self._pg_upsert_node(row)
        return result

    def add_relation(self, relation: Relation):
        now = datetime.utcnow().isoformat()

        origin_uuid = str(uuid_pkg.uuid4())
        target_uuid = str(uuid_pkg.uuid4())
        relation.start_node.properties.setdefault("iroko_uuid", origin_uuid)
        relation.start_node.properties.setdefault("_updated_at", now)
        relation.target_node.properties.setdefault("iroko_uuid", target_uuid)
        relation.target_node.properties.setdefault("_updated_at", now)

        origin_id = str(relation.start_node.id).replace("'", "\\'")
        target_id = str(relation.target_node.id).replace("'", "\\'")

        origin_props = self._process_node_properties(relation.start_node.properties) or ""
        target_props = self._process_node_properties(relation.target_node.properties) or ""

        query = (
            f"MERGE (origin:{relation.start_node.label} {{id:'{origin_id}'}})"
            f"ON CREATE SET origin += {origin_props}"
            f"ON MATCH SET origin += {origin_props}"
            f"MERGE (target:{relation.target_node.label} {{id:'{target_id}'}})"
            f"ON CREATE SET target += {target_props}"
            f"ON MATCH SET target += {target_props}"
        )
        query += self._make_relation_query(relation)
        result = self._driver.execute_query(query)

        if self._pg_engine:
            self._pg_upsert_node(self._extract_pg_row(origin_uuid, relation.start_node.label, relation.start_node.properties))
            self._pg_upsert_node(self._extract_pg_row(target_uuid, relation.target_node.label, relation.target_node.properties))
            self._pg_append_relationship(origin_uuid, target_uuid, relation.label, relation.properties)

        return result

    # ------------------------------------------------------------------
    # Update helpers
    # ------------------------------------------------------------------

    def _update_values(self, variable: str, properties: dict):
        parts = []
        for key in properties:
            parts.append(f"{variable}.`{key}` = coalesce({variable}.`{key}`, {self._cypher_literal(properties[key])})")
        return ", ".join(parts) + " " if parts else ""

    def _make_relation_query(self, relation: Relation):
        if relation.properties:
            return f"MERGE (origin)-[r:{relation.label} {self._process_node_properties(relation.properties)}]->(target)"
        return f"MERGE (origin)-[r:{relation.label}]->(target)"

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def get_node_by_properties(self, node: Node):
        if not node.properties or not node.label:
            return print("Error the properties and label pf the node are mandatory for a search")
        query = f"MATCH (node:{node.label} {self._process_node_properties(node.properties)}) RETURN node"
        result = self._driver.execute_query(query)
        if len(result.records) > 1:
            print("Warning: the query return more that one results")
        return result.records[0]

    def drop_graph(self):
        self._driver.execute_query("MATCH (a)-[r]->() DELETE r WITH DISTINCT a DELETE a")
        self._driver.execute_query("MATCH (a) DELETE a")

    def get_graph(self):
        return self._driver.execute_query("MATCH (n) RETURN n")

    def execute_external_query(self, query):
        return self._driver.execute_query(query)

    def close(self):
        self._driver.close()
        if self._pg_engine:
            self._pg_engine.dispose()
