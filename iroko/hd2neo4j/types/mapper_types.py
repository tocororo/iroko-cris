from enum import Enum


class Node:
    def __init__(self, label: str, id: str, properties: dict = {}):
        self.label = label
        self.id = id
        self.properties = {"id": id}
        self.properties.update(properties)
        self.relations: list[Relation] = []


class Relation:
    def __init__(
        self,
        label: str,
        properties: dict,
        start_node: Node,
        target_node: Node,
    ):
        self.label = label
        self.properties = properties
        self.start_node = start_node
        self.target_node = target_node


class VectorStrategies(Enum):
    BoW = "Bag-of-Words"
    TF_IDF = "Term Frequency-Inverse Document Frequency"
    DE = "Document Embeddings"
