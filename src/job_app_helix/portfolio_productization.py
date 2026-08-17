from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from .portfolio_discovery import build_plan
from .portfolio_models import EvidenceLevel, RepositoryPlan


class DeliveryForm(StrEnum):
    STATIC_SITE = "STATIC_SITE"
    CONTAINER_SERVICE = "CONTAINER_SERVICE"
    SERVICE = "SERVICE"
    CLI_PACKAGE = "CLI_PACKAGE"
    PACKAGE = "PACKAGE"
    MULTI_RUNTIME_TOOL = "MULTI_RUNTIME_TOOL"
    RUNNABLE_TOOL = "RUNNABLE_TOOL"


@dataclass(frozen=True)
class ProductizationTarget:
    repository: str
    wave_id: str
    priority: int
    delivery_form: DeliveryForm
    stacks: tuple[str, ...]
    deployment_signals: tuple[str, ...]
    blockers: tuple[str, ...]
    target_evidence: EvidenceLevel
    next_checkpoint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository": self.repository,
            "wave_id": self.wave_id,
            "priority": self.priority,
            "delivery_form": self.delivery_form.value,
            "stacks": list(self.stacks),
            "deployment_signals": list(self.deployment_signals),
            "blockers": list(self.blockers),
            "target_evidence": self.target_evidence.name,
            "next_checkpoint": self.next_checkpoint,
            "archive_allowed": False,
            "required_outcomes": [
                "preserve prior unique capabilities and useful interfaces",
                "implement the central mechanism through a real execution path",
                "pass deterministic tests and adversarial failure checks",
                "provide a directly usable entrypoint or integration surface",
                "ship in the strongest appropriate delivery form",
                "observe runtime behavior and retain a reproducible receipt",
                "continue measured evolution after the first operable delivery",
            ],
        }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def deployment_signals(path: Path) -> tuple[str, ...]:
    signals: list[str] = []
    markers = {
        "vercel.json": "vercel",
        "netlify.toml": "netlify",
        "fly.toml": "fly",
        "render.yaml": "render",
        "railway.toml": "railway",
        "Dockerfile": "docker",
        "docker-compose.yml": "docker-compose",
        "compose.yml": "docker-compose",
    }
    for marker, signal in markers.items():
        if (path / marker).is_file():
            signals.append(signal)

    package = _read_json(path / "package.json")
    scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
    for script in ("deploy", "start", "serve", "preview", "build"):
        if isinstance(scripts.get(script), str):
            signals.append(f"npm:{script}")
    if isinstance(package.get("bin"), (str, dict)):
        signals.append("node:bin")

    pyproject = _text(path / "pyproject.toml")
    if "[project.scripts]" in pyproject:
        signals.append("python:project-scripts")
    if "[project.entry-points" in pyproject:
        signals.append("python:entry-points")

    workflows = path / ".github" / "workflows"
    if workflows.is_dir():
        for workflow in workflows.iterdir():
            if not workflow.is_file() or workflow.suffix not in {".yml", ".yaml"}:
                continue
            text = _text(workflow).lower()
            if any(term in text for term in ("deploy", "pages", "vercel", "netlify")):
                signals.append(f"workflow:{workflow.name}")

    if (path / "site").is_dir() or (path / "public" / "index.html").is_file():
        signals.append("static-site-source")

    return tuple(dict.fromkeys(signals))


def infer_delivery_form(plan: RepositoryPlan) -> DeliveryForm:
    path = plan.path
    signals = set(deployment_signals(path))
    package = _read_json(path / "package.json")
    scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
    pyproject = _text(path / "pyproject.toml")

    if {"vercel", "netlify"} & signals or "static-site-source" in signals:
        return DeliveryForm.STATIC_SITE
    if "docker" in signals or "docker-compose" in signals:
        return DeliveryForm.CONTAINER_SERVICE
    if any(isinstance(scripts.get(name), str) for name in ("start", "serve")):
        return DeliveryForm.SERVICE
    if isinstance(package.get("bin"), (str, dict)) or "[project.scripts]" in pyproject:
        return DeliveryForm.CLI_PACKAGE
    if len(plan.stacks) > 1:
        return DeliveryForm.MULTI_RUNTIME_TOOL
    if (path / "pyproject.toml").is_file() or (path / "package.json").is_file():
        return DeliveryForm.PACKAGE
    return DeliveryForm.RUNNABLE_TOOL


