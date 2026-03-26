"""Servizio Ollama per miglioramento prompt e validazione."""
import logging
import re
import time
from typing import Any, Dict, Optional

import requests

from config import Config

logger = logging.getLogger(__name__)

PREFIX_PATTERNS = (
    r"^\s*ecco il prompt migliorato:\s*",
    r"^\s*prompt migliorato:\s*",
    r"^\s*ecco:\s*",
    r"^\s*here is the improved prompt:\s*",
    r"^\s*improved prompt:\s*",
)


def validate_prompt(prompt: str) -> tuple[bool, str]:
    if not prompt:
        return False, "Il prompt non può essere vuoto"
    if not isinstance(prompt, str):
        return False, "Il prompt deve essere una stringa"
    prompt = prompt.strip()
    if not prompt:
        return False, "Il prompt non può contenere solo spazi"
    if len(prompt) > 5000:
        return False, "Il prompt è troppo lungo (max 5000 caratteri)"
    return True, ""


def _detect_prompt_profile(prompt: str) -> str:
    prompt_lower = prompt.lower()
    if any(token in prompt_lower for token in ("python", "javascript", "sql", "bug", "debug", "api", "codice", "script")):
        return "technical"
    if any(token in prompt_lower for token in ("spiega", "explain", "riassumi", "summary", "analizza", "analyze")):
        return "explanatory"
    if any(token in prompt_lower for token in ("story", "creative", "campagna", "marketing", "copy", "brand", "post social")):
        return "creative"
    return "general"


def _build_system_instruction(prompt: str, target_model: Optional[str]) -> str:
    profile = _detect_prompt_profile(prompt)
    profile_rules = {
        "technical": "Privilegia vincoli chiari, input/output attesi, linguaggio o stack e criteri di qualità verificabili.",
        "explanatory": "Privilegia pubblico target, livello di profondità, struttura della risposta ed esempi concreti.",
        "creative": "Privilegia tono, audience, formato, obiettivo e stile desiderato senza appesantire il testo.",
        "general": "Privilegia chiarezza, contesto, output atteso e criteri di completezza.",
    }
    target_hint = (
        f"Il router suggerisce come modello di destinazione '{target_model}'. "
        "Ottimizza il prompt per essere compatibile con quel tipo di modello senza citarlo esplicitamente nel testo finale."
        if target_model
        else "Non hai un modello di destinazione certo: rendi il prompt robusto e ben specificato."
    )
    return (
        "Sei un prompt engineer senior. Devi migliorare il prompt dell'utente mantenendo invariato l'obiettivo.\n"
        "Rispondi nella stessa lingua del prompt originale.\n"
        "Restituisci solo il prompt finale, senza titoli, spiegazioni, virgolette o markdown.\n"
        "Se il prompt e' gia' buono, rifiniscilo leggermente senza allungarlo inutilmente.\n"
        "Trasforma richieste vaghe in richieste operative, con contesto, vincoli, formato di output e criteri di qualita' quando utili.\n"
        f"{profile_rules[profile]}\n"
        f"{target_hint}"
    )


def _cleanup_improved_prompt(text: str) -> str:
    cleaned = (text or "").strip()
    for pattern in PREFIX_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip().strip('"').strip("'").strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _request_prompt_optimization(
    prompt: str, system_instruction: str, config: Config
) -> requests.Response:
    chat_url = f"{config.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_instruction},
            {
                "role": "user",
                "content": (
                    "Migliora questo prompt mantenendo il suo intento.\n\n"
                    f"{prompt.strip()}"
                ),
            },
        ],
        "stream": False,
        "options": {
            "temperature": config.OLLAMA_TEMPERATURE,
            "top_p": config.OLLAMA_TOP_P,
            "num_predict": config.OLLAMA_NUM_PREDICT,
        },
    }
    response = requests.post(chat_url, json=payload, timeout=config.OLLAMA_TIMEOUT)
    if response.status_code != 404:
        return response

    logger.warning("Endpoint /api/chat non disponibile, fallback a /api/generate")
    generate_url = f"{config.OLLAMA_BASE_URL}/api/generate"
    generate_payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": (
            f"{system_instruction}\n\n"
            "Migliora questo prompt mantenendo il suo intento.\n\n"
            f"{prompt.strip()}"
        ),
        "stream": False,
        "options": payload["options"],
    }
    return requests.post(
        generate_url, json=generate_payload, timeout=config.OLLAMA_TIMEOUT
    )


def check_ollama_health(config: Config) -> bool:
    try:
        response = requests.get(
            f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5
        )
        if response.status_code == 200:
            models = response.json().get("models", [])
            names = [m.get("name", "") for m in models]
            if config.OLLAMA_MODEL in names:
                logger.info("Modello %s è installato", config.OLLAMA_MODEL)
            else:
                logger.warning(
                    "Modello %s non trovato. Esegui: ollama pull %s",
                    config.OLLAMA_MODEL, config.OLLAMA_MODEL,
                )
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def improve_prompt_with_ollama(
    prompt: str, config: Config, target_model: Optional[str] = None
) -> Dict[str, Any]:
    try:
        is_valid, error_msg = validate_prompt(prompt)
        if not is_valid:
            return {
                "success": False,
                "error": error_msg,
                "improved_prompt": None,
                "original_prompt": prompt,
                "elapsed_time": 0,
            }
        logger.info("Miglioramento prompt tramite Ollama: %s...", prompt[:50])
        system_instruction = _build_system_instruction(prompt, target_model)
        start_time = time.time()
        response = _request_prompt_optimization(prompt, system_instruction, config)
        elapsed_time = time.time() - start_time
        response.raise_for_status()
        result = response.json()
        message = result.get("message") or {}
        improved_prompt = _cleanup_improved_prompt(
            message.get("content", "") or result.get("response", "")
        )
        if not improved_prompt:
            return {
                "success": False,
                "error": "Il modello non ha generato un prompt migliorato",
                "improved_prompt": None,
                "original_prompt": prompt,
                "elapsed_time": elapsed_time,
            }
        logger.info("Prompt migliorato in %.2f s", elapsed_time)
        return {
            "success": True,
            "error": None,
            "improved_prompt": improved_prompt,
            "original_prompt": prompt,
            "target_model": target_model,
            "elapsed_time": elapsed_time,
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": f"Timeout Ollama dopo {config.OLLAMA_TIMEOUT} s",
            "improved_prompt": None,
            "original_prompt": prompt,
            "elapsed_time": config.OLLAMA_TIMEOUT,
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": f"Impossibile connettersi a {config.OLLAMA_BASE_URL}",
            "improved_prompt": None,
            "original_prompt": prompt,
            "elapsed_time": 0,
        }
    except requests.exceptions.HTTPError as e:
        return {
            "success": False,
            "error": f"HTTP {e.response.status_code}. Modello {config.OLLAMA_MODEL} installato?",
            "improved_prompt": None,
            "original_prompt": prompt,
            "elapsed_time": 0,
        }
    except Exception as e:
        logger.exception("Errore Ollama")
        return {
            "success": False,
            "error": str(e),
            "improved_prompt": None,
            "original_prompt": prompt,
            "elapsed_time": 0,
        }
