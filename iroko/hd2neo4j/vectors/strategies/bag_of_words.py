from sklearn.feature_extraction.text import CountVectorizer


class Singleton:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.vectorizer = CountVectorizer()
        return cls._instance


class BagOfWords(Singleton):

    def vectorize(self, data):
        vector = self.vectorizer.fit_transform(data)
        return vector.toarray()
