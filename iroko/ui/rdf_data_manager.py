import rdflib
from typing import Optional, Any
import os

class RDFDataManager:
    """
    A Singleton class to manage RDF data for the Flet app using RDFLib.
    Ensures only one instance is created and provides global access to the RDF graph.
    """

    _instance: Optional['RDFDataManager'] = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(RDFDataManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, rdf_file_path: Optional[str] = None, rdf_format: str = 'turtle'):
        """
        Initializes the RDF graph. Only runs once due to the Singleton pattern.

        Args:
            rdf_file_path (str, optional): Path to the RDF file to load.
            rdf_format (str): Format of the RDF file (e.g., 'turtle', 'xml', 'n3'). Defaults to 'turtle'.
        """
        if RDFDataManager._initialized:
            return

        # Create an RDF graph
        self.graph = rdflib.Graph()

        # Load data if a file path is provided
        if rdf_file_path:
            self.load_rdf_file(rdf_file_path, rdf_format)

        RDFDataManager._initialized = True

    def load_rdf_file(self, file_path: str, rdf_format: str = 'turtle') -> None:
        """
        Loads and parses an RDF file into the graph.
        You need to tell RDFLib what format to parse, use the format keyword-parameter to parse() [[15]].

        Args:
            file_path (str): Path to the RDF file.
            rdf_format (str): Format of the RDF file (e.g., 'turtle', 'xml', 'n3').
        """
        try:
            self.graph.parse(file_path, format=rdf_format)
            print(f"Successfully loaded RDF data from {file_path}")
        except Exception as e:
            print(f"Error loading RDF file: {e}")
            raise

    def run_sparql_query(self, query: str) -> Any:
        """
        Executes a SPARQL query on the loaded RDF graph.
        This example sends a query to execute and then get back the result [[21]].

        Args:
            query (str): The SPARQL query string.

        Returns:
            Any: The result of the SPARQL query.
        """
        try:
            result = self.graph.query(query)
            return result
        except Exception as e:
            print(f"Error executing SPARQL query: {e}")
            raise

    def get_graph(self) -> rdflib.Graph:
        """
        Returns the underlying rdflib.Graph object for direct manipulation if needed.

        Returns:
            rdflib.Graph: The RDF graph.
        """
        return self.graph

    def add_triple(self, subject: str, predicate: str, obj: str) -> None:
        """
        Adds a triple to the graph.

        Args:
            subject (str): Subject of the triple.
            predicate (str): Predicate of the triple.
            obj (str): Object of the triple.
        """
        s = rdflib.URIRef(subject) if subject.startswith('http') else rdflib.Literal(subject)
        p = rdflib.URIRef(predicate) if predicate.startswith('http') else rdflib.Literal(predicate)
        o = rdflib.URIRef(obj) if obj.startswith('http') else rdflib.Literal(obj)
        self.graph.add((s, p, o))

    def clear_graph(self) -> None:
        """
        Clears all data from the graph.
        """
        self.graph.remove((None, None, None))


# Convenience function to get the singleton instance
def get_rdf_manager() -> RDFDataManager:
    """
    Returns the singleton instance of RDFDataManager.
    If not initialized, creates one with default settings.
    The Singleton pattern ensures a class has only one instance and provides a global point of access to that instance [[3]].
    """
    app_data_path = os.getenv("FLET_APP_STORAGE_DATA")
    rdf_file_path = os.path.join(app_data_path, "sceiba.turtle")
    return RDFDataManager(rdf_file_path=rdf_file_path, rdf_format='turtle')