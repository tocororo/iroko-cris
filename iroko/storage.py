from neo4j import AsyncGraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

class Neo4jDB:
    def __init__(self):
        self._driver = AsyncGraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(
                os.getenv("NEO4J_USERNAME"),
                os.getenv("NEO4J_PASSWORD")
            ),
            database= os.getenv("NEO4J_DATABASE")
        )
    
    async def close(self):
        await self._driver.close()
    
    async def get_session(self):
        return self._driver.session()


neo4j_db = Neo4jDB()

