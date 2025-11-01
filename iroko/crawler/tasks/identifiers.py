import re
from typing import Dict, Any, List
import logging
import uuid



from iroko.crawler.schemas import TaskExecution
from iroko.crawler.task import CrawlerTask
from iroko.storage import neo4j_db

logger = logging.getLogger('iroko-cris')

class IdentifierFixTask(CrawlerTask):
    """Crawler task to fix identifier properties in the neo4j database."""

    def __init__(self, task_id: str, name: str, config: Dict[str, Any] = None):
        super().__init__(task_id, name, config)
        self.processed_nodes = 0
        self.updated_uuid_properties = 0
        self.created_identifiers = 0
        self.removed_properties = 0

    async def execute(self, execution: TaskExecution) -> Dict[str, Any]:
        """
        Execute the identifier fix task.
        
        - Renames 'id' properties to 'iroko_uuid' if the value is a UUID.
        - Converts properties like 'identifier#CODE' into relationships with new 'Identifier' nodes.
        """
        session = None
        try:
            session = await neo4j_db.get_session()
            
            # Step 1: Find nodes with 'id' property that is a UUID string and rename it
            self.logger.info("Starting to process 'id' properties to 'iroko_uuid'...")
            rename_query = """
            MATCH (n) 
            WHERE n.id IS NOT NULL AND n.id =~ '^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$'
            SET n.iroko_uuid = n.id
            REMOVE n.id
            RETURN count(n) AS updated_count
            """
            rename_result = await session.run(rename_query)
            rename_record = await rename_result.single()
            self.updated_uuid_properties = rename_record["updated_count"] if rename_record else 0
            self.logger.info(f"Renamed 'id' to 'iroko_uuid' for {self.updated_uuid_properties} nodes.")

            # Step 2: Find nodes with 'identifier#' properties and convert them to relationships
            self.logger.info("Starting to process 'identifier#' properties to relationships...")
            
            # First, get all nodes with identifier properties to process them
            prop_fetch_query = """
            MATCH (n) 
            WHERE ANY(key IN keys(n) WHERE key STARTS WITH 'identifier#')
            RETURN elementId(n) AS element_id, [key IN keys(n) WHERE key STARTS WITH 'identifier#'] AS identifier_keys
            """
            prop_result = await session.run(prop_fetch_query)
            
            async for record in prop_result:
                element_id = record["element_id"]
                identifier_keys = record["identifier_keys"]
                
                for prop_key in identifier_keys:
                    # Extract the code part from the property name (e.g., 'identifier#DOI' -> 'DOI')
                    match = re.match(r'^identifier#(.+)$', prop_key)
                    if not match:
                        continue # Skip if format doesn't match expected pattern
                    
                    code = match.group(1)
                    # Get the value of the identifier property
                    value_fetch_query = f"MATCH (n) WHERE elementId(n) = $element_id RETURN n.`{prop_key}` AS prop_value"
                    value_result = await session.run(value_fetch_query, element_id=element_id)
                    value_record = await value_result.single()
                    if not value_record or value_record["prop_value"] is None:
                        continue
                    
                    prop_value = value_record["prop_value"]
                    
                    # Create or merge the Identifier node with unique idtype and value
                    # Using MERGE with idtype and value ensures uniqueness
                    identifier_query = """
                    MERGE (i:Identifier {idtype: $idtype, value: $value})
                    RETURN elementId(i) AS identifier_element_id
                    """
                    identifier_result = await session.run(identifier_query, idtype=code, value=prop_value)
                    identifier_record = await identifier_result.single()
                    if not identifier_record:
                        self.logger.warning(f"Could not create or find Identifier node for idtype: {code}, value: {prop_value}")
                        continue
                    
                    identifier_element_id = identifier_record["identifier_element_id"]
                    
                    # Create the relationship between the original node and the Identifier node
                    # The relationship type name is not specified, using a generic one like 'HAS_IDENTIFIER'
                    relationship_query = """
                        MATCH (n) WHERE elementId(n) = $element_id
                        MATCH (i) WHERE elementId(i) = $identifier_element_id
                        MERGE (n)-[:HAS_IDENTIFIER]->(i)
                    """
                    await session.run(relationship_query, element_id=element_id, identifier_element_id=identifier_element_id)
                    
                    # Remove the original property from the node
                    remove_prop_query = f"""
                    MATCH (n) WHERE elementId(n) = $element_id
                    REMOVE n.`{prop_key}`
                    """
                    await session.run(remove_prop_query, element_id=element_id)
                    
                    self.created_identifiers += 1
                    self.removed_properties += 1
                
                self.processed_nodes += 1
                if self.processed_nodes % 100 == 0: # Log progress every 100 nodes
                    self.logger.info(f"Processed {self.processed_nodes} nodes so far...")

            self.logger.info(f"Completed processing. Processed {self.processed_nodes} nodes, "
                             f"updated {self.updated_uuid_properties} uuid properties, "
                             f"created {self.created_identifiers} identifier relationships, "
                             f"removed {self.removed_properties} old properties.")

            return {
                "status": "success",
                "processed_nodes": self.processed_nodes,
                "updated_uuid_properties": self.updated_uuid_properties,
                "created_identifiers": self.created_identifiers,
                "removed_properties": self.removed_properties
            }
            
        except Exception as e:
            self.logger.error(f"Error executing IdentifierFixTask: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "processed_nodes": getattr(self, 'processed_nodes', 0),
                "updated_uuid_properties": getattr(self, 'updated_uuid_properties', 0),
                "created_identifiers": getattr(self, 'created_identifiers', 0),
                "removed_properties": getattr(self, 'removed_properties', 0)
            }
        finally:
            if session:
                await session.close()

    def validate_config(self) -> bool:
        """
        Validate task configuration.
        
        Returns:
            True if configuration is valid
        """
        # IdentifierFixTask doesn't require specific configuration options
        return True

    def get_dependencies(self) -> List[str]:
        """
        Get list of task IDs that this task depends on.
        
        Returns:
            List of task IDs
        """
        # This task might depend on data import tasks, but no specific dependencies are required by the base definition
        return []