#!/usr/bin/env bash
# THelpViewer — unified management script.
#
# Usage:
#   ./thelp.sh download             Download help files from the internet
#   ./thelp.sh build                Build UHF 2.0 .json.gz bundles
#   ./thelp.sh build --with-dos-reference  Build default groups plus DOS reference help
#   ./thelp.sh catalog              Rebuild helps/catalog.json from existing bundles
#   ./thelp.sh serve start          Start FastAPI server in background (port 5448)
#   ./thelp.sh serve stop           Stop local FastAPI server
#   ./thelp.sh serve status         Show local FastAPI server status
#   ./thelp.sh serve restart        Restart local FastAPI server
#   ./thelp.sh update               No-op (assets are served directly)
#   ./thelp.sh docker start         Start Docker container
#   ./thelp.sh docker stop          Stop Docker container
#   ./thelp.sh docker restart       Restart Docker container
#   ./thelp.sh docker build         Build Docker images
#   ./thelp.sh all                  Full pipeline: download, build, Docker start
#
# Commands can be combined:
#   ./thelp.sh download build       Download, then build
#   ./thelp.sh build serve start    Build, then serve locally
#   ./thelp.sh update docker restart  Sync assets and restart Docker
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCES_DIR="${THELP_SOURCES_DIR:-${SCRIPT_DIR}/sources}"
DOWNLOADS_DIR="${THELP_DOWNLOADS_DIR:-${THELP_STATE_DIR:-${SCRIPT_DIR}/var}/downloads}"
HELPS_DIR="${THELP_HELPS_DIR:-${SCRIPT_DIR}/helps}"
WEB_DIR="${THELP_WEB_DIR:-${SCRIPT_DIR}/www}"
INDEX_PATH="${THELP_INDEX_PATH:-${WEB_DIR}/index.html}"
DOCS_DIR="${THELP_DOCS_DIR:-${SCRIPT_DIR}/docs}"
ASSETS_DIR="${THELP_ASSETS_DIR:-${WEB_DIR}/assets}"
README_PATH="${THELP_README_PATH:-${SCRIPT_DIR}/README.md}"
CHANGELOG_PATH="${THELP_CHANGELOG_PATH:-${SCRIPT_DIR}/CHANGELOG.md}"
STATE_DIR="${THELP_STATE_DIR:-${SCRIPT_DIR}/var}"
HOST="${THELP_HOST:-0.0.0.0}"
PID_FILE="${THELP_PID_FILE:-${STATE_DIR}/uvicorn.pid}"
LOG_FILE="${THELP_LOG_FILE:-${STATE_DIR}/uvicorn.log}"
SERVER_FOREGROUND="${THELP_SERVER_FOREGROUND:-0}"

resolve_python_candidate() {
    if [ -x "$1" ]; then
        printf '%s\n' "$1"
        return 0
    fi
    command -v "$1" 2>/dev/null
}

python_auto_supported() {
    "$1" - <<'PY' >/dev/null 2>&1
import sys

version = sys.version_info[:2]
raise SystemExit(not ((3, 10) <= version < (3, 14)))
PY
}

PYTHON_BIN=""
if [ -n "${THELP_PYTHON:-}" ]; then
    PYTHON_BIN="${THELP_PYTHON}"
else
    for candidate in \
        "${SCRIPT_DIR}/.venv/bin/python3" \
        "${SCRIPT_DIR}/.venv/bin/python" \
        python3.13 \
        python3.12 \
        python3.11 \
        python3.10 \
        python3
    do
        if candidate_path="$(resolve_python_candidate "$candidate")" && python_auto_supported "$candidate_path"; then
            PYTHON_BIN="$candidate_path"
            break
        fi
    done
    if [ -z "${PYTHON_BIN}" ]; then
        PYTHON_BIN="$(command -v python3)"
    fi
fi

do_download=false
do_build=false
do_catalog=false
do_serve=false
do_serve_stop=false
do_serve_status=false
do_serve_restart=false
do_update=false
do_start=false
do_stop=false
do_restart=false
do_docker_build=false
do_all=false
PORT="${THELP_PORT:-5448}"
download_args=()
build_groups=()
with_dos_reference=false

