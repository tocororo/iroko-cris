from iroko.hd2neo4j.types.mapper_types import VectorStrategies
from iroko.hd2neo4j.vectors.strategies.bag_of_words import BagOfWords
# from iroko.hd2neo4j.vectors.strategies.sentence_transformer import (
#     TransformerVectorizer,
# )
import logging
import importlib.util


logger = logging.getLogger('iroko-cris')


class VectorManager:
    def __init__(self, strategy: VectorStrategies):
        self.strategy = strategy

    def get_vector(self, data):
        if self.strategy == VectorStrategies.DE.value:
            if importlib.util.find_spec("sentence_transformers") is None:
                logger.error(
                    "The dependencies for vectorization corresponding to the Document Embedding strategy are not installed. "
                    "Use 'pip install hd2neo4j[ve-de]' to install them or 'pip install hd2neo4j[ve-full]' for all supported strategies."
                )
                return
            return data #TransformerVectorizer().vectorize(data)

        elif self.strategy == VectorStrategies.BoW.value:
            if importlib.util.find_spec("sklearn") is None:
                logger.error(
                    "The dependencies for vectorization corresponding to the Bag-of-Words strategy are not installed. "
                    "Use 'pip install hd2neo4j[ve-bow]' to install them or 'pip install hd2neo4j[ve-full]' for all supported strategies."
                )
                return
            return BagOfWords().vectorize(data)

        else:
            logger.warning("The strategy is not yet implemented")
