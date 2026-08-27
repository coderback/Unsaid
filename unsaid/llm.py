"""
Unified Multi-Provider LLM Abstraction Layer.
Supports:
  1. Anthropic Claude (claude-opus-4-8, claude-sonnet-4-6)
  2. Azure AI Foundry / Azure OpenAI (gpt-5.6-luna, custom model deployments)
  3. OpenAI (gpt-4o, gpt-4o-mini)
"""
import os
import json
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class _TemperatureUnsupported(Exception):
    """Internal signal: skip the temperature attempt for a model known to reject it."""

# Default model definitions
DEFAULT_MODELS = {
    "anthropic": {
        "judge": "claude-opus-4-8",
        "segmenter": "claude-sonnet-4-6",
    },
    "azure_foundry": {
        "judge": "gpt-5.6-luna",
        "segmenter": "gpt-5.6-luna",
    },
    "openai": {
        "judge": "gpt-4o",
        "segmenter": "gpt-4o-mini",
    },
}

_anthropic_client = None
_openai_clients: Dict[str, Any] = {}

# Set once a model has rejected an explicit temperature, so the retry path is
# taken directly instead of paying a failed request per call.
_ANTHROPIC_TEMPERATURE_UNSUPPORTED = False


def _set_anthropic_temperature_unsupported():
    global _ANTHROPIC_TEMPERATURE_UNSUPPORTED
    _ANTHROPIC_TEMPERATURE_UNSUPPORTED = True


def get_default_model(provider: str, role: str = "judge") -> str:
    prov = (provider or "anthropic").lower()
    return DEFAULT_MODELS.get(prov, DEFAULT_MODELS["anthropic"]).get(role, "claude-opus-4-8")


def _get_anthropic_client(api_key: Optional[str] = None):
    global _anthropic_client
    import anthropic

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY environment variable not set. Please provide an API key in configuration."
        )
    if api_key:
        return anthropic.Anthropic(api_key=api_key)
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=key)
    return _anthropic_client


def _get_azure_foundry_client(
    api_key: Optional[str] = None,
    azure_endpoint: Optional[str] = None,
    api_version: Optional[str] = None,
):
    import openai

    key = api_key or os.environ.get("AZURE_AI_API_KEY") or os.environ.get("AZURE_OPENAI_API_KEY")
    endpoint = (
        azure_endpoint
        or os.environ.get("AZURE_AI_ENDPOINT")
        or os.environ.get("AZURE_OPENAI_ENDPOINT")
        or "https://models.inference.ai.azure.com"
    )
    ver = api_version or os.environ.get("AZURE_AI_API_VERSION", "2024-05-01-preview")

    if not key:
        raise EnvironmentError(
            "AZURE_AI_API_KEY environment variable not set. Please provide an Azure API key in configuration."
        )

    cache_key = f"azure_{endpoint}_{key[:6]}"
    if cache_key in _openai_clients:
        return _openai_clients[cache_key]

    # If it's a standard Azure OpenAI resource (.openai.azure.com)
    if "openai.azure.com" in endpoint:
        client = openai.AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version=ver,
        )
    else:
        # Azure AI Foundry / Serverless Model endpoint (e.g. services.ai.azure.com / models.inference.ai.azure.com)
        client = openai.OpenAI(
            base_url=endpoint,
            api_key=key,
        )

    _openai_clients[cache_key] = client
    return client


def _get_openai_client(api_key: Optional[str] = None, base_url: Optional[str] = None):
    import openai

    key = api_key or os.environ.get("OPENAI_API_KEY")
    url = base_url or os.environ.get("OPENAI_BASE_URL")
    if not key:
        raise EnvironmentError(
            "OPENAI_API_KEY environment variable not set. Please provide an API key in configuration."
        )

    cache_key = f"openai_{url}_{key[:6]}"
    if cache_key in _openai_clients:
        return _openai_clients[cache_key]

    client = openai.OpenAI(api_key=key, base_url=url or None)
    _openai_clients[cache_key] = client
    return client