catalog_build_group_values() {
    local mode="${1:-all}"
    "${PYTHON_BIN}" - "$mode" <<'PY'
from thelpviewer.downloader.catalog import all_build_groups
import sys

default_only = len(sys.argv) > 1 and sys.argv[1] == "default"
for key in all_build_groups(default_only=default_only):
    print(key)
PY
}

mapfile -t DEFAULT_BUILD_GROUPS < <(catalog_build_group_values default)
mapfile -t ALL_BUILD_GROUPS < <(catalog_build_group_values all)

normalize_build_group() {
    "${PYTHON_BIN}" - "$1" <<'PY'
from thelpviewer.downloader.catalog import normalize_build_group
import sys

resolved = normalize_build_group(sys.argv[1])
if resolved is None:
    raise SystemExit(1)
print(resolved)
PY
}

build_group_list_text() {
    printf '%s' "${ALL_BUILD_GROUPS[*]}" | tr ' ' ','
}

selected_build_groups() {
    local requested=()
    local expanded=()
    local seen=" "
    local group

    if [ ${#build_groups[@]} -eq 0 ]; then
        requested=("${DEFAULT_BUILD_GROUPS[@]}")
    else
        requested=("${build_groups[@]}")
    fi
    if $with_dos_reference; then
        requested+=("dos-reference")
    fi

    for group in "${requested[@]}"; do
        if [ "${group}" = "all" ]; then
            expanded+=("${ALL_BUILD_GROUPS[@]}")
        else
            expanded+=("${group}")
        fi
    done

    for group in "${expanded[@]}"; do
        case "${seen}" in
            *" ${group} "*)
                ;;
            *)
                printf '%s\n' "${group}"
                seen+="${group} "
                ;;
        esac
    done
}

selected_build_source_roots() {
    "${PYTHON_BIN}" - "${SOURCES_DIR}" "$@" <<'PY'
from pathlib import Path
import sys
from thelpviewer.downloader.catalog import build_group_for_source_root

source_dir = Path(sys.argv[1])
selected = set(sys.argv[2:])
for root in sorted(source_dir.iterdir()):
    if root.is_dir() and build_group_for_source_root(root.name) in selected:
        print(root)
PY
}

remove_group_outputs() {
    local target_dir="$1"
    shift
    [ -d "$target_dir" ] || return 0

    local path
    while IFS= read -r -d '' path; do
        rm -rf "$path"
    done < <("${PYTHON_BIN}" - "$target_dir" "$@" <<'PY'
from pathlib import Path
import sys
from thelpviewer.downloader.catalog import build_group_for_help_root

help_dir = Path(sys.argv[1])
selected = set(sys.argv[2:])
for root in help_dir.iterdir():
    if root.is_dir() and build_group_for_help_root(root.name) in selected:
        sys.stdout.buffer.write(str(root).encode() + b"\0")
PY
    )
}

has_download_data() {
    [ -d "${DOWNLOADS_DIR}" ] && find "${DOWNLOADS_DIR}" -type f -print -quit | grep -q .
}

has_source_data() {
    [ -d "${SOURCES_DIR}" ] && find "${SOURCES_DIR}" -type f -print -quit | grep -q .
}

has_help_bundles() {
    [ -d "${HELPS_DIR}" ] && find "${HELPS_DIR}" -name '*.json.gz' -type f -print -quit | grep -q .
}

have_uvicorn() {
    "${PYTHON_BIN}" -c 'import uvicorn' >/dev/null 2>&1
}

have_docker() {
    command -v docker >/dev/null 2>&1
}

docker_daemon_running() {
    docker info >/dev/null 2>&1
}

server_process_matches() {
    local pid="$1"
    local command_line
    command_line="$(ps -p "${pid}" -o command= 2>/dev/null || true)"
    [[ "${command_line}" == *"uvicorn thelpviewer.server.app:app"* ]]
}

server_running() {
    if [ ! -f "${PID_FILE}" ]; then
        return 1
    fi
    local pid
    pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
    if [[ ! "${pid}" =~ ^[1-9][0-9]*$ ]]; then
        rm -f "${PID_FILE}"
        return 1
    fi
    if kill -0 "${pid}" 2>/dev/null && server_process_matches "${pid}"; then
        return 0
    fi
    rm -f "${PID_FILE}"
    return 1
}

