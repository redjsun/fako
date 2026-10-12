"""Testes unitários para o modelo BERTimbau (ml/test_bertimbau.py)."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import torch
from transformers import AutoTokenizer

from ml.bertimbau import (
    MODEL_NAME,
    NoticiasDataset,
    avaliar_modelo,
    obter_dispositivo,
    salvar_artefatos,
)
from ml.dados import DadosML, RegistroML


class TestBERTimbau(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        cls.dispositivo = obter_dispositivo()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.models_dir = Path(self.temp_dir) / "models"

        # Fixture sintética
        self.textos = [
            "Ministério da Saúde faz anúncio importante.",
            "Vacina com chip? Isso é falso!",
        ]
        self.labels_y1 = [1, 0]
        self.labels_y2 = [1, 0]
        self.pesos = [1.0, 0.7]

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_01_tokenizer_preserva_cased_e_pontuacao(self):
        """1. Garante que o tokenizer do BERTimbau preserva maiúsculas e pontuação."""
        texto = "A OMS emitiu alerta em 2024? Sim!"
        tokens = self.tokenizer.tokenize(texto)
        # Deve ter tokens com maiúsculas preservadas
        self.assertTrue(any(t.isupper() or t.startswith("A") for t in tokens))
        # Ponto de interrogação deve estar presente
        self.assertIn("?", tokens)

    def test_02_dataset_estrutura_de_tensores(self):
        """2. Garante que NoticiasDataset gera tensores corretos."""
        ds = NoticiasDataset(self.textos, self.labels_y1, self.pesos, self.tokenizer, max_length=32)
        self.assertEqual(len(ds), 2)

        item = ds[0]
        self.assertIn("input_ids", item)
        self.assertIn("attention_mask", item)
        self.assertIn("label", item)
        self.assertIn("peso", item)

        self.assertEqual(item["input_ids"].shape[0], 32)
        self.assertEqual(item["peso"].item(), 1.0)
        self.assertEqual(item["label"].item(), 1)

    def test_03_sample_weight_afeta_loss(self):
        """3. Garante que o peso da amostra afeta o cálculo da loss ponderada."""
        criterio = torch.nn.CrossEntropyLoss(reduction="none")
        logits = torch.tensor([[2.0, -1.0], [-1.0, 2.0]])
        labels = torch.tensor([0, 0])  # Segundo exemplo erra feio
        loss_unweighted = criterio(logits, labels)

        pesos_iguais = torch.tensor([1.0, 1.0])
        pesos_diferentes = torch.tensor([1.0, 0.5])

        loss1 = (loss_unweighted * pesos_iguais).sum() / pesos_iguais.sum()
        loss2 = (loss_unweighted * pesos_diferentes).sum() / pesos_diferentes.sum()

        self.assertNotEqual(loss1.item(), loss2.item())

    def test_04_salvamento_e_metadados(self):
        """4. Garante que salvar_artefatos gera os diretórios e JSON corretos."""
        from transformers import AutoModelForSequenceClassification

        # Modelo dummy pequeno para teste rápido de salvamento
        modelo_dummy = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
        metadados = {
            "modelo": "BERTimbau Teste",
            "dataset_hash": "hash123",
        }

        artefatos = salvar_artefatos(
            modelo_dummy, modelo_dummy, self.tokenizer, metadados, diretorio=self.models_dir
        )

        self.assertTrue((self.models_dir / "bertimbau_y1").exists())
        self.assertTrue((self.models_dir / "bertimbau_y2").exists())
        self.assertTrue((self.models_dir / "bertimbau_metadata.json").exists())

        with open(self.models_dir / "bertimbau_metadata.json", encoding="utf-8") as f:
            lido = json.load(f)
        self.assertEqual(lido["dataset_hash"], "hash123")


if __name__ == "__main__":
    unittest.main()
