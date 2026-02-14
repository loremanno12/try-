#!/usr/bin/env python
"""Script di health check per il servizio AI Router."""

import sys
import requests


def check_gradio_health() -> bool:
    """Verifica se Gradio è disponibile."""
    try:
        response = requests.get("http://localhost:7860/info", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def check_ollama_health() -> bool:
    """Verifica se Ollama è disponibile."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


if __name__ == "__main__":
    gradio_ok = check_gradio_health()
    ollama_ok = check_ollama_health()

    print(f"Gradio: {'✓' if gradio_ok else '✗'}")
    print(f"Ollama: {'✓' if ollama_ok else '✗'}")

    sys.exit(0 if gradio_ok else 1)