start_server_background() {
    mkdir -p "${HELPS_DIR}" "${STATE_DIR}"
    if ! have_uvicorn; then
        echo "[thelp] missing dependency: uvicorn is not installed for ${PYTHON_BIN}."
        echo "[thelp] install requirements first: pip install -r requirements.txt"
        return 1
    fi
    if server_running; then
        echo "[thelp] server already running (pid $(cat "${PID_FILE}"))."
        echo "[thelp] url: http://localhost:${PORT}/"
        echo "[thelp] log: ${LOG_FILE}"
        return 0
    fi
    export THELP_PORT="${PORT}"
    export THELP_HOST="${HOST}"
    export THELP_WEB_DIR="${WEB_DIR}"
    export THELP_INDEX_PATH="${INDEX_PATH}"
    export THELP_HELPS_DIR="${HELPS_DIR}"
    export THELP_DOCS_DIR="${DOCS_DIR}"
    export THELP_ASSETS_DIR="${ASSETS_DIR}"
    export THELP_README_PATH="${README_PATH}"
    export THELP_CHANGELOG_PATH="${CHANGELOG_PATH}"
    export THELP_STATE_DIR="${STATE_DIR}"
    nohup "${PYTHON_BIN}" -m uvicorn thelpviewer.server.app:app --host "${HOST}" --port "${PORT}" > "${LOG_FILE}" 2>&1 &
    echo $! > "${PID_FILE}"
    sleep 1
    if server_running; then
        echo "[thelp] serving on http://localhost:${PORT}/"
        echo "[thelp] pid: $(cat "${PID_FILE}")"
        echo "[thelp] log: ${LOG_FILE}"
        return 0
    fi
    echo "[thelp] server failed to start."
    echo "[thelp] inspect log: ${LOG_FILE}"
    return 1
}

start_server_foreground() {
    mkdir -p "${HELPS_DIR}" "${STATE_DIR}"
    if ! have_uvicorn; then
        echo "[thelp] missing dependency: uvicorn is not installed for ${PYTHON_BIN}."
        echo "[thelp] install requirements first: pip install -r requirements.txt"
        return 1
    fi
    export THELP_PORT="${PORT}"
    export THELP_HOST="${HOST}"
    export THELP_WEB_DIR="${WEB_DIR}"
    export THELP_INDEX_PATH="${INDEX_PATH}"
    export THELP_HELPS_DIR="${HELPS_DIR}"
    export THELP_DOCS_DIR="${DOCS_DIR}"
    export THELP_ASSETS_DIR="${ASSETS_DIR}"
    export THELP_README_PATH="${README_PATH}"
    export THELP_CHANGELOG_PATH="${CHANGELOG_PATH}"
    export THELP_STATE_DIR="${STATE_DIR}"
    echo "[thelp] serving in foreground on http://localhost:${PORT}/"
    exec "${PYTHON_BIN}" -m uvicorn thelpviewer.server.app:app --host "${HOST}" --port "${PORT}"
}

stop_server() {
    if ! server_running; then
        echo "[thelp] server is not running."
        return 0
    fi
    local pid
    pid="$(cat "${PID_FILE}")"
    kill -- "${pid}"
    rm -f "${PID_FILE}"
    echo "[thelp] stopped server pid ${pid}."
}

