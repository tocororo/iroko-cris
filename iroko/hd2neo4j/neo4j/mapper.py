from iroko.hd2neo4j.mapping_config.mapping_config import (
    MappingConfig,
    EntityMapping,
)
from iroko.hd2neo4j.utils.data_iterator import Data_Iterator
from iroko.hd2neo4j.utils.utils import sanitize_str_value
from ..types.mapper_types import Node, Relation
import uuid as uuid_pkg
from iroko.hd2neo4j.neo4j.repository import Neo4jRepository
from iroko.hd2neo4j.vectors.vectorizer import VectorManager
import logging
import traceback

logger = logging.getLogger('iroko-cris')


class Mapper:
    def __init__(
        self,
        config: MappingConfig,
        data: Data_Iterator,
        repository: Neo4jRepository,
    ):
        self.config = config
        self.data = data
        self.relations = []
        self.repository = repository

    def start(self):
        for entity_config in self.config.entities:
            logger.info("Starting Mapper")
            self._map_instances(entity_config, self.data)  # TODO: get the corresponding data fro each use case(entity)

    def _map_instances(self, entity_config: EntityMapping, entity_data: Data_Iterator):
        exceptionsIds = []
        required_fields_ids = []
        success_iteration = 0
        required_fields_error = 0
        if entity_data is not None:

            for item in entity_data:
                item_id = item.get("id")
                try:
                    node = Node(entity_config.name, item_id)

                    if entity_config.validate_required(item):
                        self.process_data_properties_in_instance(
                            entity_config.properties,
                            item,
                            entity_config.valuesof,
                            node,
                        )

                        # ----- Vectors handling
                        if entity_config.vectorize:
                            vector_config: dict = entity_config.vectorize

                            vector_phrase: str = vector_config.get("phrase")
                            for value in vector_config.get("values"):
                                if not isinstance(value, str):
                                    logger.error("The vectorization of complex items is not supported")
                                    continue
                                if not entity_config.properties.get(value):
                                    logger.error(f"The value of '{value}' could not be Found")
                                else:
                                    vector_phrase = vector_phrase.replace(
                                        f":{value}",
                                        f"{item.get(value)}",
                                    )

                            vector_manager = VectorManager(vector_config.get("strategy"))
                            vector = vector_manager.get_vector(vector_phrase)
                            node.properties.update({f"vectors": vector})
                        # ----- Vectors handling

                        if node.relations:
                            for relation in node.relations:
                                self.repository.add_relation(relation)
                        else:
                            self.repository.add_node(node)

                        success_iteration += 1
                        logger.info(f"SUCCESSFULLY PROCESSED {item_id}")
                    else:
                        required_fields_error += 1
                        required_fields_ids.append(item_id)

                except Exception as e:
                    exceptionsIds.append({'id':item_id, 'message': str(e)})
                    traceback.print_exc()

            logger.info(f"{success_iteration} SUCCESSFULLY ENTRIES")
            logger.error(f" ON {len(exceptionsIds)} ITEMS")
            logger.error(exceptionsIds)
            logger.info("===============================================================")
            logger.error(f"REQUIRED FIELDS ERROR ON {len(required_fields_ids)}")
            logger.error(required_fields_ids)

    def process_data_properties_in_instance(
        self,
        properties_config: dict,
        data_instance: dict,
        values_of_config,
        node: Node,
    ):
        for property_key in properties_config.keys():
            value = data_instance.get(property_key)
            if value:
                self._process_property(
                    property_key,
                    value,
                    properties_config,
                    values_of_config,
                    node,
                )

    def _process_property(
        self,
        property_key: str,
        property_value,
        properties_config: dict,
        values_of_config,
        node: Node,
    ):
        if "identifiers" == property_key and isinstance(property_value, list):
            for identifier in property_value:
                node.properties.update(
                    self._process_identifiers_dict(
                        identifier,
                        properties_config.get("identifiers"),
                        values_of_config,
                    )
                )

        if "__relation" in properties_config[property_key]:
            if isinstance(property_value, list):
                for relation in property_value:
                    if isinstance(relation, dict):

                        self._process_relation(
                            property_key,
                            relation,
                            properties_config,
                            node,
                        )
            elif isinstance(property_value, dict):
                self._process_relation(
                    property_key,
                    property_value,
                    properties_config,
                    node,
                )

        # Literal
        elif isinstance(property_value, str):
            self._process_primitive_types(property_key, property_value, properties_config, node)

        # Dict
        elif isinstance(property_value, dict):
            self._process_dict(property_key, property_value, properties_config, node)

        elif isinstance(property_value, list):
            self._process_list(property_key, property_value, properties_config, node)

    def _process_dict(
        self,
        property_key,
        property_value,
        properties_config: dict,
        node: Node,
    ):
        property_config_value = properties_config.get(property_key)
        if isinstance(property_config_value, dict) and isinstance(property_value, dict):

            nested_node = Node(property_key, uuid_pkg.uuid4())
            relation_label = "HAS"

            for new_key in property_config_value.keys():
                if "__predicated" == new_key:
                    if property_config_value.get(new_key):
                        relation_label = property_config_value.get(new_key)

                if property_value.get(new_key) and isinstance(property_value.get(new_key), str):
                    self._process_primitive_types(
                        new_key,
                        property_value.get(new_key),
                        property_config_value,
                        nested_node,
                    )

                elif property_value.get(new_key) and isinstance(property_value.get(new_key), list):
                    self._process_list(
                        new_key,
                        property_value,
                        property_config_value,
                        nested_node,
                    )

                elif property_value.get(new_key) and isinstance(property_value.get(new_key), dict):
                    self._process_dict(
                        new_key,
                        property_value.get(new_key),
                        property_config_value,
                        nested_node,
                    )

            if nested_node.properties:
                node.relations.append(Relation(relation_label, {}, node, nested_node))

    def _process_identifiers_dict(
        self,
        identifier_data: dict,
        identifier_config: dict,
        values_of_entity_config: dict,
    ):
        __predicate = identifier_config.get("__predicate")

        values_of = str(identifier_config.get(__predicate)).split(":")[1]

        __predicate_source = identifier_data.get(__predicate)

        predicate = values_of_entity_config.get(values_of).get(__predicate_source)

        object_value = identifier_data.get(identifier_config.get("__object"))

        return {predicate: object_value}

    def _process_list(
        self,
        property_key,
        property_value,
        property_config: dict,
        node: Node,
    ):
        dict_config = property_config.get(property_key)
        if isinstance(property_value[0], dict) and isinstance(dict_config, dict):
            for dic in property_value:
                self._process_dict(property_key, dic, dict_config, node)

        elif isinstance(property_value[0], str):
            self._process_primitive_types(property_key, property_value, property_config, node)

    def _process_primitive_types(
        self,
        property_key,
        property_value,
        properties_config,
        node: Node,
    ):
        node.properties.update({properties_config.get(property_key): sanitize_str_value(property_value)})

    def _process_relation(
        self,
        property_key,
        target_object: dict,
        properties_config: dict,
        node: Node,
    ):
        # logger.info(f" Processing relations of: ({node.label}) ")
        relation_config: dict = properties_config.get(property_key)
        target_id, target_label, relation_label = ("",) * 3
        node_properties = {}
        relation_properties = {}

        for key in relation_config:
            if "__relation" == key:
                target_id = target_object.get(relation_config.get(key))
            elif "__target" == key:
                target_label = relation_config.get(key)
            elif "__predicate" == key:
                relation_label = relation_config.get(key)
            elif "relation_properties" == key:
                relation_properties_config: dict = relation_config.get(key)

                for relation_config_key in relation_properties_config.keys():
                    relation_value = target_object.get(relation_config_key)

                    if not relation_value:
                        continue

                    if isinstance(relation_value, dict):
                        logger.error("A object can not be a assigned to relation properties")
                        continue

                    if isinstance(relation_value, str):
                        relation_properties.update(
                            {relation_properties_config.get(relation_config_key): sanitize_str_value(relation_value)}
                        )
                    elif isinstance(relation_value, list):
                        if isinstance(relation_value[0], dict):
                            logger.error("A object can not be a assigned to relation properties")
                            continue

                        if isinstance(relation_value[0], str):
                            relation_properties.update(
                                {relation_properties_config.get(relation_config_key): sanitize_str_value(relation_value)}
                            )
            # TODO implement the target properties use case.
            else:
                if not target_object.get(key):
                    continue

                node_properties.update({relation_config.get(key): sanitize_str_value(target_object.get(key))})

        node.relations.append(
            Relation(
                relation_label,
                relation_properties,
                node,
                Node(target_label, target_id, node_properties),
            )
        )
