#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: enforce_federation.py <metadata.json>")
        sys.exit(1)
    metadata_path = Path(sys.argv[1])
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metrics = metadata.get("metrics", {})
    bias = metrics.get("bias_score", metadata.get("bias_score"))
    status = "OK" if bias is None or bias <= 0.1 else "WARN"
    print(json.dumps({"adapter": metadata.get("name"), "version": metadata.get("version"), "bias_score": bias, "status": status}))


if __name__ == "__main__":
    main()
