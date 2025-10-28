#!/usr/bin/env python3
import json
import sys


def main() -> None:
    payload = sys.argv[1] if len(sys.argv) > 1 else "{}"
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        data = {"raw": payload}
    name = data.get("name", "unknown")
    version = data.get("version", "?")
    print(f"[notify_slack] Adapter {name}:{version} ready")


if __name__ == "__main__":
    main()
