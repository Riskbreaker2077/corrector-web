"""
providers.py
------------
Capa de abstracción para hablar con varios proveedores de LLM
con una interfaz unificada: ProviderClient(provider, model, api_key).chat(system, user)

Todos los SDKs son perezosos (lazy import): solo se importa el SDK del
proveedor que se vaya a usar, para que la app arranque aunque falte alguno.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable

# Catálogo de modelos disponibles por proveedor.
# Orden = orden en el desplegable. El primero es el por defecto recomendado.
MODELS: dict[str, list[str]] = {
    "OpenAI": [
        "gpt-5.5",
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-4o-mini",  # legado, sigue siendo barato y suficiente para corrección
    ],
    "Anthropic": [
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
    ],
    "Gemini": [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
    ],
    "DeepSeek": [
        "deepseek-v4-pro",
        "deepseek-v4-flash",
    ],
    "MiniMax": [
        "MiniMax-M2.7",
        "MiniMax-M2.5",
    ],
}

# URL donde el usuario obtiene cada API key — útil para ayuda en la GUI.
KEY_URLS: dict[str, str] = {
    "OpenAI":    "https://platform.openai.com/api-keys",
    "Anthropic": "https://console.anthropic.com/settings/keys",
    "Gemini":    "https://aistudio.google.com/apikey",
    "DeepSeek":  "https://platform.deepseek.com/api_keys",
    "MiniMax":   "https://platform.minimax.io/user-center/basic-information/interface-key",
}


@dataclass
class CallResult:
    """Resultado de una llamada al modelo."""
    text: str
    ok: bool = True
    error: str = ""


# ---------------------------------------------------------------------------
# Implementaciones por proveedor
# ---------------------------------------------------------------------------

def _call_openai_compat(api_key: str, model: str, system: str, user: str,
                        base_url: str | None = None,
                        temperature: float = 0.3) -> CallResult:
    """
    Llama a cualquier endpoint compatible con la API de OpenAI ChatCompletions.
    Sirve para OpenAI, DeepSeek y MiniMax con solo cambiar base_url.
    """
    try:
        from openai import OpenAI
    except ImportError:
        return CallResult("", False, "Falta el paquete 'openai'. Instálalo con: pip install openai")

    try:
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = OpenAI(**kwargs)

        # Algunos modelos nuevos (gpt-5.x) exigen omitir temperature; lo enviamos
        # solo si el nombre no parece de la familia "thinking"/reasoning.
        send_temperature = not _is_reasoning_model(model)

        params = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if send_temperature:
            params["temperature"] = temperature

        resp = client.chat.completions.create(**params)
        return CallResult(resp.choices[0].message.content or "")
    except Exception as e:
        return CallResult("", False, f"{type(e).__name__}: {e}")


def _is_reasoning_model(model: str) -> bool:
    """Heurística: modelos de razonamiento que rechazan temperature."""
    m = model.lower()
    return (
        m.startswith("gpt-5")
        or m.startswith("o1") or m.startswith("o3") or m.startswith("o4")
    )


def _call_anthropic(api_key: str, model: str, system: str, user: str,
                    temperature: float = 0.3) -> CallResult:
    try:
        import anthropic
    except ImportError:
        return CallResult("", False, "Falta el paquete 'anthropic'. Instálalo con: pip install anthropic")

    try:
        client = anthropic.Anthropic(api_key=api_key)

        # claude-opus-4-7 rechaza temperature != default
        params = {
            "model": model,
            "max_tokens": 4096,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        if model != "claude-opus-4-7":
            params["temperature"] = temperature

        msg = client.messages.create(**params)
        # msg.content es lista de bloques; tomamos el texto plano.
        chunks = []
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                chunks.append(block.text)
        return CallResult("".join(chunks))
    except Exception as e:
        return CallResult("", False, f"{type(e).__name__}: {e}")


def _call_gemini(api_key: str, model: str, system: str, user: str,
                 temperature: float = 0.3) -> CallResult:
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return CallResult("", False, "Falta el paquete 'google-genai'. Instálalo con: pip install google-genai")

    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=temperature,
            ),
        )
        return CallResult(resp.text or "")
    except Exception as e:
        return CallResult("", False, f"{type(e).__name__}: {e}")


# Tabla de despacho — agrega aquí proveedores nuevos.
_DISPATCH: dict[str, Callable] = {
    "OpenAI":    lambda key, model, sys, usr, t: _call_openai_compat(key, model, sys, usr, None, t),
    "Anthropic": lambda key, model, sys, usr, t: _call_anthropic(key, model, sys, usr, t),
    "Gemini":    lambda key, model, sys, usr, t: _call_gemini(key, model, sys, usr, t),
    "DeepSeek":  lambda key, model, sys, usr, t: _call_openai_compat(key, model, sys, usr, "https://api.deepseek.com", t),
    "MiniMax":   lambda key, model, sys, usr, t: _call_openai_compat(key, model, sys, usr, "https://api.minimax.io/v1", t),
}


def call_model(provider: str, model: str, api_key: str,
               system: str, user: str, temperature: float = 0.3) -> CallResult:
    """
    Punto de entrada unificado. Devuelve siempre un CallResult.
    No lanza excepciones — los errores van en result.error.
    """
    if provider not in _DISPATCH:
        return CallResult("", False, f"Proveedor desconocido: {provider}")
    if not api_key:
        return CallResult("", False, f"Falta la API key de {provider}.")
    return _DISPATCH[provider](api_key, model, system, user, temperature)
