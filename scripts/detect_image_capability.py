from __future__ import annotations

import argparse
import json
import sys

from image_proxy import detect_capability


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect image-generation support for an OpenAI-compatible proxy."
    )
    parser.add_argument("--base-url", help="Override OPENAI_BASE_URL")
    parser.add_argument("--api-key", help="Override OPENAI_API_KEY")
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--quality", default="low")
    parser.add_argument("--background")
    parser.add_argument("--prompt", default=None, help="Optional probe prompt")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    kwargs = {
        "base_url": args.base_url,
        "api_key": args.api_key,
        "size": args.size,
        "quality": args.quality,
        "background": args.background,
    }
    if args.prompt:
        kwargs["prompt"] = args.prompt

    report = detect_capability(**kwargs)
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report.get("supported") else 1


if __name__ == "__main__":
    raise SystemExit(main())
