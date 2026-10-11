"""Testes de validação do pipeline de dados de ML (ml/dados.py).

Valida os 14 requisitos especificados na etapa 1:
1. dataset é carregado;
2. registros sem texto são removidos;
3. URLs são removidas;
4. assinaturas/veículos são tratados conforme as regras;
5. maiúsculas são preservadas;
6. pontuação é preservada;
7. y1 está correto;
8. y2 está correto;
9. pesos estão corretos;
10. portal não aparece nos splits;
11. reserva não aparece nos splits;
12. treino/validação/teste são reproduzíveis;
13. hash é gerado;
14. o mesmo pipeline pode ser utilizado posteriormente pelos dois modelos.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ml.dados import (
    CLASSES_VERACIDADE,
    MAPA_Y1,
    MAPA_Y2,
    PESOS_ORIGEM,
    carregar,
    limpar_texto,
)


class TestPipelineDadosML(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.caminho_dir = Path(self.temp_dir)
        self.caminho_dataset = self.caminho_dir / "dataset_teste.jsonl"
        self.caminho_anotacoes = self.caminho_dir / "anotacoes"
        self.caminho_cache = self.caminho_dir / "cache"

        self.caminho_anotacoes.mkdir(parents=True, exist_ok=True)
        self.caminho_cache.mkdir(parents=True, exist_ok=True)

        # Base sintética com múltiplos casos de teste
        self.registros_teste = [
            # 1 & 14: Carregamento padrão
            {
                "id": "item-1",
                "base": "factcheck",
                "texto_curto": "Ministério anuncia novo programa de saúde pública.",
                "veracidade": "verdadeiro",
                "origem_rotulo": "agencia",
                "split_produto": "treino",
            },
            # 2: Registro sem texto_curto (deve ser descartado)
            {
                "id": "item-2-sem-texto",
                "base": "fakebr",
                "texto_curto": None,
                "texto": "Texto longo presente mas sem texto_curto.",
                "veracidade": "falso",
                "origem_rotulo": "curadoria",
                "split_produto": "treino",
            },
            # 2b: Registro com texto_curto vazio (deve ser descartado)
            {
                "id": "item-2b-vazio",
                "base": "fakebr",
                "texto_curto": "   ",
                "veracidade": "falso",
                "origem_rotulo": "curadoria",
                "split_produto": "treino",
            },
            # 3, 4, 5, 6: URLs, assinaturas, veículos, maiúsculas e pontuação
            {
                "id": "item-3-limpeza",
                "base": "fakerecogna",
                "texto_curto": "Boato – Post afirma que vacina altera DNA! Confira em https://t.co/xyz123 | G1",
                "veracidade": "falso",
                "origem_rotulo": "agencia",
                "split_produto": "validacao",
            },
            # 7 & 8: Enganoso (y1=1, y2=0)
            {
                "id": "item-4-enganoso",
                "base": "factcheck",
                "texto_curto": "Número de empregos gerados em 2024 foi o maior da história.",
                "veracidade": "enganoso",
                "origem_rotulo": "agencia",
                "split_produto": "teste",
            },
            # 9: Pesos por origem (mensagem com peso 0.7)
            {
                "id": "item-5-mensagem",
                "base": "fakenewsbr",
                "texto_curto": "URGENTE: repasse esta mensagem antes de meia-noite!",
                "veracidade": "falso",
                "origem_rotulo": "mensagem",
                "split_produto": "treino",
            },
            # 10: Origem portal (NÃO deve entrar nos splits)
            {
                "id": "item-6-portal",
                "base": "verdadeiras",
                "texto_curto": "Inflação fica em 0.4% no mês de setembro segundo IBGE.",
                "veracidade": "verdadeiro",
                "origem_rotulo": "portal",
                "split_produto": "treino",
            },
            # 11: Registro marcado como reserva (NÃO deve entrar nos splits de treino/val/teste)
            {
                "id": "item-7-reserva",
                "base": "factcheck",
                "texto_curto": "Alegação descartada para balanceamento de classes.",
                "veracidade": "verdadeiro",
                "origem_rotulo": "agencia",
                "split_produto": "reserva",
            },
            # Item com anotação para teste de sobreposição
            {
                "id": "item-8-anotado",
                "base": "factcheck",
                "texto_curto": "Declaração de político sobre gastos públicos.",
                "veracidade": "falso",
                "origem_rotulo": "agencia",
                "split_produto": "treino",
            },
        ]

        with open(self.caminho_dataset, "w", encoding="utf-8") as f:
            for r in self.registros_teste:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        # Anotação externa que revisa item-8
        anotacao = {
            "id": "item-8-anotado",
            "veracidade": "enganoso",
            "tipo": "falso_contexto",
            "anotador": "revisor_1",
        }
        with open(self.caminho_anotacoes / "anotacoes.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps(anotacao) + "\n")

        # Cache de padronização para item-1
        cache_item1 = {
            "texto_padronizado": "Ministério anuncia oficialmente novo programa de saúde pública."
        }
        with open(self.caminho_cache / "item-1__v1.json", "w", encoding="utf-8") as f:
            json.dump(cache_item1, f)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_01_dataset_carregado(self):
        """1. Garante que o dataset é lido corretamente."""
        dados = carregar(
            caminho_dataset=self.caminho_dataset,
            caminho_anotacoes=self.caminho_anotacoes,
        )
        self.assertGreater(dados.total_ativos(), 0)
        self.assertIsNotNone(dados.dataset_hash)

    def test_02_registros_sem_texto_removidos(self):
        """2. Garante que registros sem texto_curto são descartados dos splits."""
        dados = carregar(
            caminho_dataset=self.caminho_dataset,
            caminho_anotacoes=self.caminho_anotacoes,
        )
        todos_ids = [r.id for r in dados.treino + dados.validacao + dados.teste + dados.reserva]
        self.assertNotIn("item-2-sem-texto", todos_ids)
        self.assertNotIn("item-2b-vazio", todos_ids)
        self.assertEqual(dados.metadados["descartados_sem_texto"], 2)

    def test_03_urls_removidas(self):
        """3. Garante que URLs http/https/www são removidas do texto."""
        texto_limpo = limpar_texto("Veja em https://exemplo.com/noticia e www.portal.com/teste aqui!")
        self.assertNotIn("https://", texto_limpo)
        self.assertNotIn("www.portal.com", texto_limpo)
        self.assertEqual(texto_limpo, "Veja em e aqui!")

    def test_04_assinaturas_e_veiculos_removidos(self):
        """4. Garante que prefixos de veículos, sufixos e assinaturas são removidos."""
        t1 = limpar_texto("Boato – Afirmação que circula | Boatos.org")
        self.assertEqual(t1, "Afirmação que circula")

        t2 = limpar_texto("FATO OU FAKE: Nova taxa entra em vigor na segunda-feira | G1")
        self.assertEqual(t2, "Nova taxa entra em vigor na segunda-feira")

        t3 = limpar_texto("Projeto aprovado pelo congresso - Por João Silveira")
        self.assertEqual(t3, "Projeto aprovado pelo congresso")

        t4 = limpar_texto("Foto: Agência Brasil. Notícia oficial sobre economia")
        self.assertEqual(t4, "Notícia oficial sobre economia")

        # Garante que NÃO apaga conteúdo jornalístico legítimo com a preposição "por"
        t5_legitimo = limpar_texto("Inquérito foi aberto por Alexandre de Moraes")
        self.assertEqual(t5_legitimo, "Inquérito foi aberto por Alexandre de Moraes")

    def test_05_maiusculas_preservadas(self):
        """5. Garante que NÃO aplica .lower() e que maiúsculas são preservadas."""
        original = "A OMS declarou Emergência Global em Saúde Pública."
        limpo = limpar_texto(original)
        self.assertEqual(limpo, original)
        self.assertTrue(any(c.isupper() for c in limpo))

    def test_06_pontuacao_preservada(self):
        """6. Garante que pontuação não é removida sem necessidade."""
        original = "Isso realmente aconteceu? Não, é mentira!"
        limpo = limpar_texto(original)
        self.assertIn("?", limpo)
        self.assertIn("!", limpo)
        self.assertIn(",", limpo)
        self.assertEqual(limpo, original)

    def test_07_y1_correto(self):
        """7. Garante o mapeamento de y1 (É mais do que falso? falso->0, enganoso->1, verdadeiro->1)."""
        dados = carregar(
            caminho_dataset=self.caminho_dataset,
            caminho_anotacoes=self.caminho_anotacoes,
        )
        mapa = {r.id: r for r in dados.treino + dados.validacao + dados.teste}
        # item-3-limpeza é falso -> y1=0
        self.assertEqual(mapa["item-3-limpeza"].veracidade, "falso")
        self.assertEqual(mapa["item-3-limpeza"].y1, 0)

        # item-4-enganoso é enganoso -> y1=1
        self.assertEqual(mapa["item-4-enganoso"].veracidade, "enganoso")
        self.assertEqual(mapa["item-4-enganoso"].y1, 1)

        # item-1 é verdadeiro -> y1=1
        self.assertEqual(mapa["item-1"].veracidade, "verdadeiro")
        self.assertEqual(mapa["item-1"].y1, 1)

    def test_08_y2_correto(self):
        """8. Garante o mapeamento de y2 (É verdadeiro? falso->0, enganoso->0, verdadeiro->1)."""
        dados = carregar(
            caminho_dataset=self.caminho_dataset,
            caminho_anotacoes=self.caminho_anotacoes,
        )
        mapa = {r.id: r for r in dados.treino + dados.validacao + dados.teste}
        # item-3-limpeza é falso -> y2=0
        self.assertEqual(mapa["item-3-limpeza"].y2, 0)

        # item-4-enganoso é enganoso -> y2=0
        self.assertEqual(mapa["item-4-enganoso"].y2, 0)

        # item-1 é verdadeiro -> y2=1
        self.assertEqual(mapa["item-1"].y2, 1)

    def test_09_pesos_por_origem(self):
        """9. Garante que os pesos por origem estão corretos (agencia 1.0, mensagem 0.7, etc.)."""
        dados = carregar(
            caminho_dataset=self.caminho_dataset,
            caminho_anotacoes=self.caminho_anotacoes,
        )
        mapa = {r.id: r for r in dados.treino + dados.validacao + dados.teste}
        self.assertEqual(mapa["item-1"].peso, 1.0)
        self.assertEqual(mapa["item-5-mensagem"].peso, 0.7)

    def test_10_portal_nao_aparece_nos_splits(self):
        """10. Garante que registros com origem portal são excluídos de todos os splits de ML."""
        dados = carregar(
            caminho_dataset=self.caminho_dataset,
            caminho_anotacoes=self.caminho_anotacoes,
        )
        todos_ativos = dados.treino + dados.validacao + dados.teste
        self.assertNotIn("item-6-portal", [r.id for r in todos_ativos])
        self.assertEqual(dados.metadados["descartados_portal"], 1)

    def test_11_reserva_nao_aparece_nos_splits(self):
        """11. Garante que registros em reserva não entram em treino, validação ou teste."""
        dados = carregar(
            caminho_dataset=self.caminho_dataset,
            caminho_anotacoes=self.caminho_anotacoes,
        )
        splits_principais = dados.treino + dados.validacao + dados.teste
        self.assertNotIn("item-7-reserva", [r.id for r in splits_principais])
        self.assertIn("item-7-reserva", [r.id for r in dados.reserva])

    def test_12_splits_reproduziveis(self):
        """12. Garante que múltiplas chamadas geram exatamente a mesma divisão."""
        d1 = carregar(
            caminho_dataset=self.caminho_dataset,
            caminho_anotacoes=self.caminho_anotacoes,
            seed=42,
        )
        d2 = carregar(
            caminho_dataset=self.caminho_dataset,
            caminho_anotacoes=self.caminho_anotacoes,
            seed=42,
        )
        self.assertEqual([r.id for r in d1.treino], [r.id for r in d2.treino])
        self.assertEqual([r.id for r in d1.validacao], [r.id for r in d2.validacao])
        self.assertEqual([r.id for r in d1.teste], [r.id for r in d2.teste])
        self.assertEqual(d1.dataset_hash, d2.dataset_hash)

        # Garante ausência total de sobreposição de IDs entre os três conjuntos
        ids_treino = set(r.id for r in d1.treino)
        ids_validacao = set(r.id for r in d1.validacao)
        ids_teste = set(r.id for r in d1.teste)
        self.assertEqual(ids_treino & ids_validacao, set())
        self.assertEqual(ids_treino & ids_teste, set())
        self.assertEqual(ids_validacao & ids_teste, set())

    def test_13_dataset_hash_gerado(self):
        """13. Garante que o hash do dataset é uma string SHA-256 válida e consistente."""
        dados = carregar(
            caminho_dataset=self.caminho_dataset,
            caminho_anotacoes=self.caminho_anotacoes,
        )
        self.assertTrue(isinstance(dados.dataset_hash, str))
        self.assertEqual(len(dados.dataset_hash), 64)

    def test_14_pipeline_unificado_texto_original_e_padronizado(self):
        """14. Garante suporte unificado para texto original e padronizado via cache."""
        dados_orig = carregar(
            texto="original",
            caminho_dataset=self.caminho_dataset,
            caminho_anotacoes=self.caminho_anotacoes,
            caminho_cache=self.caminho_cache,
        )
        dados_padr = carregar(
            texto="padronizado",
            versao_prompt="v1",
            caminho_dataset=self.caminho_dataset,
            caminho_anotacoes=self.caminho_anotacoes,
            caminho_cache=self.caminho_cache,
        )

        mapa_orig = {r.id: r for r in dados_orig.treino}
        mapa_padr = {r.id: r for r in dados_padr.treino}

        self.assertEqual(
            mapa_orig["item-1"].texto,
            "Ministério anuncia novo programa de saúde pública.",
        )
        self.assertEqual(
            mapa_padr["item-1"].texto,
            "Ministério anuncia oficialmente novo programa de saúde pública.",
        )


if __name__ == "__main__":
    unittest.main()
