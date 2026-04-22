# meteor-image

[English](./README.md) | [简体中文](./README_cn.md)

`meteor-image` is a Codex skill for generating images through the `meteor041.com` OpenAI-compatible proxy.

Works seamlessly with OpenAI-compatible proxies (like meteor041.com), enabling image generation in Codex with the same proxy settings you already use.

Unlike the built-in `imagegen` skill, this skill automatically reuses your existing Codex proxy configuration. 

- `~/.codex/config.toml`
- `~/.codex/auth.json`

If your Codex is already set up to use meteor041.com, image generation will work out of the box — no additional setup required.

That means if Codex is already configured to use the `meteor041.com` proxy, this skill can use the same settings without requiring you to manually pass a separate base URL or API key every time.

## What It Does

- Detect whether the configured upstream supports image generation
- Prefer `/images/generations`
- Fall back to `/responses` if needed
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

If you have the Codex skill installer scripts available, install from GitHub with:

```bash
curl -sL https://meteor041.com/install-meteor-image.sh | bash
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

## Configuration

Priority order:

1. `OPENAI_BASE_URL` and `OPENAI_API_KEY` from environment variables
2. `~/.codex/config.toml` and `~/.codex/auth.json`

The current implementation expects a Codex configuration shaped like:

```toml
[model_providers.OpenAI]
base_url = "https://meteor041.com"
```

And an auth file like:

```json
{
  "OPENAI_API_KEY": "..."
}
```

## Why Not Use The Built-In `imagegen` Skill?

The built-in `imagegen` skill is aimed at Codex's default built-in image generation flow. This custom skill exists for cases where you specifically want to route image generation through a third-party OpenAI-compatible proxy and reuse the local Codex proxy configuration already on disk.

## Notes

- The proxy currently works with `/images/generations`
- `/responses` may not be available or stable depending on the upstream
- The skill is intentionally proxy-specific rather than a generic OpenAI image wrapper
