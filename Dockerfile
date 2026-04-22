FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5448

# Runtime files are bind-mounted by docker-compose. The image only provides Python + deps.
CMD ["/bin/bash", "-lc", "chmod +x /app/thelp.sh && THELP_SERVER_FOREGROUND=1 exec /app/thelp.sh serve ${THELP_PORT:-5448}"]
