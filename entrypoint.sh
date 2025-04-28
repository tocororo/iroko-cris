#!/bin/sh

# Wait for Neo4j with extended timeout and retries
MAX_RETRIES=60
RETRY_DELAY=5
COUNT=0

echo "Waiting for Neo4j to be ready..."
while [ $COUNT -lt $MAX_RETRIES ]; do
    if python3 -c "
import socket, sys
try:
    sock = socket.create_connection(('neo4j', 7687), timeout=5)
    sock.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
"; then
        echo "Neo4j is ready!"
        break
    fi
    COUNT=$((COUNT+1))
    echo "Attempt $COUNT/$MAX_RETRIES - Neo4j not ready, retrying in $RETRY_DELAY seconds..."
    sleep $RETRY_DELAY
done

if [ $COUNT -eq $MAX_RETRIES ]; then
    echo "Error: Neo4j not ready after $((MAX_RETRIES * RETRY_DELAY)) seconds"
    exit 1
fi

# Start FastAPI
exec uvicorn api.main:app --host 0.0.0.0 --port 8000