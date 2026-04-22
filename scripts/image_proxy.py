from __future__ import annotations

import base64
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any

import requests

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

PREFERRED_IMAGE_MODELS = ("gpt-image-2", "gpt-image-1")
FALLBACK_RESPONSE_MODELS = (
    "gpt-5.4",
    "gpt-5.2",
    "gpt-5.1",
    "gpt-5",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4o",
    "gpt-4o-mini",
)
DEFAULT_TEST_PROMPT = "Create a small flat blue square icon on a white background."
FORCE_CURL_TRANSPORTS: set[str] = set()
DEFAULT_HTTP_TIMEOUT = 240
DEFAULT_REQUEST_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    "Origin": "https://meteor041.com",
    "Referer": "https://meteor041.com/",
}


class ConfigError(RuntimeError):
    pass


@dataclass
class ApiError(RuntimeError):
    path: str
    status_code: int | None
    message: str
    raw_body: str | None = None

    def __str__(self) -> str:
        if self.status_code is None:
            return f"{self.path}: {self.message}"
        return f"{self.path}: HTTP {self.status_code} - {self.message}"


def load_config(
    base_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, str]:
    resolved_base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "").strip()
    resolved_api_key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
    base_url_source = "environment" if resolved_base_url else ""
    api_key_source = "environment" if resolved_api_key else ""

    if not resolved_base_url or not resolved_api_key:
        codex_home = get_codex_home()
        config_path = codex_home / "config.toml"
        auth_path = codex_home / "auth.json"
        config_data = read_toml_file(config_path) if config_path.exists() else {}
        auth_data = read_json_file(auth_path) if auth_path.exists() else {}

        if not resolved_base_url:
            config_base_url = extract_base_url_from_codex_config(config_data)
            if config_base_url:
                resolved_base_url = config_base_url
                base_url_source = str(config_path)

        if not resolved_api_key:
            config_api_key = extract_api_key_from_auth(auth_data)
            if config_api_key:
                resolved_api_key = config_api_key
                api_key_source = str(auth_path)

    if not resolved_base_url:
        raise ConfigError("Missing OPENAI_BASE_URL")
    if not resolved_api_key:
        raise ConfigError("Missing OPENAI_API_KEY")
    return {
        "base_url": resolved_base_url.rstrip("/"),
        "api_key": resolved_api_key,
        "source": describe_config_source(base_url_source, api_key_source),
    }


def get_codex_home() -> pathlib.Path:
    configured = (os.getenv("CODEX_HOME") or "").strip()
    if configured:
        return pathlib.Path(configured).expanduser()
    return pathlib.Path.home() / ".codex"


def read_toml_file(path: pathlib.Path) -> dict[str, Any]:
    if tomllib is None:
        raise ConfigError("tomllib is unavailable, so config.toml cannot be read")
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"Failed to read {path}: {error}") from error
    except Exception as error:
        raise ConfigError(f"Failed to parse {path}: {error}") from error


