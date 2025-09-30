# legacy rdf build from sceiba data. 


import json
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, BNode
from rdflib.namespace import FOAF, XSD, OWL
from rdflib.container import Container
from sympy import Le

class ConfigurationManager:
    """esta clase es l encargada  de establecer el orden en que se va a mapear
    ademas de validar el json de configuracion garantizando que tenga la estructura correcta"""
    def __init__(self, json_ontology_conf, namespace):
        self.json_ontology_conf = json_ontology_conf
        self.namespace = namespace

    def _set_json_ontology_conf(new_json_ontology_conf):
        json_ontology_conf = new_json_ontology_conf
        return json_ontology_conf

    def validate_mapping_section(self, mapping_section):
        if not isinstance(mapping_section, dict):
            print("La sección 'mapping' debe ser un objeto JSON.")
            return False

        required_keys = ["_class", "required", "properties", "valuesOf"]
        for key in required_keys:
            if key not in mapping_section:
                print(f"La clave '{key}' es requerida en la sección 'mapping'.")
                return False

        if not isinstance(mapping_section["required"], list):
            print("'required' debe ser una lista de nombres de propiedades requeridas.")
            return False

        if not isinstance(mapping_section["properties"], dict):
            print("'properties' debe ser un objeto JSON que mapea propiedades a URIs.")
            return False

        if not isinstance(mapping_section["valuesOf"], dict):
            print(
                "'valuesOf' debe ser un objeto JSON que mapea propiedades a sus valores permitidos.")
            return False

        return True

    def validate_entities(self, entities):
        for entity in entities:
            if "mapping" in entity:
                if not self.validate_mapping_section(entity["mapping"]):
                    return False
        return True

    def validate_config_json(self):
        if not isinstance(self.json_ontology_conf, dict):
            print("El archivo JSON debe contener un objeto JSON en la parte superior.")
            return False

        required_keys = ["name", "description", "created", "last_updated",
                         "mapping_order",
                         "entities"]
        for key in required_keys:
            if key not in self.json_ontology_conf:
                print(f"La clave '{key}' es requerida en el archivo JSON.")
                return False

        if not self.validate_entities(self.json_ontology_conf["entities"]):
            return False

        return True

    def put_the_order(self):
        """    Replace the order of entities in the JSON configuration.


        Returns:
        ordered_entities (list): The ordered list of entities.
        """
        try:
            if self.validate_config_json():
                order = self.json_ontology_conf.get("mapping_order", [])
                entities_map = {entity["pid"]: entity for entity in self.json_ontology_conf.get(
                    "entities", [])}
                ordered_entities = [entities_map[pid] for pid in order if pid in entities_map]

                # Replace the entities array in the JSON configuration
                self.json_ontology_conf["entities"] = ordered_entities

                return ordered_entities
        except Exception as e:
            print(f"Error al reemplazar el arreglo de entidades: {str(e)}")
        return None


class EntityMapping:
    def __init__(self, config: dict):
        self.config = config
        self.pid = self.config['pid']
        self.jsonfile = self.config["jsonfile"] if "jsonfile" in self.config else ""
        self.name = self.config['name']
        self.description = self.config['description']
        self.destination_class = self.config['_class']
        self.required = self.config['required']
        self.properties = self.config['properties']
        self.valuesof = self.config['valuesOf']

    def validate_required(self, instance):
        """Validates that all required attributes are present in the instance

        Args:
            required_attributes (list): A list of attribute names that are required.
            instance (dict): A dictionary representing the instance to validate.

    Returns:
        bool: True if all required attributes are present, False otherwise.

        """
        # Iterate over the list of required attributes
        for required_attribute in self.required:
            # If any required attribute is missing from the instance JSON, return False
            if required_attribute not in instance:
                return False
        # All required attributes are present in the instance JSON, so return True
        return True


