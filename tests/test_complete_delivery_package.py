from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_complete_delivery_package.py"
SOURCE_COMMIT = "c" * 40


def _load_module() -> ModuleType:
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location(
        "build_complete_delivery_package",
        SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def test_complete_delivery_package_includes_census_layers(tmp_path: Path) -> None:
    module = _load_module()
    original_copy_map = dict(module.base.COPY_MAP)
    original_required = set(module.base.BASE_REQUIRED_PACKAGE_PATHS)

    result = module.build_complete_package(
        tmp_path / "output",
        source_commit=SOURCE_COMMIT,
    )

    package = result.package_dir
    assert (
        package
        / "04_TECHNICAL_DILIGENCE"
        / "PORTFOLIO_EXPANSION_MAP.md"
    ).is_file()
    assert (
        package
        / "05_MACHINE_CONTRACTS"
        / "owned_library_census.json"
    ).is_file()
    assert (package / "PORTFOLIO_EXPANSION_MAP.md").is_file()
    assert (package / "owned_library_census.json").is_file()
    assert result.zip_path.is_file()

    module.base.verify_package(package)
    assert original_copy_map == module.base.COPY_MAP
    assert original_required == module.base.BASE_REQUIRED_PACKAGE_PATHS


def test_base_package_remains_base_after_complete_build(tmp_path: Path) -> None:
    module = _load_module()

    module.build_complete_package(
        tmp_path / "complete",
        source_commit=SOURCE_COMMIT,
    )
    base_result = module.base.build_package(
        tmp_path / "base",
        source_commit=SOURCE_COMMIT,
    )

    assert not (base_result.package_dir / "owned_library_census.json").exists()
    assert not (base_result.package_dir / "PORTFOLIO_EXPANSION_MAP.md").exists()
    module.base.verify_package(base_result.package_dir)
