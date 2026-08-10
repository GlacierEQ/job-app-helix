from __future__ import annotations

import math

import pytest

from job_app_helix.scaffold_runtime import (
    AuthorityClaims,
    ContractError,
    canonical_json,
    digest,
    sanitized_environment,
    validate_budget,
)


def test_canonical_json_is_order_independent() -> None:
    assert digest({"b": 2, "a": 1}) == digest({"a": 1, "b": 2})
    expected = '{"a":true,"b":[2,1]}'
    assert canonical_json({"b": [2, 1], "a": True}) == expected


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_values_fail_closed(value: float) -> None:
    with pytest.raises(ContractError):
        canonical_json({"value": value})
    with pytest.raises(ContractError):
        validate_budget(value, maximum=10.0)


def test_unsupported_types_are_rejected_not_stringified() -> None:
    with pytest.raises(ContractError):
        canonical_json({"value": object()})


def test_budget_has_explicit_upper_bound() -> None:
    assert validate_budget(10.0, maximum=10.0) == 10.0
    with pytest.raises(ContractError, match="exceeds"):
        validate_budget(10.01, maximum=10.0)


def test_authority_enforces_scope_issuer_and_expiry() -> None:
    claims = AuthorityClaims(
        grant_id="g1",
        issuer="external-promotion-authority",
        subject_id="leaf-1",
        scopes=("promote",),
        issued_at=100.0,
        not_after=200.0,
    )
    claims.validate(
        now=150.0,
        required_scope="promote",
        expected_issuer="external-promotion-authority",
    )
    with pytest.raises(ContractError, match="expired"):
        claims.validate(
            now=201.0,
            required_scope="promote",
            expected_issuer="external-promotion-authority",
        )
    with pytest.raises(ContractError, match="scope"):
        claims.validate(
            now=150.0,
            required_scope="delete",
            expected_issuer="external-promotion-authority",
        )


def test_environment_receipt_contains_no_local_paths() -> None:
    env = sanitized_environment(runner="ci")
    blob = str(env)
    assert "PYTHONPATH" not in blob
    assert "/Users/" not in blob
    assert "\\Users\\" not in blob
