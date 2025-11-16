# iroko-cris

**iroko** is a Current Research Information System(CRIS), based on [sceiba-ontology](https://github.com/tocororo/sceiba-ontology.git).

## Tech stack

- Neo4J
- FastAPI
- Angular
https://typesense.org/docs/guide/syncing-data-into-typesense.html
https://hub.researchgraph.org/typesense-and-neo4j-in-a-hybrid-information-retrieval-solution/

## run dev

```bash

uvicorn iroko.main:app --reload --host 0.0.0.0 --port 8000 --ssl-keyfile haproxy/ssl/iroko.key --ssl-certfile haproxy/ssl/iroko.crt

```
```bash
./deploy.sh  --start-from api --build 
```
## podman

podman-compose build --no-cache
podman-compose down -v && podman-compose up -d


podman exec iroko-api python /app/.data/map.py > map_execution.log 2>&1
podman exec --user root iroko-api python /app/.data/map.py > map_execution.log 2>&1
podman exec --user root iroko-api bash -c "nohup python /app/.data/map.py > /app/map_execution.log 2>&1 &"