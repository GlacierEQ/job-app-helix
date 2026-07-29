from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

from job_app_helix import readme_mesh_pb2

ROOT = Path(__file__).resolve().parents[1]
PROTO = ROOT / "proto" / "readme_mesh.proto"


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "grpc_tools.protoc",
                f"--proto_path={PROTO.parent}",
                f"--python_out={output}",
                str(PROTO),
            ],
            check=True,
        )
        generated_path = output / "readme_mesh_pb2.py"
        spec = importlib.util.spec_from_file_location(
            "generated_readme_mesh_pb2", generated_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("unable to load generated Protobuf module")
        generated = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generated)
        if generated.DESCRIPTOR.serialized_pb != readme_mesh_pb2.DESCRIPTOR.serialized_pb:
            raise SystemExit(
                "committed readme_mesh_pb2.py does not match "
                "proto/readme_mesh.proto"
            )
    print("Protobuf descriptor matches committed Python binding")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
