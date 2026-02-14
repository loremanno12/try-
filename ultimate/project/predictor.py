import logging
from typing import Any, Dict

from cache import ModelCache
from config import Config
from ollama_service import validate_prompt

logger = logging.getLogger(__name__)


def predict_model(prompt: str, config: Config, model_cache: ModelCache) -> Dict[str, Any]:
    """Predice quale modello utilizzare per un dato prompt."""
    try:
        is_valid, error_msg = validate_prompt(prompt)
        if not is_valid:
            logger.warning(f"Prompt non valido: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "predicted_model": None,
                "confidence": None,
            }

        embedding_model = model_cache.get_embedding_model(config.EMBEDDING_MODEL)
        classifier = model_cache.get_classifier(config.CLASSIFIER_PATH)
        label_encoder = model_cache.get_label_encoder(config.ENCODER_PATH)

        if classifier is None or label_encoder is None:
            error_msg = "Modelli non trovati. Addestrare prima il modello."
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "predicted_model": None,
                "confidence": None,
            }

        logger.info(f"Predizione del modello per il prompt: {prompt[:50]}...")
        prompt_embedding = embedding_model.encode([prompt])

        prediction = classifier.predict(prompt_embedding)
        probabilities = classifier.predict_proba(prompt_embedding)

        predicted_model = label_encoder.inverse_transform(prediction)[0]
        confidence = float(probabilities[0].max())

        logger.info(f"Modello predetto: {predicted_model} (confidenza: {confidence:.2%})")

        if confidence < config.CONFIDENCE_THRESHOLD:
            logger.warning(f"Predizione a bassa confidenza: {confidence:.2%}")

        return {
            "success": True,
            "error": None,
            "predicted_model": predicted_model,
            "confidence": confidence,
            "all_probabilities": {
                label_encoder.inverse_transform([i])[0]: float(prob)
                for i, prob in enumerate(probabilities[0])
            },
        }

    except Exception as e:
        error_msg = f"Errore durante la predizione: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "predicted_model": None,
            "confidence": None,
        }


def format_prediction_output(result: Dict[str, Any], config: Config) -> str:
    """Formatta il risultato della predizione per la visualizzazione."""
    if not result["success"]:
        return f"❌ **Errore:** {result['error']}"

    output = f"### 🎯 Modello Consigliato\n\n"
    output += f"**{result['predicted_model']}**\n\n"
    output += f"📊 Confidenza: **{result['confidence']:.1%}**\n\n"

    if result.get("all_probabilities"):
        output += "---\n\n"
        output += "### 📈 Top 3 Modelli\n\n"

        sorted_probs = sorted(
            result["all_probabilities"].items(), key=lambda x: x[1], reverse=True
        )[: config.TOP_N_PREDICTIONS]

        for i, (model, prob) in enumerate(sorted_probs, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
            bar_length = int(prob * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)

            output += f"{medal} **{model}**\n"
            output += f"`{bar}` {prob:.1%}\n\n"

    if result["confidence"] < config.CONFIDENCE_THRESHOLD:
        output += "\n---\n\n"
        output += f"⚠️ **Attenzione:** Confidenza sotto la soglia del {config.CONFIDENCE_THRESHOLD:.0%}. "
        output += "Considera di migliorare il prompt per risultati più accurati.\n"

    return output
