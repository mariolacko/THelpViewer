#!/usr/bin/env bash
# THelpViewer — unified management script.
#
# Usage:
#   ./thelp.sh download             Download help files from the internet
#   ./thelp.sh build                Build compressed .json.gz bundles
#   ./thelp.sh serve                Start HTTP server only (port 5448)
#   ./thelp.sh update               Sync JS/CSS/HTML assets to www/
#   ./thelp.sh restart              Restart Docker container
#   ./thelp.sh all                  Full pipeline: download, build, Docker up
#
# Commands can be combined:
#   ./thelp.sh download build       Download, then build
#   ./thelp.sh build serve          Build, then serve locally
#   ./thelp.sh update restart       Sync assets and restart Docker
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCES_DIR="${SCRIPT_DIR}/sources"
WWW_DIR="${SCRIPT_DIR}/www"
ASSETS_SRC="${SCRIPT_DIR}/converter/assets"
ASSETS_DST="${WWW_DIR}/assets"

do_download=false
do_build=false
do_serve=false
do_update=false
do_restart=false
do_all=false
PORT=5448

for arg in "$@"; do
    case "$arg" in
        download) do_download=true ;;
        build)    do_build=true ;;
        serve)    do_serve=true ;;
        update)   do_update=true ;;
        restart)  do_restart=true ;;
        all)      do_all=true ;;
        [0-9]*)   PORT="$arg" ;;
    esac
done

# "all" enables the full pipeline
if $do_all; then
    do_download=true
    do_build=true
    do_restart=true
fi

# No args → show help
if ! $do_download && ! $do_build && ! $do_serve && ! $do_update && ! $do_restart; then
    echo "THelpViewer"
    echo ""
    echo "Usage: ./thelp.sh <command> [command...] [port]"
    echo ""
    echo "Commands:"
    echo "  download    Download help files from the internet"
    echo "  build       Build compressed .json.gz bundles"
    echo "  serve       Start local HTTP server (default port ${PORT})"
    echo "  update      Sync JS/CSS/HTML assets from converter/ to www/"
    echo "  restart     Restart Docker container (rebuild + up)"
    echo "  all         Full pipeline: download + build + restart"
    echo ""
    echo "Examples:"
    echo "  ./thelp.sh all                  # Everything from scratch"
    echo "  ./thelp.sh build serve          # Build and serve locally"
    echo "  ./thelp.sh update restart       # Push asset changes to Docker"
    echo "  ./thelp.sh download build       # Download sources and build"
    exit 0
fi

if $do_download; then
    echo "=== Download ==="
    cd "${SCRIPT_DIR}"
    python3 -m downloader
    echo "Download complete."
    echo ""
fi

if $do_build; then
    echo "=== Build ==="
    echo "Sources: ${SOURCES_DIR}"
    echo "Output:  ${WWW_DIR}"
    echo ""
    cd "${SCRIPT_DIR}"
    python3 -m converter --bundle --clean "${SOURCES_DIR}" "${WWW_DIR}"
    echo "Build complete."
    echo ""
fi

if $do_update; then
    echo "=== Update assets ==="
    cp "${ASSETS_SRC}"/*.js "${ASSETS_DST}/"
    cp "${ASSETS_SRC}"/*.css "${ASSETS_DST}/"
    # Sync font files
    if [ -d "${ASSETS_SRC}/fonts" ]; then
        mkdir -p "${ASSETS_DST}/fonts"
        cp "${ASSETS_SRC}/fonts"/* "${ASSETS_DST}/fonts/" 2>/dev/null || true
    fi
    # Rebuild docs catalog
    if [ -d "${SCRIPT_DIR}/docs" ]; then
        cd "${SCRIPT_DIR}"
        python3 -c "
from converter.writers.bundle import _copy_docs
from pathlib import Path
_copy_docs(Path('docs'), Path('www/docs'), readme=Path('README.md'))
"
    fi
    echo "Assets synced: converter/assets/ → www/assets/"
    echo ""
fi

if $do_restart; then
    echo "=== Restart Docker ==="
    cd "${SCRIPT_DIR}"
    # Sync assets before rebuild
    cp "${ASSETS_SRC}"/*.js "${ASSETS_DST}/"
    cp "${ASSETS_SRC}"/*.css "${ASSETS_DST}/"
    docker compose down
    docker compose build --no-cache
    docker compose up -d
    echo ""
    echo "Ready: http://localhost:${PORT}/"
    echo ""
fi

if $do_serve; then
    echo "Serving on http://localhost:${PORT}"
    cd "${SCRIPT_DIR}"
    python3 -m http.server "${PORT}" --directory "${WWW_DIR}"
fi