def _checkpoint(plan: RepositoryPlan, form: DeliveryForm, signals: tuple[str, ...]) -> str:
    if plan.blockers:
        return f"repair execution blocker: {plan.blockers[0]}"
    if plan.target_evidence < EvidenceLevel.TEST:
        return (
            "finish central mechanism and reach positive-count deterministic "
            "test proof"
        )
    if form is DeliveryForm.STATIC_SITE:
        return (
            "build, deploy, smoke-test, and bind the live site receipt to the "
            "exact source head"
        )
    if form is DeliveryForm.CONTAINER_SERVICE:
        return (
            "build the container, run an isolated smoke test, deploy it, and "
            "capture health receipts"
        )
    if form is DeliveryForm.SERVICE:
        return (
            "make the service cold-start cleanly, add health checks, deploy it, "
            "and observe runtime behavior"
        )
    if form is DeliveryForm.CLI_PACKAGE:
        return (
            "install from a clean environment, run an end-to-end command, "
            "package/release it, and bind receipts"
        )
    if form is DeliveryForm.PACKAGE:
        return (
            "make clean installation and public API smoke tests pass, then "
            "publish or integrate the package"
        )
    if form is DeliveryForm.MULTI_RUNTIME_TOOL:
        return (
            "prove each runtime boundary, expose one coherent entrypoint, "
            "package it, and run an end-to-end flow"
        )
    if signals:
        return (
            "execute the strongest existing delivery path and bind runtime "
            "proof to the exact source head"
        )
    return (
        "create a real runnable entrypoint, package the product, then advance "
        "to an appropriate deployment surface"
    )


def compile_productization_targets(
    *,
    workspace: Path,
    inventory_path: Path,
    rollout_path: Path,
    wave_ids: set[str] | None = None,
) -> tuple[ProductizationTarget, ...]:
    plans = build_plan(
        workspace=workspace,
        inventory_path=inventory_path,
        rollout_path=rollout_path,
        wave_ids=wave_ids,
    )
    targets: list[ProductizationTarget] = []
    for plan in plans:
        form = infer_delivery_form(plan)
        signals = deployment_signals(plan.path) if plan.path.is_dir() else ()
        targets.append(
            ProductizationTarget(
                repository=plan.repository,
                wave_id=plan.wave_id,
                priority=plan.priority,
                delivery_form=form,
                stacks=plan.stacks,
                deployment_signals=signals,
                blockers=plan.blockers,
                target_evidence=max(plan.target_evidence, EvidenceLevel.TEST),
                next_checkpoint=_checkpoint(plan, form, signals),
            )
        )
    return tuple(targets)


def productization_payload(targets: tuple[ProductizationTarget, ...]) -> dict[str, Any]:
    forms = {form.value: 0 for form in DeliveryForm}
    for target in targets:
        forms[target.delivery_form.value] += 1
    return {
        "schema": "glaciereq.portfolio-productization.v1",
        "mission": (
            "Rewrite every admitted job-engineering repository into its strongest useful, "
            "functional, operable, and appropriately deployed form while preserving prior gains."
        ),
        "default_action": "PRODUCTIZE",
        "retirement_policy": "OPERATOR_AUTHORIZATION_REQUIRED",
        "targets": [target.to_dict() for target in targets],
        "summary": {
            "repositories": len(targets),
            "blocked": sum(bool(target.blockers) for target in targets),
            "delivery_forms": forms,
        },
    }
