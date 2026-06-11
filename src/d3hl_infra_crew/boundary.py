from __future__ import annotations

import re
from dataclasses import dataclass

LIVE_MUTATION_PATTERNS = [
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

PLAINTEXT_SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{20,}",
    r"ghp_[A-Za-z0-9_]{20,}",
    r"xox[baprs]-[A-Za-z0-9-]{20,}",
    r"AKIA[0-9A-Z]{16}",
    r"BEGIN (RSA|OPENSSH|EC) PRIVATE KEY",
    r"(?i)(password|token|secret|credential)\s*[:=]\s*[^\s`'\"]{8,}",
]


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

    if lowered_boundary == "plan_only":
        for pattern in LIVE_MUTATION_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
                findings.append(f"live mutation pattern present under plan_only: {pattern}")

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
