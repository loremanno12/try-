"""Servizio Ollama per miglioramento prompt e validazione."""
import logging
import time
from typing import Any, Dict

import requests

from config import Config

logger = logging.getLogger(__name__)


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


def improve_prompt_with_ollama(prompt: str, config: Config) -> Dict[str, Any]:
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
        system_instruction = """Sei un esperto nel migliorare i prompt per modelli AI.
Il tuo compito è riformulare il prompt dell'utente per renderlo più chiaro, specifico e dettagliato,
mantenendo l'intento originale ma rendendolo più efficace per ottenere risposte di qualità.

Regole importanti:
1. Mantieni la stessa lingua del prompt originale (italiano, inglese, ecc.)
2. Sii conciso ma specifico - aggiungi dettagli utili senza essere prolisso
3. Aggiungi contesto solo se necessario per chiarire l'intento
4. Non cambiare l'obiettivo principale del prompt
5. Restituisci SOLO il prompt migliorato, senza spiegazioni o commenti aggiuntivi
6. Non iniziare con frasi come "Ecco il prompt migliorato:" - scrivi direttamente il prompt

Esempi:
- Input: "scrivi codice python"
  Output: "Scrivi una funzione Python ben documentata con type hints che risolva il seguente problema:"

- Input: "spiega quantum computing"
  Output: "Fornisci una spiegazione chiara e accessibile del quantum computing, includendo i concetti fondamentali di qubit, sovrapposizione e entanglement, con esempi pratici"
"""
        full_prompt = (
            f"{system_instruction}\n\n"
            f"Prompt originale da migliorare:\n{prompt}\n\nPrompt migliorato:"
        )
        url = f"{config.OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": config.OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": 0.7, "top_p": 0.9, "num_predict": 500},
        }
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=config.OLLAMA_TIMEOUT)
        elapsed_time = time.time() - start_time
        response.raise_for_status()
        result = response.json()
        improved_prompt = result.get("response", "").strip()
        if not improved_prompt:
            return {
                "success": False,
                "error": "Il modello non ha generato un prompt migliorato",
                "improved_prompt": None,
                "original_prompt": prompt,
                "elapsed_time": elapsed_time,
            }
        for prefix in [
            "Ecco il prompt migliorato:",
            "Prompt migliorato:",
            "Ecco:",
            "Here is the improved prompt:",
            "Improved prompt:",
        ]:
            if improved_prompt.lower().startswith(prefix.lower()):
                improved_prompt = improved_prompt[len(prefix) :].strip()
        logger.info("Prompt migliorato in %.2f s", elapsed_time)
        return {
            "success": True,
            "error": None,
            "improved_prompt": improved_prompt,
            "original_prompt": prompt,
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
