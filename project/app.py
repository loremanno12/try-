import logging
import sys

from cache import ModelCache
from config import Config
from training import should_retrain, train_model
from ui import create_gradio_interface

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

config = Config()
model_cache = ModelCache()


def main():
    """Punto di ingresso principale per l'applicazione."""
    logger.info("=" * 60)
    logger.info("Avvio del Sistema Router AI")
    logger.info("=" * 60)

    if should_retrain(config):
        logger.info("Addestramento del modello in corso...")
        success, message = train_model(config, model_cache)
        if not success:
            logger.error(f"Addestramento fallito: {message}")
            logger.error(
                "Verifica che training_data.json esista con la struttura corretta"
            )
            return
        logger.info(message)
    else:
        model_cache.get_classifier(config.CLASSIFIER_PATH)
        model_cache.get_label_encoder(config.ENCODER_PATH)

    logger.info("Avvio dell'interfaccia Gradio")
    logger.info(
        f"Accedi a http://{config.GRADIO_SERVER_NAME}:{config.GRADIO_SERVER_PORT}"
    )
    logger.info("=" * 60)

    interface = create_gradio_interface(config, model_cache)
    interface.launch(
        server_name=config.GRADIO_SERVER_NAME,
        server_port=config.GRADIO_SERVER_PORT,
        share=config.GRADIO_SHARE,
    )


if __name__ == "__main__":
    main()
