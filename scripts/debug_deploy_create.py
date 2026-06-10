#!/usr/bin/env python3
"""Debug harness for `crewai deploy create` / provisioning failures."""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

LOG_PATH = Path("/home/d3/Github/d3hl_infra_crew/.cursor/debug-556310.log")
SESSION_ID = "556310"
RUN_ID = os.environ.get("DEBUG_RUN_ID", "pre-fix")


def log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    entry = {
        "sessionId": SESSION_ID,
        "runId": RUN_ID,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    # #region agent log
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    # #endregion


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, cwd=str(cwd) if cwd else None
    )
    return proc.returncode, proc.stdout, proc.stderr


def main() -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    root = Path("/home/d3/Github/d3hl_infra_crew")

    code, out, err = run(["git", "remote", "get-url", "origin"], cwd=root)
    origin = out.strip() if code == 0 else None
    # #region agent log
    log("B", "debug_deploy_create.py:main", "git_origin_url", {
        "exit_code": code, "origin_url": origin,
    })
    # #endregion

    code, out, err = run(
        ["gh", "repo", "view", "--json", "nameWithOwner,isPrivate,url"],
        cwd=root,
    )
    repo_meta = {}
    if code == 0 and out.strip():
        repo_meta = json.loads(out)
    owner_repo = repo_meta.get("nameWithOwner", "d3hl/d3hl_infra_crew")
    unauth_status = None
    try:
        with urllib.request.urlopen(
            f"https://api.github.com/repos/{owner_repo}", timeout=15
        ) as resp:
            unauth_status = resp.status
    except urllib.error.HTTPError as exc:
        unauth_status = exc.code
    # #region agent log
    log("A", "debug_deploy_create.py:main", "github_repo_metadata", {
        "exit_code": code,
        "name_with_owner": repo_meta.get("nameWithOwner"),
        "is_private": repo_meta.get("isPrivate"),
        "canonical_url": repo_meta.get("url"),
        "origin_matches_canonical": origin == repo_meta.get("url") + ".git" if repo_meta.get("url") else None,
        "unauthenticated_api_status": unauth_status,
        "amp_needs_github_app": unauth_status == 404 and repo_meta.get("isPrivate"),
    })
    # #endregion

    code, out, err = run(["uv", "run", "crewai", "deploy", "status"], cwd=root, timeout=60)
    # #region agent log
    log("A", "debug_deploy_create.py:main", "deploy_status", {
        "exit_code": code,
        "output": (out + err).strip()[-800:],
    })
    # #endregion

    code, out, err = run(["uv", "run", "crewai", "deploy", "logs"], cwd=root, timeout=60)
    combined = (out + err).strip()
    # #region agent log
    log("A", "debug_deploy_create.py:main", "deploy_logs_tail", {
        "exit_code": code,
        "repository_not_found": "Repository not found" in combined,
        "provisioning_failed": "Provisioning failed" in combined,
        "tail": combined[-1200:],
    })
    # #endregion

    pyproject = (root / "pyproject.toml").stat().st_mtime
    uv_lock = root / "uv.lock"
    lock_stale = uv_lock.exists() and uv_lock.stat().st_mtime < pyproject
    # #region agent log
    log("C", "debug_deploy_create.py:main", "lockfile_state", {
        "uv_lock_exists": uv_lock.exists(),
        "lock_stale_vs_pyproject": lock_stale,
    })
    # #endregion

    print(f"Debug complete. Logs: {LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
