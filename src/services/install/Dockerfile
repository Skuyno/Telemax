FROM python:3.12-slim

WORKDIR /code

# docker CLI + compose plugin — this service drives the HOST's Docker daemon
# via the bind-mounted /var/run/docker.sock (Docker-outside-of-Docker), it
# never runs its own nested daemon.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && . /etc/os-release \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY shared_secrets.yml .

# VERSION is read at runtime from the bind-mounted repo root (REPO_ROOT),
# not copied in at build time — it lives outside this service's own build
# context (COPY can't reach above it), and reading it live means a VERSION
# bump doesn't require rebuilding this image.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8900"]
