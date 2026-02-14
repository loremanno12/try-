"""Configurazione centrale per il sistema AI Router (env + default)."""
import os
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class Config:
    """Configurazione per il sistema AI Router."""

    MODEL_DIR: Path = Path(os.getenv("MODEL_DIR", "models"))
    CLASSIFIER_PATH: Optional[Path] = None
    ENCODER_PATH: Optional[Path] = None

    TRAINING_DATA_PATH: Path = Path(
        os.getenv("TRAINING_DATA_PATH", "training_data.json")
    )

    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    MLP_HIDDEN_LAYERS: Tuple[int, ...] = tuple(
        map(int, os.getenv("MLP_HIDDEN_LAYERS", "100,50").split(","))
    )
    MLP_MAX_ITER: int = int(os.getenv("MLP_MAX_ITER", "500"))
    MLP_RANDOM_STATE: int = int(os.getenv("MLP_RANDOM_STATE", "42"))

    CONFIDENCE_THRESHOLD: float = float(
        os.getenv("CONFIDENCE_THRESHOLD", "0.5")
    )
    TOP_N_PREDICTIONS: int = int(os.getenv("TOP_N_PREDICTIONS", "3"))

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma3:270m")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "60"))

    GRADIO_SERVER_NAME: str = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
    GRADIO_SERVER_PORT: int = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    GRADIO_SHARE: bool = os.getenv("GRADIO_SHARE", "false").lower() == "true"

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __post_init__(self):
        if self.CLASSIFIER_PATH is None:
            self.CLASSIFIER_PATH = self.MODEL_DIR / "mlp_classifier.pkl"
        if self.ENCODER_PATH is None:
            self.ENCODER_PATH = self.MODEL_DIR / "label_encoder.pkl"
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
