#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create additional users if needed
    CREATE USER iroko_app WITH PASSWORD 'iroko_app_password';
    GRANT CONNECT ON DATABASE iroko TO iroko_app;  # Changed database name
    
    -- You can add more initialization here if needed
EOSQL