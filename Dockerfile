FROM python:3.12-slim

WORKDIR /app

# Copy converter package and build script
COPY converter/ /app/converter/
COPY downloader/ /app/downloader/
COPY thelp.sh /app/thelp.sh
RUN chmod +x /app/thelp.sh

# Sources are mounted read-only, downloads and www are volumes
VOLUME ["/app/sources", "/app/downloads", "/app/www"]

EXPOSE 5448

# Default: serve only (no rebuild on restart).
# To rebuild: docker compose exec viewer ./thelp.sh build
# To rebuild + serve: docker compose run viewer ./thelp.sh build serve 5448
CMD ["/app/thelp.sh", "serve", "5448"]