def call_structured_tool(
    provider: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    tool_name: str,
    tool_description: str,
    parameters_schema: Dict[str, Any],
    api_key: Optional[str] = None,
    azure_endpoint: Optional[str] = None,
    azure_api_version: Optional[str] = None,
    max_tokens: int = 4096,
    retries: int = 2,
    temperature: float = 0.0,
) -> Dict[str, Any]:
    """
    Unified caller for executing structured tool calls across Anthropic, Azure AI Foundry, and OpenAI.
    Returns the parsed dictionary produced by the tool call.

    temperature is requested but NOT honoured everywhere. Anthropic and standard
    OpenAI accept it; some reasoning-model deployments (including Azure AI
    Foundry gpt-5.6-luna) reject an explicit temperature, in which case the call
    is retried at the model fixed default and a warning is logged. Do not assume
    a run is reproducible without checking for that warning.
    """
    prov = (provider or "anthropic").lower()

    # ─────────────────────────────────────────────────────────────────────────
    # Provider 1: Anthropic Claude
    # ─────────────────────────────────────────────────────────────────────────
    if prov in ("anthropic", "claude"):
        import anthropic

        client = _get_anthropic_client(api_key=api_key)
        anthropic_tool = {
            "name": tool_name,
            "description": tool_description,
            "input_schema": parameters_schema,
        }

        base_kwargs: Dict[str, Any] = {
            "model": model or DEFAULT_MODELS["anthropic"]["judge"],
            "max_tokens": max_tokens,
            "system": system_prompt,
            "tools": [anthropic_tool],
            "tool_choice": {"type": "tool", "name": tool_name},
            "messages": [{"role": "user", "content": user_prompt}],
        }

        for attempt in range(retries + 1):
            try:
                try:
                    if _ANTHROPIC_TEMPERATURE_UNSUPPORTED:
                        raise _TemperatureUnsupported()
                    response = client.messages.create(**base_kwargs, temperature=temperature)
                except _TemperatureUnsupported:
                    response = client.messages.create(**base_kwargs)
                except anthropic.BadRequestError as b_err:
                    if "temperature" not in str(b_err).lower():
                        raise
                    # Newer reasoning models reject an explicit temperature. Drop it
                    # for the rest of the process rather than re-failing every call.
                    if not _ANTHROPIC_TEMPERATURE_UNSUPPORTED:
                        logger.warning(
                            "Anthropic model %s rejects an explicit temperature; "
                            "continuing at its fixed default. Output will NOT be "
                            "deterministic.", base_kwargs["model"],
                        )
                    _set_anthropic_temperature_unsupported()
                    response = client.messages.create(**base_kwargs)

                for block in response.content:
                    if block.type == "tool_use" and block.name == tool_name:
                        return block.input

                logger.warning("Anthropic returned no tool_use block on attempt %d", attempt + 1)
            except anthropic.RateLimitError:
                wait = 30 * (attempt + 1)
                logger.warning("Anthropic rate limit; waiting %ds…", wait)
                time.sleep(wait)
            except Exception as e:
                logger.error("Anthropic error on attempt %d: %s", attempt + 1, e)
                if attempt == retries:
                    raise

        raise RuntimeError(f"Anthropic tool call failed after {retries + 1} attempts.")

    # ─────────────────────────────────────────────────────────────────────────
    # Provider 2 & 3: Azure AI Foundry / OpenAI
    # ─────────────────────────────────────────────────────────────────────────
    elif prov in ("azure_foundry", "azure", "azure_openai", "openai"):
        import openai

        if prov in ("azure_foundry", "azure", "azure_openai"):
            client = _get_azure_foundry_client(
                api_key=api_key,
                azure_endpoint=azure_endpoint,
                api_version=azure_api_version,
            )
            target_model = model or DEFAULT_MODELS["azure_foundry"]["judge"]
        else:
            client = _get_openai_client(api_key=api_key, base_url=azure_endpoint)
            target_model = model or DEFAULT_MODELS["openai"]["judge"]

        openai_tool = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_description,
                "parameters": parameters_schema,
            },
        }

        for attempt in range(retries + 1):
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]

                kwargs: Dict[str, Any] = {
                    "model": target_model,
                    "messages": messages,
                    "tools": [openai_tool],
                    "tool_choice": {"type": "function", "function": {"name": tool_name}},
                }
                # Some reasoning models reject an explicit temperature; only send it
                # when it differs from their fixed default.
                if temperature is not None:
                    kwargs["temperature"] = temperature

                # Newer models (GPT-5.6 Luna, o1, o3, latest Azure Foundry) require max_completion_tokens
                try:
                    response = client.chat.completions.create(
                        **kwargs,
                        max_completion_tokens=max_tokens,
                    )
                except openai.BadRequestError as b_err:
                    err_msg = str(b_err).lower()
                    if "temperature" in err_msg and "unsupported" in err_msg:
                        logger.warning(
                            "%s rejects an explicit temperature; retrying at its fixed "
                            "default. Output will NOT be deterministic.", prov,
                        )
                        kwargs.pop("temperature", None)
                        response = client.chat.completions.create(
                            **kwargs, max_completion_tokens=max_tokens
                        )
                    elif "max_completion_tokens" in err_msg or "unsupported_parameter" in err_msg:
                        # Fallback for legacy OpenAI endpoints that only accept max_tokens
                        response = client.chat.completions.create(
                            **kwargs,
                            max_tokens=max_tokens,
                        )
                    else:
                        raise


                choice = response.choices[0]
                if choice.message.tool_calls:
                    for tc in choice.message.tool_calls:
                        if tc.function.name == tool_name:
                            return json.loads(tc.function.arguments)

                # Fallback: check if the model returned raw JSON in choice.message.content
                if choice.message.content:
                    raw_text = choice.message.content.strip()
                    if raw_text.startswith("```"):
                        parts = raw_text.split("```")
                        if len(parts) >= 2:
                            raw_text = parts[1]
                            if raw_text.startswith("json"):
                                raw_text = raw_text[4:]
                            raw_text = raw_text.strip()
                    try:
                        parsed = json.loads(raw_text)
                        if isinstance(parsed, dict):
                            if tool_name in parsed and isinstance(parsed[tool_name], dict):
                                return parsed[tool_name]
                            return parsed
                    except Exception:
                        pass

                logger.warning("%s returned no matching tool_call on attempt %d", prov, attempt + 1)
            except openai.RateLimitError:
                wait = 30 * (attempt + 1)
                logger.warning("%s rate limit; waiting %ds…", prov, wait)
                time.sleep(wait)
            except Exception as e:
                logger.error("%s error on attempt %d: %s", prov, attempt + 1, e)
                if attempt == retries:
                    raise

        raise RuntimeError(f"{prov} tool call failed after {retries + 1} attempts.")

    else:
        raise ValueError(f"Unsupported model provider: '{provider}'. Supported: 'anthropic', 'azure_foundry', 'openai'")
