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
4. If `/images/generations` works, use it as the primary route.
5. If `/images/generations` fails but `/responses` succeeds, use `/responses`.
6. If neither route succeeds, report that the proxy does not currently expose image generation.

Do not assume image support purely because text completion works.

## Generate An Image

After capability detection succeeds, run:

```bash
python scripts/generate_image.py --prompt "<user prompt>"
```

Pass through optional arguments when the user provides them:

- `--size`
- `--quality`
- `--background`
- `--output`

If the user asks to edit an existing image, first confirm that the upstream proxy supports image editing. If it does not, state that only image generation is currently available.

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
- proxy incompatibility

Do not claim success unless the API actually returns a valid image result.

## Output

If generation succeeds:

1. Save the image locally.
2. Return the saved path.
3. Briefly note which route succeeded:
   - `/images/generations`
   - `/responses`
