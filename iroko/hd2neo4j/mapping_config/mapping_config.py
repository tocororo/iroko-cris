class EntityMapping:
    def __init__(self, config: dict):
        self.config = config
        self.name = self.config.get("name")
        self.required = self.config.get("mapping").get("required")
        self.properties = self.config.get("mapping").get("properties")
        if self.properties.get("identifiers"):
            self.valuesof = self.config.get("mapping").get("valuesOf")
        else:
            self.valuesof = None
        if self.config.get("mapping").get("_vectorize"):
            self.vectorize = self.config.get("mapping").get("_vectorize")
        else:
            self.vectorize = None

    def validate_required(self, instance):
        for required_attribute in self.required:
            if required_attribute not in instance:
                return False
        return True


class MappingConfig:

    def __init__(self, config: dict):
        self.config = config
        self.name = self.config.get("name")
        # self.description = self.config["description"]
        # self.created = self.config["created"]
        # self.last_updated = self.config["last_updated"]
        # self._order = self.config["_order"]
        # self.namespaces = self.config["namespaces"]
        # self.default_namespace = self.config["default_namespace"]

        # Possible values n-ary, direct, reification
        self.relation_strategy = self.config["relation_strategy"] if ("relation_strategy" in self.config) else "n-ary"

        # Possible values Bag, Seq, Alt, List
        self.list_strategy = self.config["list_strategy"] if ("list_strategy" in self.config) else "Bag"

        entities = [EntityMapping(entity) for entity in self.config.get("entities")]
        # entities_map = {entity.pid: entity for entity in entities}
        # ordered_entities = [
        #     entities_map[pid] for pid in self._order if pid in entities_map
        # ]
        self.entities = entities
