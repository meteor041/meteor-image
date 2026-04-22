# meteor-image

[English](./README.md) | [简体中文](./README_cn.md)

`meteor-image` 是一个 Codex 技能，用于通过基于 `sub2api` 中转站项目的 OpenAI-compatible 代理生成图片。

它可以无缝配合基于 `sub2api` 的部署站点使用，例如 meteor041.com，并直接复用你当前在 Codex 中已经配置好的代理设置来完成图片生成。

不同于内置的 `imagegen` 技能，这个技能会自动复用你现有的 Codex 代理配置。

- `~/.codex/config.toml`
- `~/.codex/auth.json`

如果你的 Codex 已经配置为使用基于 `sub2api` 的部署站点，例如 meteor041.com，那么图片生成可以直接开箱即用，不需要额外配置。

这意味着如果 Codex 已经配置好了兼容的 `sub2api` 端点，这个技能可以直接复用同一套设置，而不需要你每次手动传入单独的 base URL 或 API key。

## 功能

- 检测当前配置的上游是否支持图片生成
- 优先使用 `/images/generations`
- 必要时回退到 `/responses`
- 当 base URL 指向根路径时，自动尝试补上 `/v1`
- 当 Python `urllib` 指纹被 Cloudflare/WAF 拦截时，回退到 `curl`

## 技能结构

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

## 安装

通过 GitHub 托管的安装脚本执行：

```bash
curl -fsSL https://raw.githubusercontent.com/meteor041/meteor-image/main/install-meteor-image.sh | bash
```

Windows PowerShell 可执行：

```powershell
irm https://raw.githubusercontent.com/meteor041/meteor-image/main/install-meteor-image.ps1 | iex
```

或者手动将 `meteor-image` 目录复制到：

```text
~/.codex/skills/
```

安装完成后，重启 Codex 以便发现新技能。

## 使用方法

示例提示词：

```text
Use $meteor-image to create a realistic WeChat screenshot mockup.
```

能力检测：

```bash
python meteor-image/scripts/detect_image_capability.py
```

生成图片：

```bash
python meteor-image/scripts/generate_image.py --prompt "A realistic phone screenshot mockup"
```

## 配置

优先级顺序：

1. 环境变量中的 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY`
2. `~/.codex/config.toml` 和 `~/.codex/auth.json`

当前实现预期的 Codex 配置格式如下：

```toml
[model_providers.OpenAI]
base_url = "https://meteor041.com"
```

这里的 `https://meteor041.com` 只是一个部署示例地址。任何兼容的 `sub2api` 部署都应当可以工作。

认证文件示例：

```json
{
  "OPENAI_API_KEY": "..."
}
```

## 为什么不直接使用内置 `imagegen` 技能？

内置的 `imagegen` 技能主要面向 Codex 默认内建的图片生成流程。这个自定义技能用于你明确希望通过基于 `sub2api` 的 OpenAI-compatible 中转站来路由图片生成，并复用本地磁盘上已有 Codex 代理配置的场景。

## 说明

- 这个技能面向基于 `sub2api` 的 OpenAI-compatible 中转站部署
- meteor041.com 是其中一个已部署站点，不是协议本身，也不是项目名
- 兼容部署当前可用于 `/images/generations`
- `/responses` 是否可用或是否稳定，取决于具体上游实现
- 这个技能有意针对代理场景设计，而不是做成一个通用的 OpenAI 图片封装器
