"""Motor de inferência para os classificadores BERTimbau Y1 e Y2.

Carrega os artefatos locais treinados em `models/`, compartilha o tokenizador
entre os dois classificadores e executa predições com tensores PyTorch em modo eval.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError

logger = logging.getLogger("fako.api.bertimbau_engine")


class BertimbauEngine:
    """Gerencia o ciclo de vida e a inferência dos modelos BERTimbau."""

    def __init__(
        self,
        models_dir: str | Path | None = None,
        device: str = "cpu",
        max_length: int = 256,
    ) -> None:
        self.raw_models_dir = models_dir or "models"
        self.device = device
        self.max_length = max_length
        self.model_version = "1.0.0"
        self.model_name = "BERTimbau (neuralmind/bert-base-portuguese-cased)"

        self.tokenizer: Any = None
        self.model_y1: Any = None
        self.model_y2: Any = None
        self.metadata: dict[str, Any] = {}
        self.is_available: bool = False
        self.error_message: str | None = None

    def _resolve_models_path(self) -> Path | None:
        """Resolve o caminho da pasta de modelos em múltiplos contextos de execução."""
        candidate = Path(self.raw_models_dir)
        if candidate.is_absolute() and candidate.exists():
            return candidate

        # Ordem de busca para diretórios relativos
        search_paths = [
            Path.cwd() / candidate,
            Path(__file__).resolve().parents[3] / candidate,  # raiz do repositório
            Path(__file__).resolve().parents[2] / candidate,  # /app/models dentro do container
            Path.cwd().parent / candidate,
        ]

        for p in search_paths:
            if p.exists() and (p / "bertimbau_y1").exists():
                return p.resolve()

        return None

    def load(self) -> bool:
        """Carrega o tokenizador e os dois modelos em memória.

        Não interrompe a aplicação caso os modelos não existam ou ocorra falha.
        """
        try:
            import torch  # noqa: F401
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            self.is_available = False
            self.error_message = f"Dependências de ML não instaladas: {exc}"
            logger.warning(self.error_message)
            return False

        models_path = self._resolve_models_path()
        if not models_path:
            self.is_available = False
            self.error_message = (
                f"Diretório de modelos '{self.raw_models_dir}' não encontrado. "
                "Verifique o volume ou a variável MODELS_DIR."
            )
            logger.warning(self.error_message)
            return False

        dir_y1 = models_path / "bertimbau_y1"
        dir_y2 = models_path / "bertimbau_y2"
        meta_file = models_path / "bertimbau_metadata.json"

        if not dir_y1.exists() or not dir_y2.exists():
            self.is_available = False
            self.error_message = (
                f"Artefatos bertimbau_y1 ou bertimbau_y2 não encontrados em {models_path}."
            )
            logger.warning(self.error_message)
            return False

        try:
            logger.info("Carregando tokenizador compartilhado de %s...", dir_y1)
            self.tokenizer = AutoTokenizer.from_pretrained(str(dir_y1), local_files_only=True)

            logger.info("Carregando classificador BERTimbau Y1 de %s...", dir_y1)
            self.model_y1 = AutoModelForSequenceClassification.from_pretrained(
                str(dir_y1), local_files_only=True
            )
            self.model_y1.to(self.device)
            self.model_y1.eval()

            logger.info("Carregando classificador BERTimbau Y2 de %s...", dir_y2)
            self.model_y2 = AutoModelForSequenceClassification.from_pretrained(
                str(dir_y2), local_files_only=True
            )
            self.model_y2.to(self.device)
            self.model_y2.eval()

            if meta_file.exists():
                with open(meta_file, encoding="utf-8") as f:
                    self.metadata = json.load(f)

            self.is_available = True
            self.error_message = None
            logger.info(
                "Modelos BERTimbau carregados com sucesso no dispositivo '%s'.", self.device
            )
            return True

        except Exception as exc:  # noqa: BLE001
            self.is_available = False
            self.error_message = f"Falha ao carregar artefatos do BERTimbau: {exc}"
            logger.error(self.error_message, exc_info=True)
            return False

    def predict(self, text: str) -> dict[str, Any]:
        """Executa a inferência síncrona nos modelos Y1 e Y2."""
        if not self.is_available or self.model_y1 is None or self.model_y2 is None:
            raise ServiceUnavailableError(
                f"Serviço de IA indisponível: {self.error_message or 'modelos não inicializados'}"
            )

        import torch

        encoded = self.tokenizer(
            text,
            max_length=self.max_length,
            padding=False,
            truncation=True,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in encoded.items()}

        with torch.no_grad():
            out_y1 = self.model_y1(**inputs)
            out_y2 = self.model_y2(**inputs)

            probs_y1 = torch.softmax(out_y1.logits, dim=-1)[0].cpu().tolist()
            probs_y2 = torch.softmax(out_y2.logits, dim=-1)[0].cpu().tolist()

            pred_y1 = int(torch.argmax(out_y1.logits, dim=-1)[0].item())
            pred_y2 = int(torch.argmax(out_y2.logits, dim=-1)[0].item())

        return {
            "pred_y1": pred_y1,
            "probs_y1": probs_y1,
            "pred_y2": pred_y2,
            "probs_y2": probs_y2,
            "device": self.device,
            "model_name": self.model_name,
            "version": self.model_version,
            "training_timestamp": self.metadata.get("timestamp_utc"),
            "dataset_hash": self.metadata.get("dataset_hash"),
        }


_engine_instance: BertimbauEngine | None = None


def get_bertimbau_engine() -> BertimbauEngine:
    """Retorna a instância singleton do motor de inferência."""
    global _engine_instance
    if _engine_instance is None:
        settings = get_settings()
        _engine_instance = BertimbauEngine(
            models_dir=settings.models_dir,
            device=settings.ai_device,
        )
    return _engine_instance


def set_bertimbau_engine(engine: BertimbauEngine | None) -> None:
    """Permite injetar uma instância mockada durante testes automatizados."""
    global _engine_instance
    _engine_instance = engine
