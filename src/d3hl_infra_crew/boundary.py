from __future__ import annotations

import re
from dataclasses import dataclass

SUPPORTED_BOUNDARIES = {"plan_only", "live_read_check", "live_apply_gated"}

PLAN_ONLY_BLOCKED_PATTERNS = [
    r"\bterraform\s+login\b",
    r"\bterraform(?:\s+-chdir=\S+)?\s+plan\b",
    r"\bterraform\s+apply\b",
    r"\bterraform\s+destroy\b",
    r"\btofu\s+apply\b",
    r"\btofu\s+destroy\b",
    r"\bqm\s+(create|set|importdisk|template|destroy|start|stop|clone)\b",
    r"\bpvesh\s+(create|set|delete)\b",
    r"\bpodman\s+(login|push)\b",
    r"\bansible-playbook\b.*\b(register|apply|provision|deploy|publish)\b",
    r"\bcloudflare\b[^\n]*(create|update|delete|apply)",
    r"\bsatellite\b[^\n]*(publish|promote|register|delete|sync)",
]

LIVE_READ_CHECK_BLOCKED_PATTERNS = [
    r"\bterraform\s+apply\b",
    r"\bterraform\s+destroy\b",
    r"\btofu\s+apply\b",
    r"\btofu\s+destroy\b",
    r"\bqm\s+(create|set|importdisk|template|destroy|start|stop|clone)\b",
    r"\bpvesh\s+(create|set|delete)\b",
    r"\bpodman\s+push\b",
    r"\bcloudflare\b[^\n]*(create|update|delete|apply)",
    r"\bsatellite\b[^\n]*(publish|promote|register|delete|sync)",
]

# Explicit teardown commands. These stay blocked at every boundary, including the
# most permissive one: the orchestrator may build, but never emits an explicit teardown.
ALWAYS_BLOCKED_TEARDOWN_PATTERNS = [
    r"\bterraform\s+destroy\b",
    r"\btofu\s+destroy\b",
    r"\bqm\s+destroy\b",
    r"\bpvesh\s+delete\b",
    r"\bcloudflare\b[^\n]*delete",
    r"\bsatellite\b[^\n]*delete",
]

# Create/update/apply commands permitted under live_apply_gated, but only on a line
# that carries an explicit operator-approved apply gate marker.
GATED_MUTATION_PATTERNS = [
    r"\bterraform(?:\s+-chdir=\S+)?\s+apply\b",
    r"\btofu\s+apply\b",
    r"\bqm\s+(create|set|importdisk|template|start|stop|clone)\b",
    r"\bpvesh\s+(create|set)\b",
    r"\bpodman\s+push\b",
    r"\bcloudflare\b[^\n]*(create|update|apply)",
    r"\bsatellite\b[^\n]*(publish|promote|register|sync)",
]

PLAINTEXT_SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{20,}",
    r"ghp_[A-Za-z0-9_]{20,}",
    r"xox[baprs]-[A-Za-z0-9-]{20,}",
    r"AKIA[0-9A-Z]{16}",
    r"BEGIN (RSA|OPENSSH|EC) PRIVATE KEY",
    r"(?i)(password|token|secret|credential)\s*[:=]\s*[^\s`'\"]{8,}",
]

ANSIBLE_MUTATION_VERBS = ("apply", "configure", "deploy", "patch", "provision", "publish", "register")


def _command_lines(text: str, command: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if re.search(command, line, flags=re.IGNORECASE)]


def _is_ansible_syntax_check(line: str) -> bool:
    return "--syntax-check" in line


def _is_ansible_check_mode(line: str) -> bool:
    return "--check" in line


def _ansible_line_looks_mutating(line: str) -> bool:
    lowered = line.lower()
    return any(verb in lowered for verb in ANSIBLE_MUTATION_VERBS)


def _is_operator_approved_podman_login(line: str) -> bool:
    lowered = line.lower()
    return "operator-approved" in lowered or "approval gate" in lowered or "approved login gate" in lowered


def _is_operator_approved_mutation(line: str) -> bool:
    lowered = line.lower()
    return (
        "operator-approved" in lowered
        or "approval gate" in lowered
        or ("approved" in lowered and "gate" in lowered)
    )


@dataclass
class BoundaryCheck:
    allowed_boundary: str
    passed: bool
    findings: list[str]

    def to_text(self) -> str:
        status = "passed" if self.passed else "failed"
        lines = [f"Boundary check: {status}", f"Allowed boundary: {self.allowed_boundary}"]
        if self.findings:
            lines.append("Findings:")
            lines.extend(f"- {finding}" for finding in self.findings)
        else:
            lines.append("Findings: none")
        return "\n".join(lines)


def evaluate_boundary(text: str, allowed_boundary: str = "plan_only") -> BoundaryCheck:
    findings: list[str] = []
    lowered_boundary = allowed_boundary.lower().strip()

    if lowered_boundary not in SUPPORTED_BOUNDARIES:
        findings.append(f"unsupported boundary: {allowed_boundary}")

    if lowered_boundary == "plan_only":
        for pattern in PLAN_ONLY_BLOCKED_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
                findings.append(f"live mutation pattern present under plan_only: {pattern}")
        for line in _command_lines(text, r"\bansible-playbook\b"):
            if not _is_ansible_syntax_check(line):
                findings.append("ansible execution present under plan_only: ansible-playbook")

    if lowered_boundary == "live_read_check":
        for pattern in LIVE_READ_CHECK_BLOCKED_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
                findings.append(f"mutation pattern present under live_read_check: {pattern}")
        for line in _command_lines(text, r"\bpodman\s+login\b"):
            if not _is_operator_approved_podman_login(line):
                findings.append("podman login present without an operator-approved login gate")
        for line in _command_lines(text, r"\bansible-playbook\b"):
            if _is_ansible_syntax_check(line):
                continue
            if not _is_ansible_check_mode(line):
                if _ansible_line_looks_mutating(line):
                    findings.append("mutating ansible-playbook present without --check under live_read_check")
                else:
                    findings.append("ansible-playbook present without --check under live_read_check")

    if lowered_boundary == "live_apply_gated":
        for pattern in ALWAYS_BLOCKED_TEARDOWN_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
                findings.append(f"explicit teardown pattern present (blocked at every boundary): {pattern}")
        for pattern in GATED_MUTATION_PATTERNS:
            for line in _command_lines(text, pattern):
                if not _is_operator_approved_mutation(line):
                    findings.append(
                        f"mutation pattern present without an operator-approved apply gate under live_apply_gated: {pattern}"
                    )
        for line in _command_lines(text, r"\bansible-playbook\b"):
            if _is_ansible_syntax_check(line) or _is_ansible_check_mode(line):
                continue
            if not _is_operator_approved_mutation(line):
                findings.append("ansible-playbook present without an operator-approved apply gate under live_apply_gated")

    for pattern in PLAINTEXT_SECRET_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            value = match.group(0)
            if "op://" not in value:
                findings.append(f"possible plaintext secret pattern present: {pattern}")
                break

    return BoundaryCheck(
        allowed_boundary=allowed_boundary,
        passed=not findings,
        findings=findings,
    )
