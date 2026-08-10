from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


class ContractError(ValueError):
    """Raised when an input cannot participate in a deterministic proof contract."""


def _normalize(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ContractError("non-finite numbers are not canonical")
        return value
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ContractError("canonical object keys must be strings")
        return {key: _normalize(value[key]) for key in sorted(value)}
    raise ContractError(f"unsupported canonical type: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        _normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def validate_budget(value: float, *, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ContractError("budget must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ContractError("budget must be finite")
    if value <= 0:
        raise ContractError("budget must be positive")
    if not math.isfinite(maximum) or maximum <= 0:
        raise ContractError("maximum budget contract is invalid")
    if value > maximum:
        raise ContractError("budget exceeds maximum")
    return value


@dataclass(frozen=True)
class AuthorityClaims:
    grant_id: str
    issuer: str
    subject_id: str
    scopes: tuple[str, ...]
    issued_at: float
    not_after: float

    def validate(
        self,
        *,
        now: float,
        required_scope: str,
        expected_issuer: str,
    ) -> None:
        if not self.grant_id.strip():
            raise ContractError("grant_id missing")
        if self.issuer != expected_issuer:
            raise ContractError("authority issuer mismatch")
        if not self.subject_id.strip():
            raise ContractError("authority subject missing")
        if required_scope not in self.scopes:
            raise ContractError("authority scope missing")
        times = (
            ("issued_at", self.issued_at),
            ("not_after", self.not_after),
            ("now", now),
        )
        for label, value in times:
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ContractError(f"{label} must be finite")
        if self.not_after <= self.issued_at:
            raise ContractError("authority lifetime invalid")
        if now < self.issued_at:
            raise ContractError("authority not active")
        if now > self.not_after:
            raise ContractError("authority expired")


def sanitized_environment(*, runner: str) -> dict[str, str]:
    """Portable proof metadata with no usernames, home paths, or PYTHONPATH leakage."""
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": sys.platform,
        "machine": platform.machine() or "unknown",
        "runner": runner,
    }
