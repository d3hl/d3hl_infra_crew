from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path("/home/d3/Github")

REPO_ALIASES = {
    "bootc": WORKSPACE_ROOT / "d3hl-rhel-bootc-orchestrator",
    "rhel-bootc-orchestrator": WORKSPACE_ROOT / "d3hl-rhel-bootc-orchestrator",
    "d3hl-rhel-bootc-orchestrator": WORKSPACE_ROOT / "d3hl-rhel-bootc-orchestrator",
    "cf": WORKSPACE_ROOT / "cf-controller",
    "cf-controller": WORKSPACE_ROOT / "cf-controller",
    "cloudflare": WORKSPACE_ROOT / "cf-controller",
    "proxmox": WORKSPACE_ROOT / "d3hl-managed-proxmox",
    "d3hl-managed-proxmox": WORKSPACE_ROOT / "d3hl-managed-proxmox",
    "agent-contract": WORKSPACE_ROOT / "agent-contract-master",
    "agent-contract-master": WORKSPACE_ROOT / "agent-contract-master",
}

COMPLETED_STATUSES = {"passing", "completed", "complete", "done"}
ACTIVE_STATUSES = {"in_progress", "active"}
BLOCKED_STATUSES = {"blocked"}


@dataclass
class FeatureSummary:
    id: str = "unknown"
    priority: int | None = None
    title: str = "unknown"
    status: str = "unknown"
    area: str = "unknown"
    next_step: str = ""
    dependencies: list[str] = field(default_factory=list)


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str


@dataclass
class RepoStateSnapshot:
    repo: str
    path: str
    exists: bool
    active_feature: FeatureSummary | None
    baseline_command: str | None
    git_status: str
    recent_commits: str
    claude_progress_excerpt: str
    feature_list_excerpt: str
    blockers: list[str]
    static_check: CommandResult | None = None

    def to_prompt_json(self) -> str:
        payload: dict[str, Any] = {
            "repo": self.repo,
            "path": self.path,
            "exists": self.exists,
            "baseline_command": self.baseline_command,
            "git_status": self.git_status,
            "recent_commits": self.recent_commits,
            "claude_progress_excerpt": self.claude_progress_excerpt,
            "feature_list_excerpt": self.feature_list_excerpt,
            "blockers": self.blockers,
            "active_feature": self.active_feature.__dict__ if self.active_feature else None,
        }
        if self.static_check:
            payload["static_check"] = self.static_check.__dict__
        return json.dumps(payload, indent=2, sort_keys=True)


def resolve_repo(target_repo: str) -> Path:
    raw = target_repo.strip()
    candidate = REPO_ALIASES.get(raw, Path(raw).expanduser())
    resolved = candidate.resolve()
    if not resolved.is_relative_to(WORKSPACE_ROOT):
        raise ValueError(f"target_repo must resolve under {WORKSPACE_ROOT}: {target_repo}")
    return resolved


def read_text(path: Path, max_chars: int = 12000) -> str:
    if not path.exists():
        return ""
    data = path.read_text(encoding="utf-8", errors="replace")
    if len(data) > max_chars:
        return data[:max_chars] + "\n...[truncated]"
    return data


def run_command(command: list[str], cwd: Path, timeout: int = 300) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env={**os.environ, "UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR", "/tmp/uv-cache")},
        )
    except FileNotFoundError:
        # e.g. git/uv not installed in a minimal container — degrade instead of crashing.
        return CommandResult(
            command=" ".join(command),
            returncode=127,
            stdout="",
            stderr=f"command not found: {command[0]}",
        )
    return CommandResult(
        command=" ".join(command),
        returncode=completed.returncode,
        stdout=completed.stdout[-12000:],
        stderr=completed.stderr[-12000:],
    )


def load_feature_list(repo_path: Path) -> dict[str, Any]:
    feature_path = repo_path / "feature_list.json"
    if not feature_path.exists():
        return {}
    return json.loads(feature_path.read_text(encoding="utf-8"))


def _feature_title(feature: dict[str, Any]) -> str:
    return str(feature.get("title") or feature.get("name") or feature.get("description") or "unknown")


def _priority(feature: dict[str, Any]) -> int:
    value = feature.get("priority", 9999)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 9999


def summarize_feature(feature: dict[str, Any]) -> FeatureSummary:
    return FeatureSummary(
        id=str(feature.get("id", "unknown")),
        priority=_priority(feature),
        title=_feature_title(feature),
        status=str(feature.get("status", "unknown")),
        area=str(feature.get("area", "unknown")),
        next_step=str(feature.get("nextStep") or feature.get("next_step") or ""),
        dependencies=[str(item) for item in feature.get("dependencies", [])],
    )


def select_active_feature(feature_list: dict[str, Any]) -> FeatureSummary | None:
    features = feature_list.get("features") or []
    if not isinstance(features, list) or not features:
        return None

    active = [item for item in features if str(item.get("status", "")).lower() in ACTIVE_STATUSES]
    if active:
        return summarize_feature(sorted(active, key=_priority)[0])

    unfinished = [
        item for item in features
        if str(item.get("status", "")).lower() not in COMPLETED_STATUSES
    ]
    if unfinished:
        return summarize_feature(sorted(unfinished, key=_priority)[0])

    blocked = [item for item in features if str(item.get("status", "")).lower() in BLOCKED_STATUSES]
    if blocked:
        return summarize_feature(sorted(blocked, key=_priority)[0])

    return summarize_feature(sorted(features, key=_priority)[0])


def git_output(repo_path: Path, args: list[str]) -> str:
    if not (repo_path / ".git").exists():
        return "not a git worktree"
    result = run_command(["git", *args], cwd=repo_path, timeout=60)
    output = result.stdout.strip() or result.stderr.strip()
    return output or f"git {' '.join(args)} returned {result.returncode}"


def collect_repo_state(target_repo: str, run_static_checks: bool = False) -> RepoStateSnapshot:
    repo_path = resolve_repo(target_repo)
    exists = repo_path.exists()
    blockers: list[str] = []
    if not exists:
        return RepoStateSnapshot(
            repo=target_repo,
            path=str(repo_path),
            exists=False,
            active_feature=None,
            baseline_command=None,
            git_status="repo path missing",
            recent_commits="repo path missing",
            claude_progress_excerpt="",
            feature_list_excerpt="",
            blockers=["target repo path does not exist"],
        )

    feature_list = load_feature_list(repo_path)
    active_feature = select_active_feature(feature_list)
    baseline = "./init.sh" if (repo_path / "init.sh").exists() else None
    if baseline is None:
        blockers.append("target repo has no init.sh baseline")
    if not (repo_path / "feature_list.json").exists():
        blockers.append("target repo has no feature_list.json")
    if not (repo_path / "claude-progress.md").exists():
        blockers.append("target repo has no claude-progress.md")

    static_check = None
    if run_static_checks:
        if baseline:
            static_check = run_command(["./init.sh"], cwd=repo_path, timeout=600)
            if static_check.returncode != 0:
                blockers.append("target repo ./init.sh failed")
        else:
            blockers.append("static checks requested but no init.sh exists")

    return RepoStateSnapshot(
        repo=target_repo,
        path=str(repo_path),
        exists=True,
        active_feature=active_feature,
        baseline_command=baseline,
        git_status=git_output(repo_path, ["status", "--short", "--branch"]),
        recent_commits=git_output(repo_path, ["log", "--oneline", "-5"]),
        claude_progress_excerpt=read_text(repo_path / "claude-progress.md"),
        feature_list_excerpt=read_text(repo_path / "feature_list.json"),
        blockers=blockers,
        static_check=static_check,
    )
