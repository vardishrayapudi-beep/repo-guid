"""Ollama client interaction functions with robust parsing and error handling."""

from __future__ import annotations

from typing import Any
import requests
import ollama

from models import RepoGuideError


def get_installed_ollama_models(client: Any = None) -> list[str]:
    """
    Retrieves installed Ollama models, supporting both response formats:
    - Object with .models attribute (each with .model or .name)
    - Dict with 'models' key (each with 'model' or 'name')

    Returns an empty list gracefully if Ollama is not running or unreachable.
    """
    api = client if client is not None else ollama
    try:
        data = api.list()
    except (
        ollama.RequestError,
        ollama.ResponseError,
        ConnectionError,
        OSError,
        requests.RequestException,
    ):
        return []
    except Exception:
        # Fallback safeguard against unexpected driver issues
        return []

    raw_models = getattr(data, "models", None)
    if raw_models is None and isinstance(data, dict):
        raw_models = data.get("models", [])

    if not raw_models:
        return []

    model_names: list[str] = []
    for m in raw_models:
        name = None
        if hasattr(m, "model") and m.model:
            name = m.model
        elif hasattr(m, "name") and m.name:
            name = m.name
        elif isinstance(m, dict):
            name = m.get("model") or m.get("name")
        elif isinstance(m, str):
            name = m

        if name and name not in model_names:
            model_names.append(name)

    return model_names


def run_ollama_chat(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    client: Any = None,
) -> str:
    """
    Executes a chat generation with a local Ollama model.
    Parses both object-based and dictionary-based responses.
    Translates raw API errors into actionable RepoGuideError messages.
    """
    api = client if client is not None else ollama
    try:
        response = api.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={
                "num_ctx": 4096,
            },
        )

        # Handle object or dict response formats
        if hasattr(response, "message") and hasattr(response.message, "content"):
            return response.message.content
        elif isinstance(response, dict) and "message" in response:
            msg = response["message"]
            if isinstance(msg, dict):
                return msg.get("content", "")
            return getattr(msg, "content", str(msg))
        elif hasattr(response, "content"):
            return response.content
        return str(response)

    except ollama.ResponseError as e:
        status = getattr(e, "status_code", None)
        msg_lower = str(e).lower()
        if status == 404 or "not found" in msg_lower or "model" in msg_lower and "not found" in msg_lower:
            raise RepoGuideError(
                f"📦 Model '{model_name}' was not found in Ollama. "
                f"Please run `ollama pull {model_name}` in your terminal to download and install it."
            ) from e
        raise RepoGuideError(f"❌ Ollama model error: {e}") from e

    except (ollama.RequestError, ConnectionError, OSError, requests.RequestException) as e:
        err_msg = str(e)
        if any(k in err_msg.lower() for k in ["connection", "connect", "refused", "111", "10061"]):
            raise RepoGuideError(
                "🔌 Ollama is not running. Please start the Ollama service on your machine "
                "(`ollama serve` or open the Ollama desktop app)."
            ) from e
        raise RepoGuideError(f"❌ Ollama communication error: {err_msg}") from e
