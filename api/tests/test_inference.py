"""Testes automatizados do serviço de inferência e integração do BERTimbau."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.core.deps import get_current_admin
from app.core.exceptions import ServiceUnavailableError
from app.integrations.bertimbau_engine import BertimbauEngine, set_bertimbau_engine
from app.main import app
from app.models.user import User
from app.services.inference_service import InferenceService
from app.services.text_cleaner import limpar_texto


class TestTextCleaner(unittest.TestCase):
    """Garante que a limpeza textual na API reproduza o comportamento de treino."""

    def test_remove_urls(self):
        texto = "Confira a notícia em https://site.com/noticia e www.boatos.org sobre vacinas."
        limpo = limpar_texto(texto)
        self.assertNotIn("https://", limpo)
        self.assertNotIn("www.", limpo)
        self.assertIn("vacinas.", limpo)

    def test_remove_prefixos_checagem(self):
        casos = [
            ("FATO OU FAKE: Vacina da gripe altera DNA.", "Vacina da gripe altera DNA."),
            ("É FAKE: Chá de ervas cura infecção.", "Chá de ervas cura infecção."),
            ("COMPROVA: Documento vazado sobre eleições.", "Documento vazado sobre eleições."),
            ("BOATO — Alerta urgente sobre novo vírus.", "Alerta urgente sobre novo vírus."),
        ]
        for entrada, esperado in casos:
            with self.subTest(entrada=entrada):
                self.assertEqual(limpar_texto(entrada), esperado)

    def test_remove_sufixos_veiculo(self):
        casos = [
            ("Governo anuncia novo programa social | G1", "Governo anuncia novo programa social"),
            ("MEC altera calendário de matrículas - Lupa", "MEC altera calendário de matrículas"),
        ]
        for entrada, esperado in casos:
            with self.subTest(entrada=entrada):
                self.assertEqual(limpar_texto(entrada), esperado)

    def test_preserva_maiusculas_e_pontuacao(self):
        texto = "ATENÇÃO: A OMS declarou emergência internacional em 2024?"
        limpo = limpar_texto(texto)
        self.assertTrue(limpo.startswith("ATENÇÃO:"))
        self.assertTrue(limpo.endswith("?"))


class TestInferenceServiceUnit(unittest.TestCase):
    """Testes unitários da lógica de negócios e avaliação pedagógica do InferenceService."""

    def setUp(self):
        self.mock_engine = MagicMock(spec=BertimbauEngine)
        self.mock_engine.is_available = True
        self.mock_engine.model_name = "BERTimbau Teste"
        self.mock_engine.model_version = "1.0.0"
        self.mock_engine.device = "cpu"
        self.service = InferenceService(self.mock_engine)

    def test_caso_nao_confiavel(self):
        """Y1=0 (falso) e Y2=0 (não-verdadeiro) -> status 'nao_confiavel'."""
        self.mock_engine.predict.return_value = {
            "pred_y1": 0,
            "probs_y1": [0.85, 0.15],
            "pred_y2": 0,
            "probs_y2": [0.92, 0.08],
            "model_name": "BERTimbau",
            "version": "1.0.0",
            "device": "cpu",
        }
        resp = self.service.analyze("Boato falso sem embasamento algum.")
        self.assertEqual(resp.educational_assessment.status, "nao_confiavel")
        self.assertFalse(resp.educational_assessment.is_inconclusive)
        self.assertEqual(resp.y1.predicted_label, "falso")
        self.assertEqual(resp.y2.predicted_label, "nao_verdadeiro")

    def test_caso_confiavel(self):
        """Y1=1 (não-falso) e Y2=1 (verdadeiro) -> status 'confiavel'."""
        self.mock_engine.predict.return_value = {
            "pred_y1": 1,
            "probs_y1": [0.10, 0.90],
            "pred_y2": 1,
            "probs_y2": [0.25, 0.75],
            "model_name": "BERTimbau",
            "version": "1.0.0",
            "device": "cpu",
        }
        resp = self.service.analyze("Ministério da Saúde inicia campanha anual de vacinação.")
        self.assertEqual(resp.educational_assessment.status, "confiavel")
        self.assertFalse(resp.educational_assessment.is_inconclusive)
        self.assertEqual(resp.y1.predicted_label, "nao_falso")
        self.assertEqual(resp.y2.predicted_label, "verdadeiro")

    def test_caso_atencao_ou_enganoso(self):
        """Y1=1 (não-falso) e Y2=0 (não-verdadeiro) -> status 'atencao_ou_enganoso'."""
        self.mock_engine.predict.return_value = {
            "pred_y1": 1,
            "probs_y1": [0.30, 0.70],
            "pred_y2": 0,
            "probs_y2": [0.80, 0.20],
            "model_name": "BERTimbau",
            "version": "1.0.0",
            "device": "cpu",
        }
        resp = self.service.analyze("Notícia com dados reais mas tirada de contexto.")
        self.assertEqual(resp.educational_assessment.status, "atencao_ou_enganoso")
        self.assertFalse(resp.educational_assessment.is_inconclusive)

    def test_caso_inconsistente_logico(self):
        """Y1=0 (falso) e Y2=1 (verdadeiro) -> status 'inconclusivo'."""
        self.mock_engine.predict.return_value = {
            "pred_y1": 0,
            "probs_y1": [0.60, 0.40],
            "pred_y2": 1,
            "probs_y2": [0.45, 0.55],
            "model_name": "BERTimbau",
            "version": "1.0.0",
            "device": "cpu",
        }
        resp = self.service.analyze("Afirmação com predições divergentes.")
        self.assertEqual(resp.educational_assessment.status, "inconclusivo")
        self.assertTrue(resp.educational_assessment.is_inconclusive)
        self.assertIn("conflitantes", resp.educational_assessment.summary)

    def test_motor_indisponivel_lanca_erro(self):
        """Se o motor levantar ServiceUnavailableError, o serviço propaga."""
        self.mock_engine.predict.side_effect = ServiceUnavailableError("Modelos não carregados.")
        with self.assertRaises(ServiceUnavailableError):
            self.service.analyze("Qualquer afirmação para teste.")


class TestInferenceController(unittest.TestCase):
    """Testes da rota HTTP POST /ai/analyze com TestClient."""

    def setUp(self):
        self.mock_engine = MagicMock(spec=BertimbauEngine)
        self.mock_engine.is_available = True
        self.mock_engine.predict.return_value = {
            "pred_y1": 0,
            "probs_y1": [0.80, 0.20],
            "pred_y2": 0,
            "probs_y2": [0.95, 0.05],
            "model_name": "BERTimbau Teste",
            "version": "1.0.0",
            "device": "cpu",
            "training_timestamp": "2026-10-07T20:41:27Z",
            "dataset_hash": "hash_teste",
        }
        set_bertimbau_engine(self.mock_engine)

        self.mock_admin = User(id=1, username="admin_teste", is_admin=True)
        # Mock de autenticação de admin padrão
        app.dependency_overrides[get_current_admin] = lambda: self.mock_admin
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        set_bertimbau_engine(None)

    def test_analyze_sucesso(self):
        payload = {"statement": "Vacina da gripe causa doenças graves em crianças."}
        response = self.client.post("/ai/analyze", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["statement"], payload["statement"])
        self.assertIn("cleaned_statement", data)
        self.assertEqual(data["educational_assessment"]["status"], "nao_confiavel")
        self.assertEqual(data["y1"]["predicted_class"], 0)
        self.assertEqual(data["y1"]["predicted_label"], "falso")
        self.assertEqual(data["y2"]["predicted_class"], 0)
        self.assertEqual(data["y2"]["predicted_label"], "nao_verdadeiro")
        self.assertIn("disclaimer", data)
        self.assertIn("methodology_note", data)

    def test_analyze_validacao_texto_curto_ou_vazio(self):
        """Texto com menos de 5 caracteres ou apenas espaços deve retornar 422."""
        casos = ["", "   ", "abc", "1234"]
        for c in casos:
            with self.subTest(caso=c):
                response = self.client.post("/ai/analyze", json={"statement": c})
                self.assertEqual(response.status_code, 422)

    def test_analyze_motor_indisponivel_retorna_503(self):
        """Quando o motor está indisponível, deve responder com HTTP 503."""
        self.mock_engine.is_available = False
        self.mock_engine.predict.side_effect = ServiceUnavailableError(
            "Serviço de IA indisponível: pesos não encontrados."
        )

        response = self.client.post(
            "/ai/analyze", json={"statement": "Afirmação válida com mais de 5 caracteres."}
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("Serviço de IA indisponível", response.json()["detail"])

    def test_analyze_restrito_a_admin(self):
        """Sem override de admin, requisição sem credenciais deve retornar 401."""
        app.dependency_overrides.clear()
        client = TestClient(app)
        response = client.post(
            "/ai/analyze", json={"statement": "Afirmação válida para teste de autenticação."}
        )
        self.assertEqual(response.status_code, 401)


class TestBertimbauEngineIntegration(unittest.TestCase):
    """Teste de integração do BertimbauEngine com os arquivos de pesos reais (se disponíveis)."""

    def test_engine_load_real_artifacts_if_exist(self):
        engine = BertimbauEngine(models_dir="models", device="cpu")
        loaded = engine.load()
        if loaded:
            self.assertTrue(engine.is_available)
            res = engine.predict("Notícia de teste para validação de inferência.")
            self.assertIn("pred_y1", res)
            self.assertIn("pred_y2", res)
            self.assertIn(res["pred_y1"], [0, 1])
            self.assertIn(res["pred_y2"], [0, 1])
        else:
            # Caso os pesos não estejam presentes no path do teste, deve falhar graciosamente
            self.assertFalse(engine.is_available)
            self.assertIsNotNone(engine.error_message)


if __name__ == "__main__":
    unittest.main()
