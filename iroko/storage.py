from neo4j import AsyncGraphDatabase
import os
from iroko.config import app_settings  # Add this import

# Remove the dotenv import and update the Neo4jDB class:

class Neo4jDB:
    def __init__(self):
        self._driver = AsyncGraphDatabase.driver(
            app_settings.neo4j_uri,  # Use app_settings
            auth=(
                app_settings.neo4j_username,
                app_settings.neo4j_password
            ),
            database=app_settings.neo4j_database
        )
    
    async def close(self):
        await self._driver.close()
    
    async def get_session(self):
        return self._driver.session()

neo4j_db = Neo4jDB()