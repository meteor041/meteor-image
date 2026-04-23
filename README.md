# meteor-image

[English](./README.md) | [简体中文](./README_cn.md)

`meteor-image` is a Codex skill for generating images through OpenAI-compatible proxies built on the `sub2api` relay project.

It works seamlessly with `sub2api`-based deployments such as meteor041.com, enabling image generation in Codex with the same proxy settings you already use.

Unlike the built-in `imagegen` skill, this skill automatically reuses your existing Codex proxy configuration. 

- `~/.codex/config.toml`
- `~/.codex/auth.json`

If your Codex is already set up to use a `sub2api`-based deployment such as meteor041.com, image generation will work out of the box with no additional setup.

That means if Codex is already configured to use a compatible `sub2api` endpoint, this skill can reuse the same settings without requiring you to manually pass a separate base URL or API key every time.

## What It Does

- Detect whether the configured upstream supports image generation
- Prefer `/images/generations`
- Fall back to `/responses` if needed
- Accept local input images, image URLs, and PNG masks for edit flows
- Retry root base URLs with `/v1`
- Work around Cloudflare/WAF blocks that reject Python `urllib` fingerprints by falling back to `curl`

## Skill Layout

```text
meteor-image/
├─ SKILL.md
├─ agents/
│  └─ openai.yaml
└─ scripts/
   ├─ detect_image_capability.py
   ├─ generate_image.py
   └─ image_proxy.py
```

## Install

Install via the GitHub-hosted script:

```bash
curl -fsSL https://raw.githubusercontent.com/meteor041/meteor-image/main/install-meteor-image.sh | bash
```

On Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/meteor041/meteor-image/main/install-meteor-image.ps1 | iex
```

Or install manually by copying the `meteor-image` directory into:

```text
~/.codex/skills/
```

After installing, restart Codex so the new skill is discovered.

## Usage

Example prompt:

```text
Use $meteor-image to create a realistic WeChat screenshot mockup.
```

Capability detection:

```bash
python meteor-image/scripts/detect_image_capability.py
```

Generate an image:

```bash
python meteor-image/scripts/generate_image.py --prompt "A realistic phone screenshot mockup"
```

Edit with a local reference image:

```bash
python meteor-image/scripts/generate_image.py --prompt "Turn this into a watercolor poster" --image ./input.png
```

Edit with a mask:

```bash
python meteor-image/scripts/generate_image.py --prompt "Replace the background with a sunset sky" --image ./input.png --mask ./mask.png
```

Edit with a remote image URL:

```bash
python meteor-image/scripts/generate_image.py --prompt "Restyle this as a cinematic product shot" --image-url "https://example.com/input.png"
```

Notes:

- Repeat `--image` or `--image-url` to provide multiple references
- `--mask` currently requires local `--image` inputs and must be a PNG
- Mixed local `--image` and remote `--image-url` inputs automatically use `/responses`
- Optional tuning flags include `--input-fidelity`, `--size`, `--quality`, `--background`, and `--output`

## Configuration

Priority order:

1. `OPENAI_BASE_URL` and `OPENAI_API_KEY` from environment variables
2. `~/.codex/config.toml` and `~/.codex/auth.json`

The current implementation expects a Codex configuration shaped like:

```toml
[model_providers.OpenAI]
base_url = "https://meteor041.com"
```

Here `https://meteor041.com` is only an example deployment URL. Any compatible `sub2api` deployment should work.

And an auth file like:

```json
{
  "OPENAI_API_KEY": "..."
}
```

## Why Not Use The Built-In `imagegen` Skill?

The built-in `imagegen` skill is aimed at Codex's default built-in image generation flow. This custom skill exists for cases where you specifically want to route image generation through a `sub2api`-based OpenAI-compatible relay and reuse the local Codex proxy configuration already on disk.

## Notes

- This skill targets `sub2api`-based OpenAI-compatible relay deployments
- meteor041.com is one deployed site, not the protocol or project itself
- Compatible deployments currently work with `/images/generations`
- `/responses` may not be available or stable depending on the upstream
- The skill is intentionally proxy-specific rather than a generic OpenAI image wrapper
