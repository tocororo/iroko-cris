from neo4j import GraphDatabase
from iroko.hd2neo4j.types.mapper_types import Node, Relation


class RepositorySingleton:
    _instance = None

    def __new__(cls, url, user, password, db="neo4j"):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.url = url
            cls._instance.user = user
            cls._instance.password = password
            cls._instance.db = db
        return cls._instance


class Neo4jRepository(RepositorySingleton):
    def __init__(self, uri, user, password, db="neo4j"):
        self._driver = GraphDatabase.driver(uri, auth=(user, password), database=db)

    def _process_node_properties(self, properties: dict):
        if not bool(properties):
            return

        property_string: str = " {"
        for index, key in enumerate(properties):
            if isinstance(properties[key], int) or isinstance(properties[key], list):
                property_string += f"`{key}`: {properties[key]} "
            else:
                property_string += f'`{key}`: "{properties[key]}" '
            if index != len(properties) - 1:
                property_string += ", "
        property_string += "}"
        return property_string

    def add_node(self, node: Node):
        if node.properties is not None:
            query: str = f"MERGE (:{node.label} {self._process_node_properties(node.properties)})"
        else:
            query: str = f"MERGE(:{node.label})"
        return self._driver.execute_query(query)

    def get_node_by_properties(self, node: Node):
        """get the first match for the node search
            if the properties are empty the function will no return any value.
        Returns:
            the first node that match the search params
        """

        if not node.properties or not node.label:
            return print("Error the properties and label pf the node are mandatory for a search")
        query = f"MATCH (node:{node.label} {self._process_node_properties(node.properties)}) RETURN node"
        result = self._driver.execute_query(query)

        if len(result.records) > 1:
            print("Warning: the query return more that one results")
        return result.records[0]

    # def make_update_query_for_properties(self,query_variable:str, properties:dict):
    #     query = []
    #     for key in properties.keys():
    #         query.append(f" SET {query_variable} = ")

    def add_relation(
        self,
        relation: Relation,
    ):
        # Alternative property preparation for queries
        # origin_query = (f"MERGE (origin:{relation.start_node.label} {{id:'{relation.start_node.id}'}})")
        # origin_query += self._make_properties_queries("origin", relation.start_node.properties)
        # target_query = (f"MERGE (target:{relation.target_node.label} {{id:'{relation.target_node.id}'}})")
        # target_query += self._make_properties_queries("target", relation.target_node.properties)

        query: str = (
            f"MERGE (origin:{relation.start_node.label} {{id:'{relation.start_node.id}'}})"
            "ON CREATE"
            f"  SET origin += {self._process_node_properties(relation.start_node.properties)}"
            "ON MATCH"
            f"  SET origin += {self._process_node_properties(relation.start_node.properties)}"
            f"MERGE (target:{relation.target_node.label} {{id:'{relation.target_node.id}'}})"
            "ON CREATE"
            f"  SET target += {self._process_node_properties(relation.target_node.properties)}"
            "ON MATCH"
            f"  SET "
            f"{self._update_values("target", relation.target_node.properties)}"
        )

        # query = (origin_query + target_query)
        query += self._make_relation_query(relation)
        return self._driver.execute_query(query)

    def _update_values(self, variable: str, properties: dict):
        query = ""
        for index, key in enumerate(properties):
            if isinstance(properties[key], list) or isinstance(properties[key], int):
                query += f"{variable}.`{key}` = coalesce({variable}.`{key}`, {properties[key]})"
            else:
                query += f'{variable}.`{key}` = coalesce({variable}.`{key}`, "{properties[key]}")'

            if index < len(properties) - 1:
                query += ", "
            else:
                query += " "

        return query

    def _make_relation_query(self, relation: Relation):
        if relation.properties:
            return (
                f"MERGE (origin)-[r:{relation.label} {self._process_node_properties(relation.properties)}]->(target)"
            )
        return f"MERGE (origin)-[r:{relation.label}]->(target)"

    def drop_graph(self):
        self._driver.execute_query("MATCH (a)-[r]->() DELETE r WITH DISTINCT a DELETE a")
        # self._driver.execute_query("MATCH (a) -[r] -> () DELETE a, r ")
        self._driver.execute_query("MATCH (a) DELETE a")

    def get_graph(self):
        return self._driver.execute_query("MATCH (n) RETURN n")

    def execute_external_query(
        self,
        query,
    ):
        return self._driver.execute_query(query)

    def close(self):
        self._driver.close()

    # def update_node(self, entity_label, properties):
    #     query:str = (
    #         f"MATCH (p:{entity_label})"
    #         f""
    #     )
