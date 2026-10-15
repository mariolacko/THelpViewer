FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends 7zip unar dosbox \
    && (command -v 7zz || command -v 7z) && command -v unar && command -v lsar && command -v dosbox \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

EXPOSE 5448

# Runtime files are bind-mounted by docker-compose. The image only provides Python + deps.
CMD ["/bin/bash", "-lc", "chmod +x /app/thelp.sh && THELP_SERVER_FOREGROUND=1 exec /app/thelp.sh serve ${THELP_PORT:-5448}"]
