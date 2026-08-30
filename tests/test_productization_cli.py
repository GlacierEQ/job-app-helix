from __future__ import annotations

from pathlib import Path

from job_app_helix import productization_cli


def test_output_write_failure_returns_program_error(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        productization_cli,
        "compile_productization_targets",
        lambda **_: (),
    )

    def fail_write(*_args, **_kwargs) -> None:
        raise OSError("denied")

    monkeypatch.setattr(productization_cli, "atomic_write_json", fail_write)

    result = productization_cli.main(
        [
            "--workspace",
            str(tmp_path),
            "--output",
            str(tmp_path / "productization.json"),
        ]
    )

    assert result == 2
    assert "productization program error: denied" in capsys.readouterr().err
