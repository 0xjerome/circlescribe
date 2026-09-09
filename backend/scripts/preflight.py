#!/usr/bin/env python3
"""CircleScribe environment and submission preflight.

This script intentionally does not call AWS. It verifies that the local
runtime/repository are structurally ready and reports whether AWS credentials
are present. Use --require-aws only when the AWS account is active again.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument(
        "--require-aws",
        action="store_true",
        help="Fail if the Bedrock bearer token is not present.",
    )
    args = parser.parse_args()

    backend = Path(__file__).resolve().parents[1]
    root = backend.parent

    checks: list[Check] = []

    checks.append(Check(
        "python",
        sys.version_info >= (3, 10),
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    ))

    required_paths = [
        root / "README.md",
        root / "LICENSE",
        root / "docs" / "CircleScribe_Architecture_Submission.png",
        root / "frontend" / "package.json",
        root / "frontend" / "package-lock.json",
        backend / "pyproject.toml",
        root / "sample_data" / "demo_transcript.txt",
    ]
    missing = [str(path.relative_to(root)) for path in required_paths if not path.exists()]
    checks.append(Check(
        "required_submission_files",
        not missing,
        "present" if not missing else "missing: " + ", ".join(missing),
    ))

    for module in ("fastapi", "pydantic", "boto3", "strands", "numpy"):
        checks.append(Check(
            f"python_module:{module}",
            has_module(module),
            "installed" if has_module(module) else "missing",
        ))

    audio_available = has_module("mlx_whisper")
    checks.append(Check(
        "local_audio_adapter",
        audio_available,
        "mlx-whisper installed" if audio_available else "optional; install backend [audio] extra on Apple Silicon",
        required=False,
    ))

    token_set = bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK"))
    checks.append(Check(
        "bedrock_api_key",
        token_set,
        "present in environment" if token_set else "not set",
        required=args.require_aws,
    ))

    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    checks.append(Check(
        "aws_region",
        bool(region),
        region or "not set (recommended: us-east-1)",
        required=args.require_aws,
    ))

    if args.as_json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        print("CircleScribe preflight")
        print("=" * 72)
        for check in checks:
            status = "PASS" if check.ok else ("FAIL" if check.required else "INFO")
            print(f"{status:4}  {check.name:32}  {check.detail}")

    failures = [check for check in checks if check.required and not check.ok]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
