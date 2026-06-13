"""Focused plaintext-secret scan used to enforce the op://d3HLPRV/... secrets rule.

This is intentionally narrow: it is the one retained content check after the boundary
system was removed. It flags plaintext secret *values* while allowing secret
*references* (op:// paths, Terraform/Ansible variable references, Jinja expressions).
"""

from __future__ import annotations

import re

# High-confidence secret material. These shapes are real credentials, not references,
# so they are flagged wherever they appear.
HIGH_CONFIDENCE_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{20,}",
    r"ghp_[A-Za-z0-9_]{20,}",
    r"xox[baprs]-[A-Za-z0-9-]{20,}",
    r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----",
]

# key = value / key: value assignments for secret-ish keys. The key may be a compound
# identifier that contains a secret word (e.g. client_secret, db_password, api_token).
_ASSIGNMENT = re.compile(
    r"(?i)(?P<key>[\w.\-]*(?:password|passwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|credential)[\w]*)"
    r"\s*[:=]\s*"
    r"(?P<val>\"[^\"]*\"|'[^']*'|\S+)"
)

# Value prefixes that are references, not literal secrets (allowed).
_REFERENCE_PREFIXES = (
    "op://",
    "var.",
    "local.",
    "data.",
    "module.",
    "each.",
    "self.",
    "${",
    "{{",
    "$(",
    "env.",
)


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _value_is_reference(value: str) -> bool:
    cleaned = _strip_quotes(value).strip()
    if not cleaned:
        return True  # empty default, not a secret
    if "op://" in cleaned:
        return True
    return cleaned.startswith(_REFERENCE_PREFIXES)


def find_plaintext_secrets(text: str) -> list[str]:
    """Return human-readable findings for plaintext secrets in ``text``.

    An empty list means the text is clean. ``op://d3HLPRV/...`` references and
    Terraform/Ansible/Jinja variable references are allowed and never flagged.
    """
    findings: list[str] = []

    for pattern in HIGH_CONFIDENCE_PATTERNS:
        if re.search(pattern, text):
            findings.append(f"high-confidence secret shape: {pattern}")

    for match in _ASSIGNMENT.finditer(text):
        if not _value_is_reference(match.group("val")):
            findings.append(f"plaintext value assigned to `{match.group('key')}`; use a op://d3HLPRV/... reference")

    return findings
