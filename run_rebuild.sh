#!/bin/bash
set -e

CONTAINER_NAME="iroko-rebuild"
IMAGE="${IMAGE:-localhost/iroko/iroko-cris:sceiba-prod-1}"
LOG_FILE="./logs/rebuild-$(date +%Y%m%d-%H%M%S).log"

# Load production env vars
if [ -f ./.env.production ]; then
    set -a
    source ./.env.production
    set +a
else
    echo "❌ .env.production file not found"
    exit 1
fi

# Ensure logs directory exists
mkdir -p ./logs

# Stop and remove existing rebuild container if present
if podman container exists "$CONTAINER_NAME" >/dev/null 2>&1; then
    echo "🔄 Stopping and removing existing container: $CONTAINER_NAME"
    podman stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    podman rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
fi

echo "🚀 Starting rebuild in detached container '$CONTAINER_NAME'..."
echo "   Logs: $LOG_FILE"
echo "   Monitor: podman logs -f $CONTAINER_NAME"

podman run -d \
    --name "$CONTAINER_NAME" \
    --hostname "$CONTAINER_NAME" \
    --network iroko-net \
    --restart on-failure:2 \
    --env-file ./.env.production \
    --memory=2g \
    -v "$(pwd)/rebuild.py:/app/rebuild.py:Z,ro" \
    -v "$(pwd)/.data-init:/app/.data-init:Z,rw" \
    -v "$(pwd)/logs:/app/logs:Z,rw" \
    -v "$(pwd)/docs:/app/docs:Z,ro" \
    -v "$(pwd)/.data:/app/.data:Z,rw" \
    --entrypoint="" \
    "$IMAGE" \
    sh -c "
      echo '=== Rebuild container started at \$(date) ==='
      exec python /app/rebuild.py 2>&1 | tee /app/logs/rebuild-latest.log
    "

echo "✅ Container '$CONTAINER_NAME' started."
echo ""
echo "📊 Commands:"
echo "   View live logs:  podman logs -f $CONTAINER_NAME"
echo "   Check status:    podman inspect $CONTAINER_NAME --format='{{.State.Status}}'"
echo "   Persistent log:  $LOG_FILE"
