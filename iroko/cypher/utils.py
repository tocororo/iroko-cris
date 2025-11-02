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
            r"INSERT|UPDATE|RENAME|FOREACH|LOAD\s+CSV)\b",
            re.IGNORECASE | re.MULTILINE
        )
        
        # Allow specific CALL patterns that are read-only
        allowed_call_patterns = [
            r"CALL\s+db\.relationshipTypes\(\)",
            r"CALL\s+db\.labels\(\)",
            r"CALL\s+db\.propertyKeys\(\)",
            r"CALL\s+db\.nodeLabels\(\)",
            r"CALL\s+db\.counts\(\)",
            # Add more allowed CALL patterns as needed
        ]
        
        # Check if the query is an allowed CALL pattern
        is_allowed_call = any(
            re.search(pattern, query, re.IGNORECASE | re.MULTILINE) 
            for pattern in allowed_call_patterns
        )
        
        # If it's not an allowed CALL pattern, check for write operations
        if not is_allowed_call and write_operations.search(query):
            raise ValueError("Query contains potential write operations")