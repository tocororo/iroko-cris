#!/bin/sh

# Wait for Neo4j with extended timeout and retries
MAX_RETRIES=60
RETRY_DELAY=5
COUNT=0

echo "Waiting for Memgraph to be ready..."
while [ $COUNT -lt $MAX_RETRIES ]; do
    if python3 -c "
import socket, sys
try:
    sock = socket.create_connection(('memgraph', 7687), timeout=5)
    sock.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
"; then
        echo "Memgraph is ready!"
        break
    fi
    COUNT=$((COUNT+1))
    echo "Attempt $COUNT/$MAX_RETRIES - Memgraph not ready, retrying in $RETRY_DELAY seconds..."
    sleep $RETRY_DELAY
done

if [ $COUNT -eq $MAX_RETRIES ]; then
    echo "Error: Memgraph not ready after $((MAX_RETRIES * RETRY_DELAY)) seconds"
    exit 1
fi

# Wait for PostgreSQL
COUNT=0
echo "Waiting for PostgreSQL to be ready..."
while [ $COUNT -lt $MAX_RETRIES ]; do
    if python3 -c "
import socket, sys
try:
    sock = socket.create_connection(('postgres', 5432), timeout=5)
    sock.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
"; then
        echo "PostgreSQL is ready!"
        break
    fi
    COUNT=$((COUNT+1))
    echo "Attempt $COUNT/$MAX_RETRIES - PostgreSQL not ready, retrying in $RETRY_DELAY seconds..."
    sleep $RETRY_DELAY
done

if [ $COUNT -eq $MAX_RETRIES ]; then
    echo "Error: PostgreSQL not ready after $((MAX_RETRIES * RETRY_DELAY)) seconds"
    exit 1
fi

# Start FastAPI
exec uvicorn iroko.main:app --host 0.0.0.0 --port 8000