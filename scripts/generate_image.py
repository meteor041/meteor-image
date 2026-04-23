from __future__ import annotations

import argparse
import json
import sys

from image_proxy import generate_image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an image through an OpenAI-compatible proxy."
    )
    parser.add_argument("--prompt", required=True, help="Prompt to send to the upstream image API")
    parser.add_argument(
        "--image",
        action="append",
        default=[],
        help="Path to a local input image. Repeat to provide multiple images.",
    )
    parser.add_argument(
        "--image-url",
        action="append",
        default=[],
        help="URL to an input image. Repeat to provide multiple images.",
    )
    parser.add_argument("--mask", help="Optional PNG mask path for /images/edits requests")
    parser.add_argument(
        "--input-fidelity",
        choices=("low", "high"),
        help="Optional fidelity hint for image-edit requests",
    )
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--quality", default="high")
    parser.add_argument("--background")
    parser.add_argument("--output")
    parser.add_argument("--base-url", help="Override OPENAI_BASE_URL")
    parser.add_argument("--api-key", help="Override OPENAI_API_KEY")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = generate_image(
            prompt=args.prompt,
            image_paths=args.image,
            image_urls=args.image_url,
            mask=args.mask,
            input_fidelity=args.input_fidelity,
            output=args.output,
            base_url=args.base_url,
            api_key=args.api_key,
            size=args.size,
            quality=args.quality,
            background=args.background,
        )
    except Exception as error:
        payload = {
            "saved_path": None,
            "route": None,
            "error": str(error),
        }
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 1

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
