# Builder stage
FROM quay.io/lib/python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN useradd --system --uid 1001 --create-home --home-dir /home/iroko iroko

USER iroko
WORKDIR /app
ENV PATH="/home/iroko/.local/bin:$PATH"

# Copy only what's needed to install deps
COPY requirements.txt .

RUN pip install --user --no-cache-dir --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

COPY README.md .
COPY pyproject.toml .
COPY iroko ./iroko/
RUN ls -la iroko/  
RUN pip install --user --no-cache-dir .
RUN ls -lha /home/iroko/.local


RUN pip install --user --no-cache-dir .


# Production stage
FROM quay.io/lib/python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production

RUN addgroup --system --gid 1001 iroko && \
    adduser --system --uid 1001 --gid 1001 --home /home/iroko iroko

WORKDIR /app
USER iroko
ENV PATH="/home/iroko/.local/bin:$PATH"

# Copy installed packages
COPY --from=builder --chown=iroko:iroko /home/iroko/.local /home/iroko/.local
RUN ls -lha /home/iroko/.local/lib/python3.12/site-packages


COPY .data-init ./.data-init/
COPY docs ./docs/
COPY methodologies ./methodologies/

# Copy source code
# COPY --chown=iroko:iroko iroko ./iroko

# Copy entrypoint with executable permissions
COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh


EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]