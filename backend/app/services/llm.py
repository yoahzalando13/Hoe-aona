"""Client LLM unique pour les offres gratuites compatibles OpenAI (Gemini AI Studio, Groq).

Les fournisseurs sont essayés dans l'ordre de LLM_PRIORITY ; en cas d'erreur ou de quota
atteint, le suivant prend le relais. Sans aucune clé, `available` vaut False et le
pipeline utilise ses replis heuristiques.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

from ..config import Settings, get_settings

log = logging.getLogger("hoe-aona.llm")


class LLMUnavailable(RuntimeError):
    pass


@dataclass
class Provider:
    name: str
    base_url: str
    api_key: str
    model: str
    vision_model: str | None


def _providers(s: Settings) -> list[Provider]:
    known = {
        "gemini": Provider("gemini", s.gemini_base_url, s.gemini_api_key or "", s.gemini_model, s.gemini_model),
        "groq": Provider("groq", s.groq_base_url, s.groq_api_key or "", s.groq_model, s.groq_vision_model),
    }
    order = [p.strip() for p in s.llm_priority.split(",") if p.strip() in known]
    return [known[name] for name in order if known[name].api_key]


def parse_json(text: str) -> Any:
    """Extrait un objet JSON d'une réponse (tolère les blocs ``` et le texte autour)."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(cleaned)
    except ValueError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


class LLMClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.providers = _providers(self.settings)
        self.last_provider: str | None = None

    @property
    def available(self) -> bool:
        return bool(self.providers)

    async def _post_chat(self, p: Provider, model: str, messages: list[dict], json_mode: bool,
                         temperature: float, max_tokens: int) -> str:
        body: dict[str, Any] = {"model": model, "messages": messages,
                                "temperature": temperature, "max_tokens": max_tokens}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if p.name == "gemini" or "gpt-oss" in model:
            # modèles « à raisonnement » : limiter la réflexion pour garder des jetons pour la réponse
            body["reasoning_effort"] = "low"
        async with httpx.AsyncClient(timeout=120) as http:
            resp = await http.post(f"{p.base_url.rstrip('/')}/chat/completions", json=body,
                                   headers={"Authorization": f"Bearer {p.api_key}"})
            if resp.status_code == 400 and ("response_format" in body or "reasoning_effort" in body):
                # certains modèles refusent ces options : nouvel essai sans elles
                body.pop("response_format", None)
                body.pop("reasoning_effort", None)
                resp = await http.post(f"{p.base_url.rstrip('/')}/chat/completions", json=body,
                                       headers={"Authorization": f"Bearer {p.api_key}"})
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"].get("content") or ""
        return content if isinstance(content, str) else "".join(part.get("text", "") for part in content)

    async def chat(self, messages: list[dict], json_mode: bool = False, temperature: float = 0.2,
                   max_tokens: int = 2000, vision: bool = False) -> str:
        errors = []
        for p in self.providers:
            model = p.vision_model if vision else p.model
            if not model:
                continue
            try:
                text = await self._post_chat(p, model, messages, json_mode, temperature, max_tokens)
                self.last_provider = f"{p.name}:{model}"
                return text
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{p.name}: {exc}")
                log.warning("LLM %s indisponible : %s", p.name, exc)
        raise LLMUnavailable("; ".join(errors) or "Aucune clé LLM configurée")

    async def chat_json(self, system: str, user: str, max_tokens: int = 4000) -> dict:
        """Réponse JSON (objet). Un nouvel essai est fait si la réponse est tronquée ou mal formée."""
        last_error: Exception | None = None
        for attempt in range(2):
            text = await self.chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                   json_mode=True, max_tokens=max_tokens + attempt * 2000)
            try:
                data = parse_json(text)
            except ValueError as exc:
                last_error = exc
                log.warning("Réponse JSON illisible (%s), nouvel essai", exc)
                continue
            if isinstance(data, list) and data and all(isinstance(x, dict) for x in data):
                data = {"claims": data}  # certains modèles renvoient directement la liste demandée
            if isinstance(data, dict):
                return data
            last_error = ValueError("Réponse JSON inattendue")
        raise last_error or ValueError("Réponse JSON inattendue")

    async def describe_image(self, image: bytes, mime: str, prompt: str) -> str:
        data_url = f"data:{mime};base64,{base64.b64encode(image).decode()}"
        messages = [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]}]
        return await self.chat(messages, json_mode=True, vision=True, max_tokens=3000)

    async def transcribe(self, audio: bytes, filename: str) -> str:
        """Transcription Whisper via Groq (offre gratuite)."""
        s = self.settings
        if not s.groq_api_key:
            raise LLMUnavailable("Transcription audio : clé GROQ_API_KEY absente")
        async with httpx.AsyncClient(timeout=180) as http:
            resp = await http.post(
                f"{s.groq_base_url.rstrip('/')}/audio/transcriptions",
                headers={"Authorization": f"Bearer {s.groq_api_key}"},
                data={"model": s.groq_whisper_model, "response_format": "json", "temperature": "0"},
                files={"file": (filename, audio)},
            )
            resp.raise_for_status()
            return resp.json().get("text", "")
