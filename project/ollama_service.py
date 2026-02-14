import logging

import requests

from config import Config

logger = logging.getLogger(__name__)


def validate_prompt(prompt: str) -> tuple[bool, str]:
    """Valida il prompt dell'utente."""
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
    """Verifica se Ollama è disponibile."""
    try:
        response = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