args=("$@")
i=0
while [ $i -lt $# ]; do
    arg="${args[$i]}"
    case "$arg" in
        download) do_download=true ;;
        build)    do_build=true ;;
        convert)  do_build=true ;;
        catalog)  do_catalog=true ;;
        update)   do_update=true ;;
        all)      do_all=true ;;
        docker)
            i=$((i + 1))
            if [ $i -ge $# ]; then
                echo "[thelp] missing action after 'docker'. Expected: start|stop|restart|build"
                exit 1
            fi
            case "${args[$i]}" in
                start) do_start=true ;;
                stop) do_stop=true ;;
                restart) do_restart=true ;;
                build) do_docker_build=true ;;
                *)
                    echo "[thelp] unknown docker action: ${args[$i]}"
                    echo "[thelp] expected one of: start, stop, restart, build"
                    exit 1
                    ;;
            esac
            ;;
        serve|server)
            next_arg="${args[$((i + 1))]:-}"
            case "$next_arg" in
                start)
                    do_serve=true
                    i=$((i + 1))
                    ;;
                stop)
                    do_serve_stop=true
                    i=$((i + 1))
                    ;;
                status)
                    do_serve_status=true
                    i=$((i + 1))
                    ;;
                restart)
                    do_serve_restart=true
                    i=$((i + 1))
                    ;;
                ""|[0-9]*)
                    do_serve=true
                    ;;
                *)
                    echo "[thelp] unknown serve action: ${next_arg}"
                    echo "[thelp] expected one of: start, stop, status, restart"
                    exit 1
                    ;;
            esac
            ;;
        serve-stop|server-stop) do_serve_stop=true ;;
        serve-status|server-status) do_serve_status=true ;;
        --group)
            i=$((i + 1))
            if [ $i -ge $# ]; then
                echo "[thelp] missing value after --group. Available groups: $(build_group_list_text)"
                exit 1
            fi
            group_value="${args[$i]}"
            group_value="${group_value//,/ }"
            for group_token in ${group_value}; do
                if ! normalized_group="$(normalize_build_group "${group_token}")"; then
                    echo "[thelp] unknown build group: ${group_token}"
                    echo "[thelp] available groups: $(build_group_list_text)"
                    exit 1
                fi
                build_groups+=("${normalized_group}")
            done
            ;;
        --group=*|group=*|groups=*|build-group=*)
            group_value="${arg#--group=}"
            group_value="${group_value#group=}"
            group_value="${group_value#groups=}"
            group_value="${group_value#build-group=}"
            group_value="${group_value//,/ }"
            for group_token in ${group_value}; do
                if ! normalized_group="$(normalize_build_group "${group_token}")"; then
                    echo "[thelp] unknown build group: ${group_token}"
                    echo "[thelp] available groups: $(build_group_list_text)"
                    exit 1
                fi
                build_groups+=("${normalized_group}")
            done
            ;;
        --with-dos-reference) with_dos_reference=true ;;
        start)    do_start=true ;;
        stop)     do_stop=true ;;
        restart)  do_restart=true ;;
        [0-9]*)   PORT="$arg" ;;
        *)        download_args+=("$arg") ;;
    esac
    i=$((i + 1))
done

# "all" enables the full pipeline
if $do_all; then
    do_download=true
    do_build=true
    do_start=true
fi

if ($do_serve || $do_serve_restart || $do_start || $do_restart || $do_catalog) && ! $do_build && ! has_help_bundles; then
    echo "[thelp] help bundle directory je prázdny, zapínam build."
    do_build=true
fi

needs_input_data=false
if $do_build || $do_serve || $do_serve_restart || $do_start || $do_restart; then
    needs_input_data=true
fi

if $needs_input_data && ! $do_download && ! has_source_data; then
    echo "[thelp] sources/ je prázdny, zapínam download."
    do_download=true
fi

if $with_dos_reference && ! $do_build; then
    echo "[thelp] --with-dos-reference requires build or all."
    exit 1
fi

