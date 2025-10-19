from iroko.hd2neo4j.services import RepositoryService, MapperService
import json

from iroko.config import app_settings
from neo4j import GraphDatabase


r_service: RepositoryService = RepositoryService(
    app_settings.neo4j_uri, app_settings.neo4j_username, app_settings.neo4j_password, app_settings.neo4j_database
)

def queries():
    session = GraphDatabase.driver(
                app_settings.neo4j_uri,
                auth=(
                    app_settings.neo4j_username,
                    app_settings.neo4j_password
                ),
                database=app_settings.neo4j_database
            ).session()



    session.run("""MATCH (t:Term)
    CALL apoc.create.addLabels([t], [t.vocabulary]) YIELD node
    SET node.name = node.description
    REMOVE node.description
    RETURN count(node) AS updatedNodes
    """)

    session.run("""MATCH (n:INDEXES)
    REMOVE n:INDEXES
    SET n:Index""")


    session.run("""MATCH (n:LICENCES)
    REMOVE n:LICENCES
    SET n:Licence""")


    session.run("""MATCH (n:SUBJECTS)
    REMOVE n:SUBJECTS
    SET n:Subject""")


    session.run("""MATCH (n)-[r:CLASSIFIED_BY]->(s:Subject)
    CALL apoc.create.relationship(n, 'HAS_SUBJECT', r{.*}, s) YIELD rel
    DELETE r
    RETURN count(rel) AS renamedCount""")


    session.run("""MATCH (n)-[r:LABEL]->(s:Language)
    CALL apoc.create.relationship(n, 'HAS_LANGUAGE', r{.*}, s) YIELD rel
    DELETE r
    RETURN count(rel) AS renamedCount""")



    session.run("""MATCH (n)-[r:CLASSIFIED_BY]->(s:Index)
    CALL apoc.create.relationship(n, 'IN_INDEX', r{.*}, s) YIELD rel
    DELETE r
    RETURN count(rel) AS renamedCount""")


    session.run("""MATCH (n)-[r:CLASSIFIED_BY]->(s:Licence)
    CALL apoc.create.relationship(n, 'HAS_LICENCE', r{.*}, s) YIELD rel
    DELETE r
    RETURN count(rel) AS renamedCount""")


    session.close()



#organizations
config:dict
data:dict
with open('docs/schema/organization-v1.0.0-map.json', 'r') as file:
    config = json.load(file)
    with open('.data-init/organizations.json', 'r') as f2:
        data = json.load(f2)
        m_service: MapperService = MapperService(
            mapping_config=config,
            repository_service=r_service,
            data_to_map=data
        )

        m_service.start_mapping()


# sources
config:dict
data:dict
with open('docs/schema/source-v1.0.0-map.json', 'r') as file:
    config = json.load(file)
    with open('.data-init/sources.json', 'r') as f2:
        data = json.load(f2)
        m_service: MapperService = MapperService(
            mapping_config=config,
            repository_service=r_service,
            data_to_map=data
        )

        m_service.start_mapping()

queries()

# #outputs
# config:dict
# data:dict
# with open('docs/schema/output-v1.0.0-map.json', 'r') as file:
#     config = json.load(file)
#     with open('.data-init/outputs.json', 'r') as f2:
#         data = json.load(f2)
#         m_service: MapperService = MapperService(
#             mapping_config=config,
#             repository_service=r_service,
#             data_to_map=data
#         )

#         m_service.start_mapping()




# # persons
# config:dict
# data:dict
# with open('docs/schema/person-v1.0.0-map.json', 'r') as file:
#     config = json.load(file)
#     with open('.data-init/persons.json', 'r') as f2:
#         data = json.load(f2)
#         m_service: MapperService = MapperService(
#             mapping_config=config,
#             repository_service=r_service,
#             data_to_map=data
#         )

#         m_service.start_mapping()

