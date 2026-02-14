"""Predizione del modello AI per un dato prompt."""
import logging
from typing import Any, Dict

from cache import ModelCache
from config import Config
from ollama_service import validate_prompt

logger = logging.getLogger(__name__)


def predict_model(
    prompt: str, config: Config, model_cache: ModelCache
) -> Dict[str, Any]:
    try:
        is_valid, error_msg = validate_prompt(prompt)
        if not is_valid:
            return {"success": False, "error": error_msg, "predicted_model": None, "confidence": None}
        embedding_model = model_cache.get_embedding_model(config.EMBEDDING_MODEL)
        classifier = model_cache.get_classifier(config.CLASSIFIER_PATH)
        label_encoder = model_cache.get_label_encoder(config.ENCODER_PATH)
        if classifier is None or label_encoder is None:
            return {"success": False, "error": "Modelli non trovati. Addestrare prima.", "predicted_model": None, "confidence": None}
        prompt_embedding = embedding_model.encode([prompt])
        prediction = classifier.predict(prompt_embedding)
        probabilities = classifier.predict_proba(prompt_embedding)
        predicted_model = label_encoder.inverse_transform(prediction)[0]
        confidence = float(probabilities[0].max())
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
        logger.exception("Errore predizione")
        return {"success": False, "error": str(e), "predicted_model": None, "confidence": None}


def format_prediction_output(result: Dict[str, Any], config: Config) -> str:
    if not result["success"]:
        return f"❌ **Errore:** {result['error']}"
    output = "### 🎯 Modello Consigliato\n\n"
    output += f"**{result['predicted_model']}**\n\n📊 Confidenza: **{result['confidence']:.1%}**\n\n"
    if result.get("all_probabilities"):
        output += "---\n\n### 📈 Top 3 Modelli\n\n"
        sorted_probs = sorted(result["all_probabilities"].items(), key=lambda x: x[1], reverse=True)[: config.TOP_N_PREDICTIONS]
        for i, (model, prob) in enumerate(sorted_probs, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
            bar = "█" * int(prob * 20) + "░" * (20 - int(prob * 20))
            output += f"{medal} **{model}**\n`{bar}` {prob:.1%}\n\n"
    if result["confidence"] < config.CONFIDENCE_THRESHOLD:
        output += f"\n---\n\n⚠️ Confidenza sotto {config.CONFIDENCE_THRESHOLD:.0%}. Migliora il prompt.\n"
    return output
