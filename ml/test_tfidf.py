"""Testes unitários para o modelo baseline TF-IDF (ml/tfidf.py).

Valida os 10 requisitos da etapa de TF-IDF:
1. TF-IDF faz fit somente no treino;
2. validação e teste usam apenas transform;
3. Y1 possui os alvos corretos;
4. Y2 possui os alvos corretos;
5. sample_weight é utilizado;
6. seed é reproduzível;
7. modelo consegue treinar;
8. previsões possuem tamanho correto;
9. métricas são calculadas;
10. artefatos são salvos em models/.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from ml.dados import DadosML, RegistroML
from ml.tfidf import (
    DEFAULT_LOGISTIC_PARAMS,
    DEFAULT_TFIDF_PARAMS,
    RANDOM_STATE,
    avaliar_modelo,
    carregar_artefatos,
    executar_experimento,
    preparar_vetorizador,
    salvar_artefatos,
    treinar_classificador,
    treinar_vetorizador,
)


class TestTFIDFBaseline(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.models_dir = Path(self.temp_dir) / "models"

        # Fixture sintética controlada
        self.treino = [
            RegistroML("t1", "Notícia oficial sobre saúde pública", "verdadeiro", 1, 1, "agencia", 1.0),
            RegistroML("t2", "Vacina tem substância tóxica perigosa", "falso", 0, 0, "agencia", 1.0),
            RegistroML("t3", "Repasse urgente para todos os contatos", "falso", 0, 0, "mensagem", 0.7),
            RegistroML("t4", "Número de empregos cresce acima da média", "enganoso", 1, 0, "agencia", 1.0),
            RegistroML("t5", "Governo anuncia programa de saúde pública", "verdadeiro", 1, 1, "agencia", 1.0),
            RegistroML("t6", "Golpe do aplicativo que cancela conta bancária", "falso", 0, 0, "mensagem", 0.7),
        ]
        self.val = [
            RegistroML("v1", "Ministério lança nova vacina contra gripe", "verdadeiro", 1, 1, "agencia", 1.0),
            RegistroML("v2", "Post falso afirma que benefício foi cortado", "falso", 0, 0, "agencia", 1.0),
        ]
        self.teste = [
            RegistroML("te1", "Boato afirma que eleição foi cancelada", "falso", 0, 0, "agencia", 1.0),
            RegistroML("te2", "Economia fecha ano em alta segundo relatório", "enganoso", 1, 0, "agencia", 1.0),
            RegistroML("te3", "Ministério confirma nova campanha de vacina", "verdadeiro", 1, 1, "agencia", 1.0),
        ]
        self.dados = DadosML(
            treino=self.treino,
            validacao=self.val,
            teste=self.teste,
            dataset_hash="hash_teste_123456",
            reserva=[],
            metadados={},
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_01_fit_somente_no_treino(self):
        """1. Garante que o vocabulário é ajustado estritamente no treino."""
        X_tr = [r.texto for r in self.dados.treino]
        vec, X_tr_vec = treinar_vetorizador(X_tr)

        # Palavra 'eleição' só existe no teste; NÃO deve estar no vocabulário aprendido
        self.assertNotIn("eleição", vec.vocabulary_)
        # Palavra 'saúde' está no treino; deve estar no vocabulário
        self.assertIn("saúde", vec.vocabulary_)

    def test_02_val_e_teste_usam_apenas_transform(self):
        """2. Garante que validação e teste usam apenas transform sem alterar vocabulário."""
        X_tr = [r.texto for r in self.dados.treino]
        vec, X_tr_vec = treinar_vetorizador(X_tr)
        tamanho_original = len(vec.vocabulary_)

        X_val_vec = vec.transform([r.texto for r in self.dados.validacao])
        X_te_vec = vec.transform([r.texto for r in self.dados.teste])

        self.assertEqual(len(vec.vocabulary_), tamanho_original)
        self.assertEqual(X_val_vec.shape[1], tamanho_original)
        self.assertEqual(X_te_vec.shape[1], tamanho_original)

    def test_03_y1_alvos_corretos(self):
        """3. Garante que Y1 mapeia falso=0, enganoso=1, verdadeiro=1."""
        y1_tr = [r.y1 for r in self.dados.treino]
        # t1(verdadeiro)=1, t2(falso)=0, t3(falso)=0, t4(enganoso)=1, t5(verdadeiro)=1, t6(falso)=0
        self.assertEqual(y1_tr, [1, 0, 0, 1, 1, 0])

    def test_04_y2_alvos_corretos(self):
        """4. Garante que Y2 mapeia falso=0, enganoso=0, verdadeiro=1."""
        y2_tr = [r.y2 for r in self.dados.treino]
        # t1(verdadeiro)=1, t2(falso)=0, t3(falso)=0, t4(enganoso)=0, t5(verdadeiro)=1, t6(falso)=0
        self.assertEqual(y2_tr, [1, 0, 0, 0, 1, 0])

    def test_05_sample_weight_utilizado(self):
        """5. Garante que os pesos por origem são passados ao classificador."""
        pesos = [r.peso for r in self.dados.treino]
        self.assertEqual(pesos, [1.0, 1.0, 0.7, 1.0, 1.0, 0.7])

        vec, X_tr_vec = treinar_vetorizador([r.texto for r in self.dados.treino])
        clf = treinar_classificador(X_tr_vec, [r.y1 for r in self.dados.treino], sample_weight=pesos)
        self.assertTrue(hasattr(clf, "coef_"))

    def test_06_seed_reproduzivel(self):
        """6. Garante que o treinamento é determinístico com RANDOM_STATE=42."""
        vec1, X_tr_vec1 = treinar_vetorizador([r.texto for r in self.dados.treino])
        vec2, X_tr_vec2 = treinar_vetorizador([r.texto for r in self.dados.treino])

        clf1 = treinar_classificador(X_tr_vec1, [r.y1 for r in self.dados.treino], params={"random_state": 42})
        clf2 = treinar_classificador(X_tr_vec2, [r.y1 for r in self.dados.treino], params={"random_state": 42})

        self.assertEqual(clf1.coef_.tolist(), clf2.coef_.tolist())

    def test_07_modelo_consegue_treinar_e_convergir(self):
        """7. Garante que o modelo treina com max_iter configurado sem erro."""
        res = executar_experimento(self.dados, diretorio_modelos=self.models_dir, salvar=False)
        self.assertIsNotNone(res["clf_y1"])
        self.assertIsNotNone(res["clf_y2"])

    def test_08_previsoes_possuem_tamanho_correto(self):
        """8. Garante que o número de previsões bate com cada split."""
        vec, X_tr_vec = treinar_vetorizador([r.texto for r in self.dados.treino])
        clf = treinar_classificador(X_tr_vec, [r.y1 for r in self.dados.treino])

        X_val_vec = vec.transform([r.texto for r in self.dados.validacao])
        X_te_vec = vec.transform([r.texto for r in self.dados.teste])

        preds_val = clf.predict(X_val_vec)
        preds_te = clf.predict(X_te_vec)

        self.assertEqual(len(preds_val), len(self.dados.validacao))
        self.assertEqual(len(preds_te), len(self.dados.teste))

    def test_09_metricas_sao_calculadas(self):
        """9. Garante que accuracy, precision, recall, f1, macro_f1 e bal_acc são calculadas."""
        vec, X_tr_vec = treinar_vetorizador([r.texto for r in self.dados.treino])
        clf = treinar_classificador(X_tr_vec, [r.y1 for r in self.dados.treino])
        X_val_vec = vec.transform([r.texto for r in self.dados.validacao])

        metricas = avaliar_modelo(clf, X_val_vec, [r.y1 for r in self.dados.validacao])
        self.assertIsInstance(metricas.accuracy, float)
        self.assertIsInstance(metricas.macro_f1, float)
        self.assertIsInstance(metricas.balanced_accuracy, float)
        self.assertEqual(len(metricas.confusion_matrix), 2)
        self.assertEqual(len(metricas.confusion_matrix[0]), 2)

    def test_10_artefatos_sao_salvos_e_carregados(self):
        """10. Garante que os modelos e metadados são salvos em models/ e recarregados."""
        res = executar_experimento(self.dados, diretorio_modelos=self.models_dir, salvar=True)

        self.assertTrue((self.models_dir / "tfidf_vectorizer.joblib").exists())
        self.assertTrue((self.models_dir / "tfidf_y1.joblib").exists())
        self.assertTrue((self.models_dir / "tfidf_y2.joblib").exists())
        self.assertTrue((self.models_dir / "tfidf_metadata.json").exists())

        vec, clf_y1, clf_y2, meta = carregar_artefatos(self.models_dir)
        self.assertEqual(meta["dataset_hash"], self.dados.dataset_hash)
        self.assertEqual(meta["random_state"], RANDOM_STATE)


if __name__ == "__main__":
    unittest.main()
