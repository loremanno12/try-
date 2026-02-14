import json
import logging
import pickle
from pathlib import Path
from typing import Tuple

from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder

from cache import ModelCache
from config import Config

logger = logging.getLogger(__name__)


def load_training_data(file_path: Path) -> Tuple[list, list]:
    """Carica i dati di addestramento dal file JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        prompts = []
        models = []
        for item in data:
            for prompt in item["prompts"]:
                prompts.append(prompt)
                models.append(item["modello"])

        return prompts, models
    except json.JSONDecodeError as e:
        logger.error(f"Errore nel parsing del JSON: {e}")
        raise
    except KeyError as e:
        logger.error(f"Chiave mancante nel file di training: {e}")
        raise


def validate_training_data(prompts: list, models: list) -> bool:
    """Valida il formato dei dati di addestramento."""
    if not prompts or not models:
        logger.error("I dati di addestramento sono vuoti")
        return False

    if len(prompts) != len(models):
        logger.error("Il numero di prompt e modelli non corrisponde")
        return False

    if any(not p or not isinstance(p, str) for p in prompts):
        logger.error("I dati di addestramento contengono prompt non validi")
        return False

    return True


def should_retrain(config: Config) -> bool:
    """Verifica se il modello deve essere riaddestrato."""
    if not config.CLASSIFIER_PATH.exists() or not config.ENCODER_PATH.exists():
        logger.info("File del modello non trovati, addestramento necessario")
        return True

    if config.TRAINING_DATA_PATH.exists():
        training_data_mtime = config.TRAINING_DATA_PATH.stat().st_mtime
        classifier_mtime = config.CLASSIFIER_PATH.stat().st_mtime

        if training_data_mtime > classifier_mtime:
            logger.info(
                "I dati di addestramento sono più recenti del modello, riaddestramento necessario"
            )
            return True

    logger.info("Utilizzo del modello addestrato esistente")
    return False


def train_model(config: Config, model_cache: ModelCache) -> Tuple[bool, str]:
    """Addestra il modello AI router."""
    try:
        logger.info(
            f"Caricamento dati di addestramento da: {config.TRAINING_DATA_PATH}"
        )

        if not config.TRAINING_DATA_PATH.exists():
            error_msg = (
                f"File dei dati di addestramento non trovato: {config.TRAINING_DATA_PATH}"
            )
            logger.error(error_msg)
            return False, error_msg

        prompts, models = load_training_data(config.TRAINING_DATA_PATH)

        if not validate_training_data(prompts, models):
            return False, "Formato dei dati di addestramento non valido"

        logger.info(f"Caricati {len(prompts)} esempi di addestramento")

        embedding_model = model_cache.get_embedding_model(config.EMBEDDING_MODEL)

        logger.info("Generazione degli embeddings per i dati di addestramento")
        X = embedding_model.encode(prompts)

        logger.info("Codifica delle etichette")
        label_encoder = LabelEncoder()
        y = label_encoder.fit_transform(models)

        logger.info("Addestramento del classificatore MLP")
        classifier = MLPClassifier(
            hidden_layer_sizes=config.MLP_HIDDEN_LAYERS,
            max_iter=config.MLP_MAX_ITER,
            random_state=config.MLP_RANDOM_STATE,
        )
        classifier.fit(X, y)

        logger.info(f"Salvataggio del classificatore in: {config.CLASSIFIER_PATH}")
        with open(config.CLASSIFIER_PATH, "wb") as f:
            pickle.dump(classifier, f)

        logger.info(f"Salvataggio del label encoder in: {config.ENCODER_PATH}")
        with open(config.ENCODER_PATH, "wb") as f:
            pickle.dump(label_encoder, f)

        model_cache.set_classifier(classifier)
        model_cache.set_label_encoder(label_encoder)

        success_msg = (
            f"Modello addestrato con successo con {len(prompts)} esempi"
        )
        logger.info(success_msg)
        return True, success_msg

    except FileNotFoundError as e:
        error_msg = f"File non trovato: {e}"
        logger.error(error_msg)
        return False, error_msg
    except json.JSONDecodeError as e:
        error_msg = f"Errore nel parsing del JSON: {e}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Errore durante l'addestramento: {str(e)}"
        logger.exception(error_msg)
        return False, error_msg