def read_json_file(path: pathlib.Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"Failed to read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ConfigError(f"Failed to parse {path}: {error}") from error
    if isinstance(payload, dict):
        return payload
    raise ConfigError(f"{path} did not contain a JSON object")


def extract_base_url_from_codex_config(config: dict[str, Any]) -> str:
    provider_name = config.get("model_provider")
    providers = config.get("model_providers")
    if isinstance(provider_name, str) and isinstance(providers, dict):
        provider = providers.get(provider_name)
        if isinstance(provider, dict):
            base_url = provider.get("base_url")
            if isinstance(base_url, str) and base_url.strip():
                return base_url.strip()

    if isinstance(providers, dict):
        for provider in providers.values():
            if not isinstance(provider, dict):
                continue
            base_url = provider.get("base_url")
            if isinstance(base_url, str) and base_url.strip():
                return base_url.strip()

    return ""


def extract_api_key_from_auth(auth_payload: dict[str, Any]) -> str:
    value = auth_payload.get("OPENAI_API_KEY")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return ""


def describe_config_source(base_url_source: str, api_key_source: str) -> str:
    if base_url_source == "environment" and api_key_source == "environment":
        return "environment"
    if base_url_source and api_key_source and base_url_source == api_key_source:
        return base_url_source
    if base_url_source and api_key_source:
        return f"base_url={base_url_source}; api_key={api_key_source}"
    if base_url_source:
        return f"base_url={base_url_source}"
    if api_key_source:
        return f"api_key={api_key_source}"
    return "unknown"


def request_json(
    *,
    base_url: str,
    api_key: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> Any:
    transport_key = get_transport_key(base_url)
    if transport_key in FORCE_CURL_TRANSPORTS:
        return request_json_via_curl(
            base_url=base_url,
            api_key=api_key,
            method=method,
            path=path,
            payload=payload,
            timeout=timeout,
        )

    try:
        return request_json_via_requests(
            base_url=base_url,
            api_key=api_key,
            method=method,
            path=path,
            payload=payload,
            timeout=timeout,
        )
    except ApiError as error:
        if not should_retry_with_curl(error):
            raise
        FORCE_CURL_TRANSPORTS.add(transport_key)
        return request_json_via_curl(
            base_url=base_url,
            api_key=api_key,
            method=method,
            path=path,
            payload=payload,
            timeout=timeout,
        )


def build_request_headers(api_key: str, *, include_json_content_type: bool = True) -> dict[str, str]:
    headers = dict(DEFAULT_REQUEST_HEADERS)
    headers["Authorization"] = f"Bearer {api_key}"
    if not include_json_content_type:
        headers.pop("Content-Type", None)
    return headers


def build_requests_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


def request_json_via_requests(
    *,
    base_url: str,
    api_key: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> Any:
    headers = build_request_headers(api_key, include_json_content_type=payload is not None)
    session = build_requests_session()

    try:
        response = session.request(
            method=method.upper(),
            url=f"{base_url}{path}",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as error:
        message = str(error)
        response = getattr(error, "response", None)
        if response is not None:
            body = response.text
            raise ApiError(
                path=path,
                status_code=response.status_code,
                message=extract_error_message(body),
                raw_body=body,
            ) from error
        raise ApiError(
            path=path,
            status_code=None,
            message=message,
        ) from error

    raw = response.content
    if response.status_code >= 400:
        body = response.text
        raise ApiError(
            path=path,
            status_code=response.status_code,
            message=extract_error_message(body),
            raw_body=body,
        )

    if not raw:
        return {}

    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise ApiError(
            path=path,
            status_code=None,
            message="Response body was not valid JSON",
            raw_body=raw.decode("utf-8", errors="replace"),
        ) from error


def request_json_via_curl(
    *,
    base_url: str,
    api_key: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> Any:
    curl_bin = shutil.which("curl.exe") or shutil.which("curl")
    if not curl_bin:
        raise ApiError(path=path, status_code=None, message="curl is not available")

    headers = [f"{key}: {value}" for key, value in build_request_headers(api_key).items()]
    command = [
        curl_bin,
        "-sS",
        "-L",
        "-X",
        method.upper(),
        f"{base_url}{path}",
    ]

    with tempfile.TemporaryDirectory(prefix="metero041-curl-") as temp_dir:
        header_path = pathlib.Path(temp_dir) / "headers.txt"
        body_path = pathlib.Path(temp_dir) / "body.bin"
        command.extend(["-D", str(header_path), "-o", str(body_path), "--max-time", str(timeout)])

        if payload is not None:
            command.extend(["--data-binary", json.dumps(payload)])

        for header in headers:
            command.extend(["-H", header])

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or "curl request failed"
            raise ApiError(path=path, status_code=None, message=stderr)

        status_code = parse_curl_status_code(header_path.read_text(encoding="utf-8", errors="replace"))
        raw = body_path.read_bytes()

    if status_code >= 400:
        body_text = raw.decode("utf-8", errors="replace")
        raise ApiError(
            path=path,
            status_code=status_code,
            message=extract_error_message(body_text),
            raw_body=body_text,
        )

    if not raw:
        return {}

    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise ApiError(
            path=path,
            status_code=status_code,
            message="Response body was not valid JSON",
            raw_body=raw.decode("utf-8", errors="replace"),
        ) from error


def parse_curl_status_code(header_text: str) -> int:
    statuses: list[int] = []
    for line in header_text.splitlines():
        if not line.startswith("HTTP/"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            statuses.append(int(parts[1]))
    if not statuses:
        raise ApiError(path="", status_code=None, message="curl response did not include an HTTP status")
    return statuses[-1]


def should_retry_with_curl(error: ApiError) -> bool:
    curl_bin = shutil.which("curl.exe") or shutil.which("curl")
    if not curl_bin:
        return False
    error_text = " ".join(
        part for part in (error.message, error.raw_body or "") if isinstance(part, str)
    ).lower()
    return (
        error.status_code == 403
        and ("cloudflare" in error_text or "browser's signature" in error_text or "error 1010" in error_text)
    )


def get_transport_key(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    return f"{parsed.scheme}://{parsed.netloc}".lower()


def extract_error_message(body: str) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body.strip() or "Unknown error"

    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()

    message = payload.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()

    return body.strip() or "Unknown error"


def list_models(base_url: str, api_key: str) -> list[str]:
    payload = request_json(base_url=base_url, api_key=api_key, method="GET", path="/models")
    items = payload.get("data", [])
    models: list[str] = []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                model_id = item.get("id")
                if isinstance(model_id, str) and model_id.strip():
                    models.append(model_id.strip())
    return models


def pick_image_model(models: list[str]) -> str | None:
    preferred = pick_model(models, PREFERRED_IMAGE_MODELS)
    if preferred:
        return preferred
    image_like = [model for model in models if model.startswith("gpt-image-")]
    return image_like[0] if image_like else None


def pick_responses_model(models: list[str], fallback_model: str) -> str:
    candidate = pick_model(models, FALLBACK_RESPONSE_MODELS)
    return candidate or fallback_model


def pick_model(models: list[str], aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        for model in models:
            if model == alias or model.startswith(f"{alias}-"):
                return model
    return None


def build_base_url_candidates(base_url: str) -> list[str]:
    normalized = base_url.rstrip("/")
    candidates = [normalized]
    parsed = urllib.parse.urlparse(normalized)
    path = parsed.path.rstrip("/")
    if path in {"", "/"}:
        candidates.append(f"{normalized}/v1")

    unique_candidates: list[str] = []
    for candidate in candidates:
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)
    return unique_candidates


def resolve_base_url_and_models(base_url: str, api_key: str) -> tuple[str, list[str], list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    last_error: Exception | None = None

    for candidate in build_base_url_candidates(base_url):
        try:
            models = list_models(candidate, api_key)
            attempts.append({"base_url": candidate, "ok": True})
            return candidate, models, attempts
        except Exception as error:
            last_error = error
            attempts.append(
                {
                    "base_url": candidate,
                    "ok": False,
                    "error": str(error),
                }
            )

    if last_error is None:
        raise ConfigError("Could not resolve a usable base URL")
    raise last_error


def build_images_payload(
    *,
    model: str,
    prompt: str,
    size: str | None,
    quality: str | None,
    background: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "output_format": "png",
    }
    if size:
        payload["size"] = size
    if quality:
        payload["quality"] = quality
    if background:
        payload["background"] = background
    return payload


def build_responses_payload(
    *,
    model: str,
    prompt: str,
    size: str | None,
    quality: str | None,
    background: str | None,
) -> dict[str, Any]:
    tool: dict[str, Any] = {
        "type": "image_generation",
        "format": "png",
    }
    if size:
        tool["size"] = size
    if quality:
        tool["quality"] = quality
    if background:
        tool["background"] = background

    return {
        "model": model,
        "input": prompt,
        "tools": [tool],
    }


def call_images_generation(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    size: str | None,
    quality: str | None,
    background: str | None,
) -> tuple[bytes, dict[str, Any]]:
    payload = build_images_payload(
        model=model,
        prompt=prompt,
        size=size,
        quality=quality,
        background=background,
    )
    response = request_json(
        base_url=base_url,
        api_key=api_key,
        method="POST",
        path="/images/generations",
        payload=payload,
    )
    return extract_image_bytes(response), response


def call_responses_generation(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    size: str | None,
    quality: str | None,
    background: str | None,
) -> tuple[bytes, dict[str, Any]]:
    payload = build_responses_payload(
        model=model,
        prompt=prompt,
        size=size,
        quality=quality,
        background=background,
    )
    response = request_json(
        base_url=base_url,
        api_key=api_key,
        method="POST",
        path="/responses",
        payload=payload,
    )
    return extract_response_image_bytes(response), response


def extract_image_bytes(response: dict[str, Any]) -> bytes:
    items = response.get("data", [])
    if not isinstance(items, list):
        raise ValueError("Image response did not include a valid data list")

    for item in items:
        if not isinstance(item, dict):
            continue
        b64_json = item.get("b64_json")
        if isinstance(b64_json, str) and b64_json:
            return base64.b64decode(b64_json)
        image_url = item.get("url")
        if isinstance(image_url, str) and image_url:
            return fetch_binary_url(image_url)

    raise ValueError("Image response did not contain image bytes")


def extract_response_image_bytes(response: dict[str, Any]) -> bytes:
    outputs = response.get("output", [])
    if not isinstance(outputs, list):
        raise ValueError("Responses payload did not include an output list")

    for item in outputs:
        if not isinstance(item, dict):
            continue

        if item.get("type") == "image_generation_call":
            result = item.get("result")
            if isinstance(result, str) and result:
                return base64.b64decode(result)
            if isinstance(result, list):
                for entry in result:
                    if isinstance(entry, dict):
                        b64_json = entry.get("b64_json")
                        if isinstance(b64_json, str) and b64_json:
                            return base64.b64decode(b64_json)

        if item.get("type") == "message":
            contents = item.get("content", [])
            if not isinstance(contents, list):
                continue
            for content in contents:
                if not isinstance(content, dict):
                    continue
                if content.get("type") not in {"image", "output_image"}:
                    continue
                for key in ("image_base64", "b64_json", "data"):
                    value = content.get(key)
                    if isinstance(value, str) and value:
                        return base64.b64decode(value)

    raise ValueError("Responses payload did not contain generated image bytes")


def fetch_binary_url(url: str) -> bytes:
    session = build_requests_session()
    headers = dict(DEFAULT_REQUEST_HEADERS)
    headers.pop("Content-Type", None)
    response = session.get(url, headers=headers, timeout=DEFAULT_HTTP_TIMEOUT)
    response.raise_for_status()
    return response.content


def should_fallback_to_secondary_route(error: Exception) -> bool:
    if not isinstance(error, ApiError):
        return True
    if error.status_code in {401}:
        return False
    error_text = " ".join(
        part for part in (error.message, error.raw_body or "") if isinstance(part, str)
    ).lower()
    transient_markers = (
        "cloudflare",
        "browser's signature",
        "error 1010",
        "missing close_notify",
        "proxyerror",
        "remote end closed connection",
        "remote disconnected",
        "max retries exceeded",
    )
    return error.status_code in {None, 403, 429, 500, 502, 503, 504} or any(
        marker in error_text for marker in transient_markers
    )


def classify_error(route: str | None, error: Exception) -> str:
    if isinstance(error, ConfigError):
        return "proxy_incompatibility"
    if isinstance(error, ApiError):
        error_text = " ".join(
            part for part in (error.message, error.raw_body or "") if isinstance(part, str)
        ).lower()
        if any(
            marker in error_text
            for marker in (
                "missing close_notify",
                "proxyerror",
                "remote end closed connection",
                "remote disconnected",
                "max retries exceeded",
            )
        ):
            return "transport_instability"
        if "cloudflare" in error_text or "browser's signature" in error_text or "error 1010" in error_text:
            return "proxy_incompatibility"
        if error.status_code in {401, 403}:
            return "authentication_failure"
        if route == "/images/generations" and error.status_code in {404, 405, 410, 501}:
            return "missing_images_generations"
        if route == "/responses" and error.status_code in {404, 405, 410, 501}:
            return "missing_responses"
        if error.status_code in {429, 500, 502, 503, 504}:
            return "transport_instability"
        return "proxy_incompatibility"
    return "proxy_incompatibility"


def iter_generation_routes(primary_route: str | None) -> list[str]:
    routes = [primary_route or "/images/generations", "/images/generations", "/responses"]
    unique_routes: list[str] = []
    for route in routes:
        if route not in unique_routes:
            unique_routes.append(route)
    return unique_routes


def detect_capability(
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    size: str | None = "1024x1024",
    quality: str | None = "low",
    background: str | None = None,
    prompt: str = DEFAULT_TEST_PROMPT,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "supported": False,
        "base_url": None,
        "config_source": None,
        "image_model": None,
        "responses_model": None,
        "route": None,
        "failure_reason": None,
        "base_url_attempts": [],
        "probes": [],
    }

    try:
        config = load_config(base_url=base_url, api_key=api_key)
        resolved_base_url = config["base_url"]
        resolved_api_key = config["api_key"]
        report["config_source"] = config["source"]
        resolved_base_url, models, attempts = resolve_base_url_and_models(
            resolved_base_url,
            resolved_api_key,
        )
        report["base_url"] = resolved_base_url
        report["base_url_attempts"] = attempts
    except Exception as error:
        report["failure_reason"] = classify_error(None, error)
        report["error"] = str(error)
        return report

    report["models"] = models
    image_model = pick_image_model(models)
    if not image_model:
        report["failure_reason"] = "missing_image_model"
        return report

    responses_model = pick_responses_model(models, fallback_model=image_model)
    report["image_model"] = image_model
    report["responses_model"] = responses_model

    try:
        call_images_generation(
            base_url=resolved_base_url,
            api_key=resolved_api_key,
            model=image_model,
            prompt=prompt,
            size=size,
            quality=quality,
            background=background,
        )
        report["supported"] = True
        report["route"] = "/images/generations"
        report["probes"].append({"route": "/images/generations", "ok": True})
        return report
    except Exception as error:
        report["probes"].append(
            {
                "route": "/images/generations",
                "ok": False,
                "reason": classify_error("/images/generations", error),
                "error": str(error),
            }
        )

    try:
        call_responses_generation(
            base_url=resolved_base_url,
            api_key=resolved_api_key,
            model=responses_model,
            prompt=prompt,
            size=size,
            quality=quality,
            background=background,
        )
        report["supported"] = True
        report["route"] = "/responses"
        report["probes"].append({"route": "/responses", "ok": True})
        return report
    except Exception as error:
        report["probes"].append(
            {
                "route": "/responses",
                "ok": False,
                "reason": classify_error("/responses", error),
                "error": str(error),
            }
        )
        report["failure_reason"] = classify_error("/responses", error)
        return report


def generate_image(
    *,
    prompt: str,
    output: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    size: str | None = "1024x1024",
    quality: str | None = "high",
    background: str | None = None,
) -> dict[str, Any]:
    report = detect_capability(
        base_url=base_url,
        api_key=api_key,
        size=size,
        quality=quality,
        background=background,
    )
    if not report.get("supported"):
        raise RuntimeError(json.dumps(report, indent=2))

    config = load_config(base_url=base_url, api_key=api_key)
    resolved_api_key = config["api_key"]
    resolved_base_url = str(report["base_url"])
    route = report["route"]
    image_model = report["image_model"]
    responses_model = report["responses_model"]
    generation_errors: list[dict[str, str]] = []
    image_bytes: bytes | None = None
    used_model: str | None = None
    used_route: str | None = None

    for candidate_route in iter_generation_routes(route):
        try:
            if candidate_route == "/images/generations":
                image_bytes, _ = call_images_generation(
                    base_url=resolved_base_url,
                    api_key=resolved_api_key,
                    model=image_model,
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    background=background,
                )
                used_model = image_model
            else:
                image_bytes, _ = call_responses_generation(
                    base_url=resolved_base_url,
                    api_key=resolved_api_key,
                    model=responses_model,
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    background=background,
                )
                used_model = responses_model
            used_route = candidate_route
            break
        except Exception as error:
            generation_errors.append(
                {
                    "route": candidate_route,
                    "reason": classify_error(candidate_route, error),
                    "error": str(error),
                }
            )
            if not should_fallback_to_secondary_route(error):
                break

    if image_bytes is None or used_model is None or used_route is None:
        raise RuntimeError(
            json.dumps(
                {
                    "supported": True,
                    "base_url": resolved_base_url,
                    "image_model": image_model,
                    "responses_model": responses_model,
                    "route": route,
                    "generation_errors": generation_errors,
                },
                indent=2,
            )
        )

    output_path = resolve_output_path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)

    return {
        "saved_path": str(output_path),
        "route": used_route,
        "model": used_model,
        "image_model": image_model,
        "responses_model": responses_model,
    }


def resolve_output_path(output: str | None) -> pathlib.Path:
    if output:
        path = pathlib.Path(output).expanduser()
        if not path.is_absolute():
            path = pathlib.Path.cwd() / path
    else:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        path = pathlib.Path.cwd() / f"metero041-image-{timestamp}.png"

    if not path.suffix:
        path = path.with_suffix(".png")
    return path.resolve()
