from .neo4j.mapper import Mapper
from .neo4j.repository import Neo4jRepository
import json
from .mapping_config.mapping_config import (
    MappingConfig,
)
import logging


logger = logging.getLogger('iroko-cris')


class RepositoryService:
    def __init__(self, neo4j_uri:str, neo4j_user:str, neo4j_pass:str, neo4j_db:str):
        self.repository = Neo4jRepository(neo4j_uri, neo4j_user, neo4j_pass, neo4j_db)
        
    def get_repository(self):
        return self.repository

    def clean_graph_db(self):
        self.repository.drop_graph()

    def execute_external_query(self, query: str):
        upper_query = query.upper()
        if "MERGE" in upper_query or "CREATE" in upper_query or "DELETE" in upper_query or " SET " in upper_query:
            return logger.error("Only consult queries are allowed")
        elif not "RETURN" in upper_query:
            return logger.error("The query must have a return statement")
        return self.repository.execute_external_query(query)

    def get_graph(self):
        return self.repository.get_graph()


class MapperService:
    def __init__(self, mapping_config, data_to_map, repository_service:RepositoryService):
        self.mapper = Mapper(
            MappingConfig(mapping_config),
            data_to_map,
            repository_service.get_repository(),
        )

    def start_mapping(self):
        self.mapper.start()
