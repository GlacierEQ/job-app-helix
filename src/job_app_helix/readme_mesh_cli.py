from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .readme_four_depth import render_five_depth_block
from .readme_mesh import (
    apply_block,
    render_all_blocks,
    render_repository_block,
    write_artifacts,
)
from .readme_mesh_manifest import load_mesh

DEFAULT_MANIFEST = Path("manifests/readme_mesh.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-readme",
        description=(
            "Validate, serialize, and render the evidence-bound README intelligence mesh "
            "and the Recruiter -> Expert -> Genius -> Machine -> Mesh projection."
        ),
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="Validate the mesh contract and graph.")

    build = subparsers.add_parser(
        "build", help="Write Protobuf, ProtoJSON, and textproto artifacts."
    )
    build.add_argument("--output-dir", type=Path, default=Path("artifacts/readme-mesh"))

    render = subparsers.add_parser(
        "render", help="Render one repository's legacy compatibility README block."
    )
    render.add_argument("repository")
    render.add_argument("--readme", type=Path)
    render.add_argument("--output", type=Path)

    five = subparsers.add_parser(
        "render-five-depth",
        aliases=["render-four-depth"],
        help=(
            "Render the Recruiter -> Expert -> Genius -> Machine -> Mesh projection. "
            "The render-four-depth alias remains for compatibility."
        ),
    )
    five.add_argument("repository")
    five.add_argument("--output", type=Path)
    five.add_argument("--license-path", default="LICENSE")
    five.add_argument(
        "--license-name",
        default="GlacierEQ Proprietary Copyright License and Enforcement Notice v1.1",
    )

    render_all = subparsers.add_parser(
        "render-all", help="Render legacy compatibility blocks for every repository."
    )
    render_all.add_argument(
        "--output-dir", type=Path, default=Path("artifacts/readme-mesh/blocks")
    )

    five_all = subparsers.add_parser(
        "render-five-depth-all",
        aliases=["render-four-depth-all"],
        help=(
            "Render five-depth README blocks for every repository in the current mesh. "
            "The render-four-depth-all alias remains for compatibility."
        ),
    )
    five_all.add_argument(
        "--output-dir", type=Path, default=Path("artifacts/readme-five-depth/blocks")
    )

    inventory = subparsers.add_parser("inventory", help="Emit a compact repository/edge inventory.")
    inventory.add_argument("--json", action="store_true")
    return parser


def _emit(rendered: str, output: Path | None) -> None:
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    mesh = load_mesh(args.manifest)

    if args.command == "validate":
        print(
            f"README mesh valid: {len(mesh.repositories)} repositories, "
            f"{len(mesh.edges)} typed edges, schema {mesh.schema_version}"
        )
        return 0

    if args.command == "build":
        artifacts = write_artifacts(mesh, args.output_dir)
        print(
            f"README mesh built: {len(artifacts.binary)} bytes, "
            f"sha256={artifacts.sha256}"
        )
        return 0

    if args.command == "render":
        block = render_repository_block(mesh, args.repository)
        rendered = block
        if args.readme:
            rendered = apply_block(args.readme.read_text(encoding="utf-8"), block)
        _emit(rendered, args.output)
        return 0

    if args.command in {"render-five-depth", "render-four-depth"}:
        rendered = render_five_depth_block(
            mesh,
            args.repository,
            license_path=args.license_path,
            license_name=args.license_name,
        )
        _emit(rendered, args.output)
        return 0

    if args.command == "render-all":
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for repository, block in render_all_blocks(mesh):
            filename = repository.replace("/", "__") + ".md"
            (args.output_dir / filename).write_text(block + "\n", encoding="utf-8")
        print(f"Rendered {len(mesh.repositories)} legacy README blocks to {args.output_dir}")
        return 0

    if args.command in {"render-five-depth-all", "render-four-depth-all"}:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for node in mesh.repositories:
            filename = node.repository.replace("/", "__") + ".md"
            block = render_five_depth_block(mesh, node.repository)
            (args.output_dir / filename).write_text(block, encoding="utf-8")
        print(
            f"Rendered {len(mesh.repositories)} five-depth README blocks to {args.output_dir}"
        )
        return 0

    inventory = {
        "schema_version": mesh.schema_version,
        "apex_repo": mesh.apex_repo,
        "repositories": [node.repository for node in mesh.repositories],
        "edges": [
            {
                "source": edge.source,
                "target": edge.target,
                "relation": edge.relation,
                "value": edge.value,
            }
            for edge in mesh.edges
        ],
    }
    if args.json:
        print(json.dumps(inventory, indent=2))
    else:
        print(f"Repositories: {len(mesh.repositories)}")
        print(f"Edges: {len(mesh.edges)}")
        for repository in inventory["repositories"]:
            print(f"- {repository}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
