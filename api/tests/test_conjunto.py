import json

import pytest

from app.ml.classificador import ConjuntoBert


class Membro:
    def __init__(self, texto_de_entrada, fronteiras):
        self.texto_de_entrada = texto_de_entrada
        self._fronteiras = fronteiras
        self.recebidos = []

    def fronteiras(self, texto):
        self.recebidos.append(texto)
        return self._fronteiras


def conjunto(original, hibrido, limiares=None):
    modelo = ConjuntoBert.__new__(ConjuntoBert)
    modelo.membros = [(original, 0.5), (hibrido, 0.5)]
    modelo.limiares = limiares or {"admin": 0.5, "jogador": 0.6}
    modelo.versao = "conjunto-teste"
    return modelo


def test_cada_membro_recebe_o_seu_texto_e_a_media_decide():
    original = Membro("original", (0.9, 0.8))
    hibrido = Membro("hibrido", (0.7, 0.4))
    modelo = conjunto(original, hibrido)
    analise = modelo.analisar("Afirmação extraída", "admin", enunciado="Manchete como foi lida")
    assert original.recebidos == ["Manchete como foi lida"]
    assert hibrido.recebidos == ["Afirmação extraída"]
    assert analise.probabilidades["verdadeiro"] == pytest.approx(0.6)
    assert analise.probabilidades["falso"] == pytest.approx(0.2)
    assert analise.categoria == "confere" and analise.versao_modelo == "conjunto-teste"


def test_sem_enunciado_os_dois_recebem_a_afirmacao_e_limiar_do_jogador_vale():
    original = Membro("original", (0.6, 0.5))
    hibrido = Membro("hibrido", (0.4, 0.3))
    modelo = conjunto(original, hibrido)
    analise = modelo.analisar("Texto do admin", "jogador")
    assert original.recebidos == hibrido.recebidos == ["Texto do admin"]
    assert analise.categoria == "incerto"  # confiança 0,5, abaixo do limiar 0,6 do jogador


def test_carrega_membros_e_limiares_do_conjunto_json(tmp_path, monkeypatch):
    (tmp_path / "conjunto.json").write_text(
        json.dumps(
            {
                "versao": "conjunto-2026-10-15",
                "membros": [{"pasta": "original", "peso": 1}, {"pasta": "hibrido", "peso": 1}],
                "limiares": {"jogador": 0.55},
            }
        )
    )
    monkeypatch.setattr(
        "app.ml.classificador.BertOnnx", lambda pasta: Membro(pasta.name, (0.5, 0.5))
    )
    modelo = ConjuntoBert(tmp_path)
    assert [m.texto_de_entrada for m, _ in modelo.membros] == ["original", "hibrido"]
    assert modelo.limiares["jogador"] == 0.55 and modelo.limiares["admin"] == 0.5
    assert modelo.versao == "conjunto-2026-10-15"
