---
name: "meteor-image"
description: "Use this skill when the user asks to generate, render, draw, create, design, mock up, or edit an image, screenshot, poster, illustration, UI mockup, visual asset, or diagram through the configured meteor041.com-compatible OpenAI proxy. Do not use this skill for text-only writing, coding, or analysis tasks."
---

# Meteor Image Generation Skill

Use this skill to generate images through a third-party OpenAI-compatible proxy.

## Capability Check

Before generating an image, verify that the configured upstream actually supports image generation.

1. Read `OPENAI_API_KEY` and `OPENAI_BASE_URL` from the environment.
   If either value is missing, fall back to `~/.codex/auth.json` and `~/.codex/config.toml`.
2. Run `python scripts/detect_image_capability.py`.
3. Inspect the result:
   - Prefer image model candidates in this order: `gpt-image-2`, `gpt-image-1`.
   - Probe `POST {BASE_URL}/images/generations` first.
   - If that fails, probe `POST {BASE_URL}/responses`.
   - If the configured base URL is only the site root, also retry with `/v1`.
4. Prefer `/images/generations` as the primary route, but do not assume the first successful probe will remain stable during the real generation call.
5. During the real generation call, if the primary route fails with transport instability, Cloudflare signature blocking, or transient `5xx` errors, automatically retry via the alternate route.
6. If neither route succeeds, report that the proxy does not currently expose image generation.

Do not assume image support purely because text completion works.

## Generate An Image

After capability detection succeeds, run:

```bash
python scripts/generate_image.py --prompt "<user prompt>"
```

Pass through optional arguments when the user provides them:

- `--image` (repeatable local image path)
- `--image-url` (repeatable remote image URL)
- `--mask` (PNG mask path for `/images/edits`)
- `--input-fidelity`
- `--size`
- `--quality`
- `--background`
- `--output`

The script now uses a browser-like HTTP profile and disables inherited environment proxy settings to reduce Cloudflare and proxy-related failures. It also prefers inline image bytes such as `b64_json` over downloading a returned image URL.

If the user asks to edit an existing image, the script now supports:

- local files via `--image path/to/file.png`
- remote files via `--image-url https://...`
- masked local edits via `--image ... --mask mask.png`

Route selection rules:

- pure text generation prefers `/images/generations` and falls back to `/responses`
- image edits prefer `/images/edits`
- mixed local `--image` and remote `--image-url` inputs fall back to `/responses`
- `--mask` currently requires local `--image` files and a PNG mask

## Prompt Construction

When turning the user request into an image prompt:

- Preserve the requested subject, style, composition, text, timestamp, and realism level.
- Add concrete physical details when the user asks for realistic or authentic output.
- For UI screenshots, specify device type, app style, time, signal, battery, density, counts, typography, and plausible feed content.
- For posters or news cards, specify composition, headline placement, lighting, camera angle, and editorial style.
- Do not silently remove requested text unless policy requires it.

## Failure Handling

If capability detection or generation fails, clearly report the most likely cause:

- missing image model
- missing `/images/generations`
- missing `/responses`
- authentication failure
- transport instability
- proxy incompatibility

If capability detection succeeds but the real generation call still fails, prefer diagnosing:

- unstable transport or TLS/download failure
- Cloudflare/browser-signature blocking
- transient upstream `502`/`503`/`504` errors
- local environment proxy interference

Do not claim success unless the API actually returns a valid image result.

## Output

If generation succeeds:

1. Save the image locally.
2. Return the saved path.
3. Briefly note which route succeeded:
   - `/images/generations`
   - `/responses`

## Output Rules

- Always save the generated image as a local file (e.g. `output.png`)
- Always return the file path in the response
- Do NOT embed the image inline in the message
- Do NOT rely on UI preview rendering
