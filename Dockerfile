FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# Debian separates the RAR decoder from 7zip; unar alone cannot decode every
# historical solid/SFX RAR. Keep the fallback usable on both amd64 and arm64.
RUN sed -i 's/^Components: main$/Components: main non-free/' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends 7zip 7zip-rar unar dosbox \
    && (command -v 7zz || command -v 7z) && command -v unar && command -v lsar && command -v dosbox \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

EXPOSE 5448

# Runtime files are bind-mounted by docker-compose. The image only provides Python + deps.
CMD ["/bin/bash", "-lc", "chmod +x /app/thelp.sh && THELP_SERVER_FOREGROUND=1 exec /app/thelp.sh serve ${THELP_PORT:-5448}"]
