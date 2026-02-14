import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cache import ModelCache
from config import Config
from predictor import predict_model, format_prediction_output
from ui import improve_prompt_with_tinyllama

logger = logging.getLogger(__name__)

config = Config()
model_cache = ModelCache()


class PromptRequest(BaseModel):
    prompt: str


class ImprovedPromptResponse(BaseModel):
    original: str
    improved: str
    success: bool
    error: str | None = None


class PredictionRequest(BaseModel):
    prompt: str


class PredictionResponse(BaseModel):
    success: bool
    predicted_model: str | None = None
    confidence: float | None = None
    all_probabilities: dict[str, float] | None = None
    error: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API inizializzata")
    yield
    logger.info("API chiusa")


app = FastAPI(title="AI Router API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/improve-prompt", response_model=ImprovedPromptResponse)
async def improve_prompt(request: PromptRequest):
    """Migliora un prompt usando TinyLlama."""
    try:
        if not request.prompt or not request.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt vuoto")

        improved = improve_prompt_with_tinyllama(request.prompt, config)

        return ImprovedPromptResponse(
            original=request.prompt,
            improved=improved,
            success=True,
        )

    except Exception as e:
        logger.exception("Errore nel miglioramento del prompt")
        return ImprovedPromptResponse(
            original=request.prompt,
            improved="",
            success=False,
            error=str(e),
        )


@app.post("/api/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Predice quale modello utilizzare per il prompt."""
    try:
        if not request.prompt or not request.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt vuoto")

        result = predict_model(request.prompt, config, model_cache)

        if not result["success"]:
            return PredictionResponse(
                success=False,
                error=result["error"],
            )

        return PredictionResponse(
            success=True,
            predicted_model=result["predicted_model"],
            confidence=result["confidence"],
            all_probabilities=result.get("all_probabilities"),
        )

    except Exception as e:
        logger.exception("Errore nella predizione")
        return PredictionResponse(
            success=False,
            error=str(e),
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=config.GRADIO_SERVER_NAME,
        port=8000,
    )
