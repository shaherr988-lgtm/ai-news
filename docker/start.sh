#!/bin/sh
# Entry point for the Render web service: create tables/extension if they
# don't exist yet (idempotent), then start the server. Kept as its own
# script — not an inline `sh -c "... && ..."` string in render.yaml's
# dockerCommand — because Render's own parsing of that field mangled the
# quoting and `&&`, causing the whole line to be treated as one unknown
# command (see the "sh: 1: ...: not found" / exit 127 failure).
set -e

python -m scripts.create_tables
exec uvicorn apps.web.main:app --host 0.0.0.0 --port "${PORT:-8000}"
