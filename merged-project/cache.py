"""Cache per i modelli del Router AI."""
import pickle
import logging
from pathlib import Path
from typing import Optional

from sentence_transformers import SentenceTransformer
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)


class ModelCache:
    """Cache per i modelli caricati per evitare caricamenti ridondanti."""

    def __init__(self):
        self._embedding_model: Optional[SentenceTransformer] = None
        self._classifier: Optional[MLPClassifier] = None
        self._label_encoder: Optional[LabelEncoder] = None

    def get_embedding_model(self, model_name: str) -> SentenceTransformer:
        if self._embedding_model is None:
            logger.info("Caricamento modello di embedding: %s", model_name)
            self._embedding_model = SentenceTransformer(model_name)
        return self._embedding_model

    def get_classifier(self, path: Path) -> Optional[MLPClassifier]:
        if self._classifier is None and path.exists():
            logger.info("Caricamento classificatore da: %s", path)
            with open(path, "rb") as f:
                self._classifier = pickle.load(f)
        return self._classifier

    def get_label_encoder(self, path: Path) -> Optional[LabelEncoder]:
        if self._label_encoder is None and path.exists():
            logger.info("Caricamento label encoder da: %s", path)
            with open(path, "rb") as f:
                self._label_encoder = pickle.load(f)
        return self._label_encoder

    def set_classifier(self, classifier: MLPClassifier) -> None:
        self._classifier = classifier

    def set_label_encoder(self, encoder: LabelEncoder) -> None:
        self._label_encoder = encoder

    def clear(self) -> None:
        self._embedding_model = None
        self._classifier = None
        self._label_encoder = None