# No args → show help
if ! $do_download && ! $do_build && ! $do_catalog && ! $do_serve && ! $do_serve_stop && ! $do_serve_status && ! $do_serve_restart && ! $do_update && ! $do_start && ! $do_stop && ! $do_restart; then
    echo "THelpViewer"
    echo ""
    echo "Usage: ./thelp.sh <command> [command...] [port]"
    echo ""
    echo "Commands:"
    echo "  download    Download help files from the internet"
    echo "  build       Build UHF 2.0 .json.gz bundles"
    echo "  convert     Convert source files in ${SOURCES_DIR} into ${HELPS_DIR} (alias for build)"
    echo "  catalog     Rebuild ${HELPS_DIR}/catalog.json from existing bundles"
    echo "  serve start     Start FastAPI server in background (default port ${PORT})"
    echo "  serve stop      Stop local FastAPI server"
    echo "  serve status    Show local FastAPI server status"
    echo "  serve restart   Restart local FastAPI server"
    echo "  update      No-op; assets/docs are served directly from source directories"
    echo "  docker start    Start Docker container"
    echo "  docker stop     Stop Docker container"
    echo "  docker restart  Restart Docker container (down + build + up)"
    echo "  docker build    Build Docker images (docker compose build)"
    echo "  all             Full pipeline: download + build + docker start"
    echo ""
    echo "Build groups (use with build): $(build_group_list_text)"
    echo "Default build groups: $(printf '%s' "${DEFAULT_BUILD_GROUPS[*]}" | tr ' ' ',')"
    echo "Use --with-dos-reference to add DOS reference help to a build."
    echo ""
    echo "Examples:"
    echo "  ./thelp.sh all                     # Everything from scratch"
    echo "  ./thelp.sh build serve start       # Build and start local server"
    echo "  ./thelp.sh build --group borland   # Generate only Borland bundles"
    echo "  ./thelp.sh build --group scorpion  # Add Scorpions bundles on demand"
    echo "  ./thelp.sh build --with-dos-reference # Build defaults and DOS reference help together"
    echo "  ./thelp.sh build --group borland,microsoft  # Generate selected groups"
    echo "  ./thelp.sh build --group all       # Build all groups including Scorpions"
    echo "  ./thelp.sh serve start 5450        # Start local server on port 5450"
    echo "  ./thelp.sh serve status            # Show local server status"
    echo "  ./thelp.sh serve restart           # Restart local server"
    echo "  ./thelp.sh docker start            # Start Docker container"
    echo "  ./thelp.sh docker stop             # Stop Docker container"
    echo "  ./thelp.sh docker restart          # Rebuild and restart Docker"
    echo "  ./thelp.sh catalog                 # Rebuild help catalog only"
    echo "  ./thelp.sh download build          # Download sources and build"
    echo "  ./thelp.sh download tp olddos      # Forward selectors to downloader"
    exit 0
fi

if $do_serve_status; then
    if server_running; then
        echo "[thelp] server is running."
        echo "[thelp] pid: $(cat "${PID_FILE}")"
        echo "[thelp] url: http://localhost:${PORT}/"
        echo "[thelp] log: ${LOG_FILE}"
    else
        echo "[thelp] server is not running."
    fi
fi

if $do_serve_stop; then
    stop_server
fi

if $do_serve_restart; then
    stop_server
    do_serve=true
fi

if $do_download; then
    echo "=== Download ==="
    cd "${SCRIPT_DIR}"
    "${PYTHON_BIN}" -m thelpviewer.downloader "${download_args[@]}"
    echo "Download complete."
    echo ""
fi

