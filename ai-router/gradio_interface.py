import logging
from typing import Tuple
import requests

import gradio as gr

from cache import ModelCache
from config import Config
from predictor import predict_model, format_prediction_output
from ollama_service import improve_prompt_with_ollama

logger = logging.getLogger(__name__)


def create_gradio_interface(config: Config, model_cache: ModelCache) -> gr.Blocks:
    """Crea l'interfaccia web Gradio."""

    custom_css = """
    .gradio-container {
        font-family: 'Inter', sans-serif !important;
    }

    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 1rem;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
    }

    .btn-primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
    }

    .btn-secondary {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
    }
    """

    def predict_wrapper(prompt: str) -> str:
        """Wrapper per la predizione."""
        if not prompt or not prompt.strip():
            return "⚠️ **Inserisci un prompt per ottenere una predizione**"

        result = predict_model(prompt, config, model_cache)
        return format_prediction_output(result, config)

    def improve_wrapper(prompt: str) -> str:
        """Wrapper per il miglioramento del prompt."""
        if not prompt or not prompt.strip():
            return "⚠️ **Inserisci un prompt da migliorare**"

        result = improve_prompt_with_ollama(prompt, config)
        if result["success"]:
            return result["improved_prompt"]
        else:
            logger.warning(f"Errore nel miglioramento del prompt: {result['error']}")
            return prompt  # fallback al prompt originale se fallisce

    theme = gr.themes.Soft(
        primary_hue="purple",
        secondary_hue="pink",
        neutral_hue="slate",
        font=["Inter", "sans-serif"],
    )

    with gr.Blocks(title="🤖 AI Router System", theme=theme, css=custom_css) as interface:
        gr.HTML(
            """
        <div class="main-header">
            <h1 style="margin: 0; font-size: 2.5rem; font-weight: 700;">
                🤖 Sistema Router AI
            </h1>
            <p style="margin-top: 0.5rem; font-size: 1.1rem; opacity: 0.95;">
                Trova il modello AI perfetto per il tuo prompt
            </p>
        </div>
        """
        )

        with gr.Row(equal_height=True):
            with gr.Column(scale=1):
                gr.Markdown("### 📝 Il Tuo Prompt")

                prompt_input = gr.Textbox(
                    label="",
                    placeholder="✍️ Scrivi qui la tua domanda o richiesta...",
                    lines=6,
                    max_lines=12,
                    show_label=False,
                )

                with gr.Row():
                    improve_btn = gr.Button(
                        "✨ Migliora Prompt",
                        variant="secondary",
                        size="lg",
                    )
                    predict_btn = gr.Button(
                        "🔍 Predici Modello",
                        variant="primary",
                        size="lg",
                    )

                gr.Markdown("### 📊 Risultato")
                prediction_output = gr.Markdown(
                    value="*Inserisci un prompt e clicca su 'Predici Modello' o 'Migliora Prompt' per iniziare*",
                    show_label=False,
                )

        with gr.Accordion("💡 Esempi di Prompt", open=False):
            gr.Examples(
                examples=[
                    ["Scrivi una funzione Python per calcolare i numeri di Fibonacci"],
                    ["Spiega il quantum computing in termini semplici"],
                    ["Genera una storia creativa su un viaggiatore nel tempo"],
                    ["Debug questo codice: print('Ciao Mondo)"],
                    ["Come posso ottimizzare le prestazioni del mio database?"],
                ],
                inputs=prompt_input,
                label="",
            )

        with gr.Accordion("📚 Informazioni", open=False):
            gr.Markdown(
                f"""
            ### 🎯 Come Funziona

            - **Predizione:** SentenceTransformer + MLPClassifier
            - **Soglia confidenza:** {config.CONFIDENCE_THRESHOLD:.0%}
            """
            )

        improve_btn.click(fn=improve_wrapper, inputs=prompt_input, outputs=prompt_input)

        predict_btn.click(fn=predict_wrapper, inputs=prompt_input, outputs=prediction_output)

        prompt_input.submit(
            fn=predict_wrapper, inputs=prompt_input, outputs=prediction_output
        )

    return interface