class MappingConfig:

    def __init__(self, config: dict):
        self.config = config
        self.name = self.config['name']
        self.description = self.config['description']
        self.created = self.config['created']
        self.last_updated = self.config['last_updated']
        self._order = self.config['_order']
        self.namespaces = self.config['namespaces']
        self.default_namespace = self.config['default_namespace']

        # Possible values n-ary, direct, reification
        self.relation_strategy = self.config["relation_strategy"] if ("relation_strategy" in
                                                                          self.config) else "n-ary"

        # Possible values Bag, Seq, Alt, List
        self.list_strategy = self.config["list_strategy"] if ("list_strategy" in
                                                                      self.config) else "Bag"

        entities = [EntityMapping(entity) for entity in self.config['entities']]
        entities_map = {entity.pid: entity for entity in entities}
        ordered_entities = [entities_map[pid] for pid in self._order if pid in entities_map]
        self.entities = ordered_entities


class CreateGraph:
    def __init__(self, graph: Graph = None):
        """
        Initialize a CreateGraph.

        Args:
            graph (Graph, optional): The graph to work with. Defaults to None.
        """
        if graph is None:
        # If no graph is provided, create a new one
            self.graph = Graph()
        else:
            self.graph = graph
        # Define an empty dictionary as the 'namespaces' attribute
        self.namespace = {}

    def add_triplet(self, sujeto, predicado, objeto):
        """    Add a triplet to the graph.


        Args:
            subject_uri (any): The subject_uri of the triplet.
            predicate (any): The predicate of the triplet.
            object (any): The object of the triplet.
        """
        # try:
    # Check if subject_uri is not an instance of URIRef or Literal
        if not isinstance(sujeto, (URIRef, Literal)):
        # Try to convert subject_uri to URIRef
            sujeto = URIRef(sujeto)

    # Check if predicate is not an instance of URIRef
        if not isinstance(predicado, URIRef):
        # Try to convert predicate to URIRef
            predicado = URIRef(predicado)

    # Check if object is not an instance of URIRef or Literal
        if not isinstance(objeto, (URIRef, Literal)):
        # Try to convert object to URIRef if it's a URI, or to Literal if it's a literal
            if objeto.startswith('http://') or objeto.startswith('https://'):
                objeto = URIRef(objeto)
            else:
                objeto = Literal(objeto)

    # Add the triplet to the graph
        # print('......')
        # print("{0}  -- {1} -- {2}".format(sujeto, predicado, objeto))
        self.graph.add((sujeto, predicado, objeto))

        # except Exception as e:
        #     print(f"Error while adding the triplet: {str(e)}")
    def serialize(self, format='ttl'):
            """    Serialize the RDF graph in the specified format.
    Args:
        format (str): Serialization format (e.g., 'xml', 'turtle', 'n3', 'json-ld', etc.).

            Returns:
        str: The RDF data serialized in the specified format.
            """
            print("=====================================================)")
            return self.graph.serialize(format=format, indent=True)
    def add_namespaces(self, namespaces_dict: dict):
            """    Add namespaces to the RDF graph.
        Args:
        namespaces_dict (dict): A dictionary where keys are namespaces prefixes and values are namespaces.
        Returns:
        Graph: The updated graph after adding the namespaces.
            """
            # try:
            for prefix, namespace in namespaces_dict.items():
                self.graph.namespace_manager.bind(prefix, namespace)
            return self.graph  # Returns the updated graph
            # except Exception as e:
            #         print(f"Error while adding namespaces: {str(e)}")
            #         return None  # Returns None in case of an error
        #Verifica si existe una uri dada en el grafo
    def get_namespaces(self):
        """Returns a dictionary of namespaces in the graph.

        Returns:
        dict: A dictionary mapping prefixes to URIs.
        """
        namespaces_dict = {}
        for prefix, uri in self.graph.namespaces():
           namespaces_dict[str(prefix)] = str(uri)
        return namespaces_dict
    def _uri_exists(self, uri):

            sujeto_uri = URIRef(uri)
            return (sujeto_uri, None, None) in self.graph
            #Busca una key dado su valor