if $do_build; then
    echo "=== Build ==="
    echo "Sources: ${SOURCES_DIR}"
    echo "Bundles: ${HELPS_DIR}"
    mapfile -t active_build_groups < <(selected_build_groups)
    echo "Groups: ${active_build_groups[*]}"
    echo ""
    cd "${SCRIPT_DIR}"
    build_parent_dir="$(dirname "${HELPS_DIR}")"
    mkdir -p "${STATE_DIR}" "${build_parent_dir}"
    build_tmp_dir="$(mktemp -d "${build_parent_dir}/.helps-build.XXXXXX")"
    build_backup_dir="${HELPS_DIR}.prev.$$"
    rm -rf "${build_backup_dir}"

    if { [ ${#build_groups[@]} -gt 0 ] || $with_dos_reference; } && [ -d "${HELPS_DIR}" ]; then
        cp -a "${HELPS_DIR}/." "${build_tmp_dir}/"
        remove_group_outputs "${build_tmp_dir}" "${active_build_groups[@]}"
    fi

    mapfile -t build_roots < <(selected_build_source_roots "${active_build_groups[@]}")
    if [ ${#build_roots[@]} -eq 0 ]; then
        rm -rf "${build_tmp_dir}"
        echo "[thelp] no matching source groups found under ${SOURCES_DIR}."
        exit 1
    fi

    for build_root in "${build_roots[@]}"; do
        echo "[thelp] build root: ${build_root#"${SOURCES_DIR}"/}"
        if ! "${PYTHON_BIN}" -m thelpviewer.converter --bundle --bundle-layout helps "${build_root}" "${build_tmp_dir}"; then
            rm -rf "${build_tmp_dir}"
            echo "[thelp] build failed."
            exit 1
        fi
    done

    echo "[thelp] rebuilding staged catalog."
    if ! "${PYTHON_BIN}" tools/rebuild_catalog.py "${build_tmp_dir}" --output "${build_tmp_dir}/catalog.json"; then
        rm -rf "${build_tmp_dir}"
        echo "[thelp] failed to rebuild the staged catalog."
        exit 1
    fi

    if [ -e "${HELPS_DIR}" ]; then
        mv "${HELPS_DIR}" "${build_backup_dir}"
    fi
    if ! mv "${build_tmp_dir}" "${HELPS_DIR}"; then
        echo "[thelp] failed to activate new help bundles."
        if [ -e "${build_backup_dir}" ]; then
            mv "${build_backup_dir}" "${HELPS_DIR}" || true
        fi
        rm -rf "${build_tmp_dir}"
        exit 1
    fi
    rm -rf "${build_backup_dir}"
    echo "Build complete."
    echo ""
fi

if $do_catalog; then
    echo "=== Rebuild catalog ==="
    cd "${SCRIPT_DIR}"
    "${PYTHON_BIN}" tools/rebuild_catalog.py "${HELPS_DIR}" --output "${HELPS_DIR}/catalog.json"
    echo "Catalog rebuilt."
    echo ""
fi

if $do_update; then
    echo "=== Update assets ==="
    echo "No-op: FastAPI serves assets from ${ASSETS_DIR} and docs from ${DOCS_DIR} directly."
    echo ""
fi

docker_preflight() {
    if ! have_docker; then
        echo "[thelp] docker command was not found."
        echo "[thelp] install Docker Desktop or use ./thelp.sh serve start for local runtime."
        return 1
    fi
    if ! docker_daemon_running; then
        echo "[thelp] Docker daemon is not running."
        echo "[thelp] start Docker Desktop (or another Docker runtime) and retry."
        echo "[thelp] local fallback without Docker: ./thelp.sh serve start ${PORT}"
        return 1
    fi
    return 0
}

ensure_docker_helps_readable() {
    if [ ! -f "${HELPS_DIR}/catalog.json" ]; then
        echo "[thelp] missing HELP catalog: ${HELPS_DIR}/catalog.json"
        return 1
    fi
    echo "=== Check HELP files at original paths ==="
    find "${HELPS_DIR}" -type f -exec cksum {} + >/dev/null
}

if $do_start; then
    echo "=== Start Docker ==="
    cd "${SCRIPT_DIR}"
    docker_preflight || exit 1
    ensure_docker_helps_readable || exit 1
    export THELP_PORT="${PORT}"
    docker compose up -d --build
    echo ""
    echo "Ready: http://localhost:${PORT}/"
    echo ""
fi

if $do_stop; then
    echo "=== Stop Docker ==="
    cd "${SCRIPT_DIR}"
    docker_preflight || exit 1
    export THELP_PORT="${PORT}"
    docker compose down
    echo ""
    echo "Stopped Docker services."
    echo ""
fi

if $do_restart; then
    echo "=== Restart Docker ==="
    cd "${SCRIPT_DIR}"
    docker_preflight || exit 1
    ensure_docker_helps_readable || exit 1
    export THELP_PORT="${PORT}"
    docker compose down
    docker compose build --no-cache
    docker compose up -d
    echo ""
    echo "Ready: http://localhost:${PORT}/"
    echo ""
fi

if $do_docker_build; then
    echo "=== Docker build ==="
    cd "${SCRIPT_DIR}"
    docker_preflight || exit 1
    export THELP_PORT="${PORT}"
    docker compose build
    echo ""
    echo "Docker images built."
    echo ""
fi

if $do_serve; then
    cd "${SCRIPT_DIR}"
    if [ "${SERVER_FOREGROUND}" = "1" ]; then
        start_server_foreground
    else
        start_server_background
    fi
fi
