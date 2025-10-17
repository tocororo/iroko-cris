from iroko.hd2neo4j.services import RepositoryService, MapperService
import json

from iroko.config import app_settings

r_service: RepositoryService = RepositoryService(
    app_settings.neo4j_uri, app_settings.neo4j_username, app_settings.neo4j_password, app_settings.neo4j_database
)



#outputs
config:dict
data:dict
with open('docs/schema/output-v1.0.0-map.json', 'r') as file:
    config = json.load(file)
    with open('.data-init/outputs.json', 'r') as f2:
        data = json.load(f2)
        m_service: MapperService = MapperService(
            mapping_config=config,
            repository_service=r_service,
            data_to_map=data
        )

        m_service.start_mapping()


# # sources
# config:dict
# data:dict
# with open('docs/schema/source-v1.0.0-map.json', 'r') as file:
#     config = json.load(file)
#     with open('.data-init/sources.json', 'r') as f2:
#         data = json.load(f2)
#         m_service: MapperService = MapperService(
#             mapping_config=config,
#             repository_service=r_service,
#             data_to_map=data
#         )

#         m_service.start_mapping()


# #organizations
# config:dict
# data:dict
# with open('docs/schema/organization-v1.0.0-map.json', 'r') as file:
#     config = json.load(file)
#     with open('.data-init/organizations.json', 'r') as f2:
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