class RDFMapper:
    def __init__(self, created_graph: CreateGraph,
                 mapping_config: MappingConfig):
        self.created_graph = created_graph
        self.mapping_config = mapping_config
        self.namespaces = mapping_config.namespaces

        self.instances_iter = None
        self.entity_pid = None

    def map_instances(self, entity_config, instance_iterator, entity_pid):
        self.instances_iter = instance_iterator
        self.entity_pid = entity_pid

        if self.instances_iter is not None:
            # try:
            for instance in self.instances_iter:
                subject_uri = self._validate_instance(entity_config, instance)
                self.created_graph.add_triplet(
                    str(subject_uri),
                    RDF.type,
                    str(entity_config.destination_class))
                self.process_properties_in_an_instance(
                    entity_config.properties, instance, subject_uri,
                    entity_config.valuesof)

                # if "vector":
                #     args = entity_config['vector']['args']
                #     strat_class = entity_config['vector']['strategy']
                #     strat = strat_class(args)
                #     vector = strat.get(instance)



            # except Exception as e:
            #     raise e
            #     return str(e)

    def process_properties_in_an_instance(self, properties_config: dict, instance: dict,
                                          subject_uri, valuesof_config):
        """
        este metodo procesa  la seccion de de properties de una instancia o sea
        los atributos que reprentan un literal o una lista de literales
        """
        # try:
        for property_key in properties_config.keys():
            value = instance.get(property_key)
            if value:
                self._process_property(subject_uri, property_key, value, properties_config,
                                       valuesof_config)

        # if isinstance(value, dict):
        #
        #     if self._is_a_relation(value):
        #         self._process_relation(subject_uri, key, value,
        #                                properties_config)
        #     self._process_dict(
        #         subject_uri, key, value, properties_config)
        #     continue

        # except Exception as e:
        #     print(f"Error al procesar propiedades en una instancia: {str(e)}")
        #     raise e

    def _validate_instance(self, entity_config: EntityMapping, instance: dict):
        """Validates that the instance has the
        required attributes specified in the
        configuration.

        Comprueba que la instancia sea un diccionario válido,
        que tenga una propiedad id y que la propiedad no esté vacía
        y devuelve la URI del objeto
        valida que todos los requeridos esten en el json de una instancia

        valida que la instancia tenga los atributos requeridos en la configuracion
        Args:
            instance (dict): A dictionary representing the instance to validate.

        Returns:
        str: The URI of the instance if it already exists in
        the graph, otherwise returns the new URI.
                    Returns None if the instance does
                      not have all the required attributes.

        """
        required_attribute = entity_config.required

        if entity_config.validate_required(instance):
            # Save the instance ID in a variable
            return self.get_uri_by_sceiba_id(instance.get("id"))

        return None

    def get_uri_by_sceiba_id(self, _id: str):
        """Check if the subject_uri (URI) already exists in the graph.

        Args:
            _id (str): The ID of the subject_uri.

        Returns:
        str: The subject_uri (URI) if it already exists, otherwise the new subject_uri (URI).
        """
        # Get the namespaces from the namespaces dictionary using the provided namespaces key
        new_subject = URIRef(f"{self.mapping_config.default_namespace}id/{_id}")

        # Iterate over the graph to check if the subject_uri (URI) of the instance already exists
        # TODO: optimizar con una query, en vez de recorrer todo el grafo.
        for subject in self.created_graph.graph:
            # If it finds a match, return that subject_uri (URI)
            if subject == new_subject:
                return subject
        # If no match is found, return the new subject_uri (URI)
        return new_subject
        # Return None if the instance does not have all the required attributes

    def _process_property(self, subject_uri, property_key, value, properties_config,
                          valuesof_config):

        # Identifiers
        if "identifiers" == property_key and isinstance(value, list):
            # print("process identifiers...")
            for identifier in value:
                self._process_identifiers_dict(
                    subject_uri, identifier,
                    properties_config.get("identifiers"), valuesof_config)

        # Relations
        elif "__relation" in properties_config[property_key]:
            if isinstance(value, list):
                # print("process relation...")
                for relation in value:
                    if isinstance(relation, dict):

                        self._process_relation(subject_uri, property_key, relation,
                                               properties_config)
            if isinstance(value, dict):
                self._process_relation(subject_uri, property_key, value,
                                       properties_config)

        # Literal
        elif isinstance(value, str):
            self._process_literal(subject_uri, property_key, value, properties_config)

        # Dict
        elif isinstance(value, dict):
            # print('process dict')
            self._process_dict(
                subject_uri, property_key, value, properties_config)

        # List
        elif isinstance(value, list):
            self._process_list(subject_uri, property_key, value, properties_config)

    def _process_literal(self, subject, property_key, value, properties_config):
        """Processes a literal value for a given subject_uri and key
        based on the properties configuration.

        Args:
            subject (_type_): _description_
            key (_type_): _description_
            value (_type_): _description_
            properties_config (_type_): _description_
        """
        literal = Literal(value)
        predicate = properties_config[property_key]
        self.created_graph.add_triplet(subject, predicate, literal)

    def _process_identifiers_dict(self, subject, identifiers_dict: dict, identifiers_config:
    dict, valuesof_config: dict):
        """Processes the identifiers dictionary for a
        given subject_uri based on the identifiers configuration.
        # Procesa un diccionario con un identificador (campo identifier)


        Args:
        subject_uri (_type_): _description_
        identifiers_dict (dict): A dictionary representing the identifiers for the subject_uri.
        identifiers_config (dict): A dictionary representing the configuration for the identifiers.

        """
        # try:
        # Get the predicate value from the identifiers_config dictionary based on the "__predicate" key
        # If the key is not found, use an empty string as the default value
        __predicate = identifiers_config.get("__predicate")

        values_of = str(identifiers_config.get(__predicate)).split(':')[1]

        __predicate_source = identifiers_dict.get(__predicate)

        predicate = valuesof_config.get(values_of).get(__predicate_source)

        # Get the object value from the identifiers_dict dictionary based on the "__object" key
        # If the key is not found, use an empty string as the default value
        object_value = identifiers_dict.get(
            identifiers_config.get("__object"), "")
        # Add a triple to the created graph using the subject_uri, predicate, and object value

        self.created_graph.add_triplet(subject, predicate, object_value)
        # except Exception as e:
        #     # Print an error message if an exception occurs during the processing
        #
        #     print(f"Error en _process_identifiers_dict: {str(e)}")
        #     raise e

    def _process_list(self, subject_uri, property_key, value, properties_config: dict):

        if self.mapping_config.list_strategy in ("Bag", "Seq", "Alt"):
            property_value = properties_config[property_key]
            uri_bag = URIRef(value="{0}/{1}".format(subject_uri, property_key))
            bag = Container(graph=self.created_graph.graph, uri=uri_bag,
                            rtype=self.mapping_config.list_strategy)
            # print("=========== add list ==========")
            # print("bag uri: {0} bnode: {1}".format(bag.uri, uri_bag))

            # list of literals
            if isinstance(value[0], str):

                for item in value:
                    literal = Literal(item)
                    bag.append(literal)
                if subject_uri is not None:
                    self.created_graph.add_triplet(subject_uri, property_value, bag.uri)
                # print(bag.items())

            # list of bnodes
            if isinstance(property_value, dict) and isinstance(value[0],
                                                               dict) and "__predicate" in property_value:
                bnode_predicate = property_value.get("__predicate")
                if subject_uri is not None:
                    self.created_graph.add_triplet(subject_uri, bnode_predicate, bag.uri)
                i = 1
                for item in value:
                    bnode_item = self._process_dict(subject_uri=subject_uri, property_key=property_key,
                                                    value=item,
                                                    properties_config=properties_config,
                                                    add_to_graph=False,
                                                    dict_uri="{0}/{1}#_{2}".format(subject_uri,
                                                                               property_key, i))
                    i=i+1
                    bag.append(bnode_item)
                # print(bag.items())
            # print("=========== add list ==========")
            return bag
        elif self.mapping_config.list_strategy == "List":
            # TODO: implement linked list strategy using rdf:List
            return BNode()

    def _process_dict(self, subject_uri, property_key, value, properties_config: dict,
                      add_to_graph= True, dict_uri=None):
        """
            # Procesa un diccionario, recorre el dict y si el valor no es vacío, pregunta si es

            The  `_process_literal`  method receives the subject_uri, key, a dictionary of values
            ( `value_dict` ), and a properties configuration ( `properties_config` ) as arguments.
          Within the method, it checks if the value in the dictionary is another dictionary.
            In that case, it loops through each key-value pair of the inner dictionary using
            recursion by calling the  `_process_literal`  method again.

If the value in the dictionary is not a dictionary, it checks if it is a list. If it is, it loops
 through each element of the list using recursion.

Finally, if the value in the dictionary is neither a dictionary nor a list, it is directly added
to the corresponding list in the properties configuration ( `properties_config` ).

In summary, the  `_process_literal`  method is responsible for processing a dictionary of values,
 recursively iterating through all the keys and values and adding them to the properties configuration.

I hope this clarifies the explanation for you. If you have any further questions, feel free to ask.

        Args:
            subject (_type_): The subject_uri of the dictionary
            key (_type_): The key of the current dictionary entry
            value_dict (dict): The dictionary value to process
            properties_config (dict): The configuration of properties
        """

        property_value = properties_config.get(property_key)
        if isinstance(property_value, dict) and isinstance(value,
                                                           dict) and "__predicate" in property_value:
            if dict_uri is not None:
                bnode = URIRef(dict_uri)
            else:
                bnode = BNode()
            bnode_predicate = property_value.get("__predicate")
            if add_to_graph:
                # en caso que subject_uri sea None, significa que estoy creando un bnode
                # "independiente", esto puede ser util para las listas o en otro caso.
                self.created_graph.add_triplet(subject_uri, bnode_predicate, bnode)
            for object_key, predicate in property_value.items():
                if object_key in value:
                    item = value.get(object_key)
                    if isinstance(predicate, str) and isinstance(item, str):
                        self.created_graph.add_triplet(bnode, predicate, Literal(item))
                    elif isinstance(predicate, str) and isinstance(item, list):
                        self._process_list(bnode, object_key, item, property_value)
                    elif isinstance(predicate, dict):
                        # que el predicado sea un dict, aqui significa que es otro dict dentro
                        # del dict que estamos procesando.
                        self._process_dict(bnode, object_key, item, property_value)
            return bnode

    def _process_relation(self, subject_uri, property_key, target_object: dict,
                          properties_config: dict):
        """
        Process a relation in the RDF graph.

        Args:
        subject_uri: The subject_uri of the relation source.
        key: The key representing the relation.
        value: The value of the relation as a dictionary.
        properties_config: Configuration for the properties.
        """
        # try:
        # Get the configuration for the relation
        relation_config: dict = properties_config.get(property_key)
        relation_type = str(relation_config.get("__predicate"))
        bnode = BNode()
        target_object_id = target_object.get(relation_config.get("__relation"))
        target_object_uri = self.get_uri_by_sceiba_id(target_object_id)

        # procesar la relacion segun estrategia
        if self.mapping_config.relation_strategy == "n-ary":
            self.created_graph.add_triplet(subject_uri, relation_type, bnode)
            self.created_graph.add_triplet(bnode, RDF.value, target_object_uri)
        elif self.mapping_config.relation_strategy == "direct":
            self.created_graph.add_triplet(bnode, RDF.type, relation_type)
            self.created_graph.add_triplet(subject_uri, bnode, target_object_uri)
        elif self.mapping_config.relation_strategy == "reification":
            self.created_graph.add_triplet(bnode, RDF.subject, subject_uri)
            self.created_graph.add_triplet(bnode, RDF.predicate, relation_type)
            self.created_graph.add_triplet(bnode, RDF.object, target_object_uri)

        if "relation_properties" in relation_config and isinstance(relation_config.get( \
            "relation_properties"), dict):
            for key, pred in relation_config.get("relation_properties").items():
                value = target_object.get(key)
                self.created_graph.add_triplet(bnode, pred, value)

        # TODO: add properties of target_object to the graph...

        # Add the type of the relation to the blank node
        # if relation_config.get("id"):
        #     self.created_graph.add_triplet(
        #         str(bnode_relation), RDF.type, str(relation_config.get("__predicate")))
        # Get the namespaces for the graph
        # uri_sceiba = Namespace( self.mapping_config.default_namespace)
        #
        # print("uri_sceiba", uri_sceiba)
        # # Process each key-value pair in the relation value
        # for key_invalue, value_invalue in target_object.items():
        #     # Check if the key matches the relation identifier
        #     if key_invalue == relation_config.get("__relation"):
        #         print("key_invalue", key_invalue)
        #         # Add the subject_uri of the relation as an object to the blank node
        #         print("=====================", str(bnode_relation))
        #         print("=====================", (uri_sceiba.key))
        #
        #         rel_subject = self.get_uri_by_sceiba_id(value_invalue)
        #         print("=====================", str(rel_subject))
        #
        #         # aqui tengo duda en esa uri sceiba.key y es a la hora de crear ese predicado semantico
        #         self.created_graph.add_triplet(
        #             str(bnode_relation), (uri_sceiba.key), str(rel_subject))
        #         # Add the key-value pair as a triplet to the blank node
        #     self.created_graph.add_triplet(str(bnode_relation), str(
        #         relation_config.get(key_invalue)), str(value_invalue))
        #
        # # Add the blank node as an object to the subject_uri
        #
        # self.created_graph.add_triplet(subject_uri, uri_sceiba.key, str(bnode_relation))

        # except Exception as e:
        #     print(f"Error en _process_relation: {str(e)}")
        #     raise e

        # # Dado un string nombre de entidad busca en las configuraciones su especifica configuracion
        # def search_entity_by_string_pid(self, entity_pid: str):
        #     """Searches for the specific configuration
        #     of an entity based on its pid.
        #
        #     Args:
        #     entity_pid (str): The pid of the entity.
        #
        #     Returns:
        #     dict: The configuration of the entity if found,
        #       otherwise an empty dictionary.
        #     """
        #     entity_configuration = []
        #     for entity in self.mapping_config.json_ontology_conf.get("entities"):
        #         if entity["pid"] == self.entity_pid:
        #             entity_configuration = entity
        #             break
        #
        #     return entity_configuration

        #
    # def validate_instances_array(self):
    #     """Check if the instances_iter array is valid
    #
    #     Returns:
    #     bool: True if the instances_iter array is not None, False otherwise.
    #     """
    #     if self.instances_iter is None:
    #         print("Error: No iterator")
    #         return False
    # return True

    # se encarga de validar el arreglo de instancias ,inicializa la uri con la que se va a mapear las entidades
    # Si esta correcto procede a procesar las instancias
    # def _mapping_entity(self):
    #     try:
    #         if self.validate_instances_array():
    #             uri_sceiba = None
    #             uri_sceiba = self.created_graph.get_namespaces().get(self.namespaces)
    #             if uri_sceiba is None:
    #                 raise Exception(
    #                     "Error: No se encontró la URI correspondiente")
    #             else:
    #                 if self._process_instances(
    #                     self.search_entity_by_string_pid(self.entity_pid).get(
    #                         "mapping")) == "Success":
    #                     rdf_data = self.created_graph
    #                     return rdf_data.graph
    #         else:
    #             raise Exception("Error: Invalid instances_iter array")
    #     except Exception as e:
    #         raise e
    #         return str(e)

    #
    # def process_properties_section(self, entity_configuration: EntityMapping):
    #     for instance in self.instances_iter:
    #         subject_uri = self._validate_instance(instance)
    #         self.created_graph.add_triplet(
    #             str(subject_uri), RDF.type, str(entity_configuration.destination_class))
    #         self.process_properties_in_an_instance(
    #             entity_configuration.properties, instance, subject_uri,
    #             entity_configuration.valuesof)
    #
    # def _process_instances(self, entity_configuration: EntityMapping):
    #     try:
    #         entity_class = entity_configuration.destination_class
    #         values_of_config = entity_configuration.valuesof
    #         self.process_properties_section(
    #             entity_configuration.properties, entity_class, values_of_config)
    #         return "Success"
    #     except Exception as e:
    #         error_message = f"Error processing instances_iter: {str(e)}"
    #         return error_message


class Legacy:
    def sources(self):
        with open('.data/rdf/map.json', 'r') as file:

            self.general_graph = Graph()

            data_dict = json.loads(file.read())
            mapping_config = MappingConfig(data_dict)

            create_graph = CreateGraph()
            create_graph.graph = create_graph.add_namespaces(mapping_config.namespaces)

            rdf_mapper = RDFMapper(create_graph, mapping_config)
            for entity in mapping_config.entities:
                with open(entity.jsonfile, 'r') as f:
                    data = json.loads(f.read())
                    entity_iterator_by_pid = iter(data)
                    rdf_mapper.map_instances(entity, entity_iterator_by_pid, entity.pid)
                # create_graph.graph = create_graph.graph + graph

                self.general_graph = self.general_graph + create_graph.graph
            
            self.general_graph.serialize(format='nt', destination=".data/rdf/sceiba.nt", encoding='UTF-8')

# l = Legacy()
# l.sources()

