#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

tmp_list="$(mktemp "${TMPDIR:-/tmp}/thelp-clean.XXXXXX")"
trap 'rm -f "${tmp_list}"' EXIT

find . \
  -path './.git' -prune -o \
  \( \
    -type d \( \
      -name '__pycache__' -o \
      -name '.pytest_cache' -o \
      -name '.mypy_cache' -o \
      -name '.ruff_cache' -o \
      -name '.cache' -o \
      -name 'htmlcov' -o \
      -name 'build' -o \
      -name 'dist' -o \
      -name 'out' \
    \) -o \
    -type f \( \
      -name '*.pyc' -o \
      -name '*.pyo' -o \
      -name '.coverage' -o \
      -name 'coverage.xml' -o \
      -name '.DS_Store' \
    \) -o \
    -path './var/uvicorn.pid' -o \
    -path './var/uvicorn.log' -o \
    -path './var/helps-build.*' \
  \) \
  -print > "${tmp_list}"

if [ ! -s "${tmp_list}" ]; then
  echo "[clean] nothing to remove."
  exit 0
fi

echo "[clean] removing ballast:"
while IFS= read -r path; do
  [ -n "${path}" ] || continue
  printf '  %s\n' "${path#./}"
  rm -rf "${path}"
done < "${tmp_list}"

echo "[clean] done."