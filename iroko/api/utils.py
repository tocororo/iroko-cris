from fastapi import Depends
from iroko.storage import neo4j_db
import re

import logging

logger = logging.getLogger('iroko-cris')


def validate_cypher_query(query: str, readonly: bool = True):
    """Validate Cypher query for safety"""
    if readonly:
        write_operations = re.compile(
            r"\b(CREATE|SET|DELETE|REMOVE|MERGE|DETACH\s+DELETE|DROP|ALTER|"
            r"INSERT|UPDATE|RENAME|FOREACH|CALL|WITH|LOAD\s+CSV)\b",
            re.IGNORECASE | re.MULTILINE
        )
        
        if write_operations.search(query):
            raise ValueError("Query contains potential write operations")