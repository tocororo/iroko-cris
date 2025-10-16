from sentence_transformers import SentenceTransformer


class TransformerSingleton:
    _instance = None

    def __new__(cls, model_name="sentence-transformers/all-MiniLM-L12-v2"):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.model = SentenceTransformer(model_name)
        return cls._instance


class TransformerVectorizer(TransformerSingleton):
    def vectorize(self, data):
        return self.model.encode(data)
