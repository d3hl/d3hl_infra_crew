#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"

echo "== d3hl_infra_crew static baseline =="
echo "root: $ROOT"

if [[ "$ROOT" != "/home/d3/Github/d3hl_infra_crew" ]]; then
  echo "warning: expected /home/d3/Github/d3hl_infra_crew, got $ROOT"
fi

echo "== required files =="
required_files=(
  "AGENTS.md"
  "README.md"
  "feature_list.json"
  "claude-progress.md"
  "init.sh"
  "session-handoff.md"
  "pyproject.toml"
)
for file in "${required_files[@]}"; do
  test -f "$file"
  echo "ok: $file"
done

echo "== shell syntax =="
bash -n "$0"
echo "ok: init.sh syntax"

echo "== feature list json =="
python3 -m json.tool feature_list.json >/dev/null
echo "ok: feature_list.json"

echo "== python compile =="
uv run python -m compileall src tests

echo "== unit tests =="
uv run python -m unittest discover -s tests

echo "== git whitespace =="
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git diff --check
else
  echo "skip: not a git worktree"
fi

echo "static baseline complete"
