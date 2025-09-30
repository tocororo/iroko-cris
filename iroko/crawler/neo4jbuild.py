from hd2neo4j.services import RepositoryService, MapperService
import json

r_service: RepositoryService = RepositoryService(
    "bolt://localhost:7687", "neo4j", "1qazxsw2", "iroko"
)


config:dict
data:dict

# # sources
# with open('docs/schema/source-v1.0.0-map.json', 'r') as file:
#     config = json.load(file)
# with open('.data/rdf/sources.json', 'r') as f2:
#     data = json.load(f2)

# # #persons
# with open('docs/schema/person-v1.0.0-map.json', 'r') as file:
#     config = json.load(file)
# with open('.data/rdf/persons.json', 'r') as f2:
#     data = json.load(f2)

# #organizations
# with open('docs/schema/organization-v1.0.0-map.json', 'r') as file:
#     config = json.load(file)
# with open('.data/rdf/organizations.json', 'r') as f2:
#     data = json.load(f2)

#outputs
with open('docs/schema/output-v1.0.0-map.json', 'r') as file:
    config = json.load(file)
with open('.data/rdf/outputs.json', 'r') as f2:
    data = json.load(f2)


m_service: MapperService = MapperService(
    mapping_config=config,
    repository_service=r_service,
    data_to_map=data
)

m_service.start_mapping()