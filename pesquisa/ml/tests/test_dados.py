import json

import pytest

from dados import ORIGEM_ROTULO_PESO, alvos, carregar, limpar, sha256
from padronizar import Prompt, caminho_cache


@pytest.mark.parametrize(
    "bruto, limpo",
    [
        ("Governo anuncia novo programa | G1", "Governo anuncia novo programa"),
        ("Inflação sobe 0,5% em março - Folha", "Inflação sobe 0,5% em março"),
        ("Vacina chega ao país (Estadão Conteúdo)", "Vacina chega ao país"),
        ("Chuva atinge SP. Com informações da Agência Brasil.", "Chuva atinge SP."),
        ("(Reuters) - Bolsa fecha em alta", "Bolsa fecha em alta"),
        ("Veja o vídeo: https://t.co/abc VACINA mata!", "Veja o vídeo: VACINA mata!"),
        ("Veja: vídeo mostra fraude na urna", "Veja: vídeo mostra fraude na urna"),
        ("É FALSO que a Terra é plana?!", "É FALSO que a Terra é plana?!"),
        ("Folha diz que ministro caiu", "Folha diz que ministro caiu"),
    ],
)
def test_limpar_tira_url_e_credito_e_mantem_caixa_e_pontuacao(bruto, limpo):
    assert limpar(bruto) == limpo


@pytest.mark.parametrize(
    "veracidade, esperado", [("falso", (0, 0)), ("enganoso", (1, 0)), ("verdadeiro", (1, 1))]
)
def test_alvos_ordinais(veracidade, esperado):
    assert alvos(veracidade) == esperado


def test_pesos_sem_portal_e_com_as_origens_novas():
    assert "portal" not in ORIGEM_ROTULO_PESO
    assert ORIGEM_ROTULO_PESO["mensagem"] == 0.7
    for origem in ("agencia", "curadoria", "equipe", "jogo", "portal_verificado"):
        assert ORIGEM_ROTULO_PESO[origem] == 1.0


def registro(
    id_, split="treino", veracidade="falso", origem="agencia", curto="Texto curto", **extra
):
    return {
        "id": id_,
        "split_produto": split,
        "veracidade": veracidade,
        "origem_rotulo": origem,
        "texto_curto": curto,
        "texto": "texto longo",
        "base": "factcheck",
        "fonte": "lupa.uol.com.br",
        "data": "2022-05-01",
        "tipo_sugerido": "fabricado",
        "veredito_original": "falso" if origem == "agencia" else None,
        **extra,
    }


@pytest.fixture
def dataset(tmp_path):
    registros = [
        registro("a"),
        registro("b", "validacao", "enganoso"),
        registro("c", "teste", "verdadeiro", "curadoria"),
        registro("d", origem="portal", veracidade="verdadeiro"),
        registro("e", "reserva"),
        registro("f", "fora"),
        registro("g", curto=None),
        registro("h", veracidade="verdadeiro", origem="mensagem", data=None),
    ]
    caminho = tmp_path / "dataset.jsonl"
    caminho.write_text("".join(json.dumps(r) + "\n" for r in registros), encoding="utf-8")
    return caminho


def ids(conjunto):
    return {s: [e.id for e in ex] for s, ex in conjunto.splits.items()}


def test_carregar_filtra_splits_portal_e_sem_texto_curto(dataset, tmp_path):
    conjunto = carregar(dataset=dataset, anotacoes=tmp_path / "nao-existe.csv")
    assert ids(conjunto) == {"treino": ["a", "h"], "validacao": ["b"], "teste": ["c"]}
    assert conjunto.dataset_sha256 == sha256(dataset)
    assert conjunto.contagens()["treino"] == {"falso": 1, "verdadeiro": 1}


def test_carregar_preenche_alvos_pesos_e_checado(dataset, tmp_path):
    conjunto = carregar(dataset=dataset, anotacoes=tmp_path / "nao-existe.csv")
    a, h = conjunto.splits["treino"]
    assert (a.y1, a.y2, a.peso, a.checado, a.ano) == (0, 0, 1.0, True, 2022)
    assert (h.y1, h.y2, h.peso, h.checado, h.ano) == (1, 1, 0.7, False, None)
    (c,) = conjunto.splits["teste"]
    assert c.checado is False and c.tipo is None and c.tipo_sugerido == "fabricado"


def test_incluir_portal_so_para_diagnostico(dataset, tmp_path):
    conjunto = carregar(dataset=dataset, anotacoes=tmp_path / "x.csv", incluir_portal=True)
    assert "d" in ids(conjunto)["treino"]


def test_anotacao_da_equipe_substitui_rotulo_e_origem(dataset, tmp_path):
    anotacoes = tmp_path / "consolidado.csv"
    anotacoes.write_text("id,tipo,veracidade\na,enganoso,enganoso\n", encoding="utf-8")
    (a, _) = carregar(dataset=dataset, anotacoes=anotacoes).splits["treino"]
    assert (a.tipo, a.veracidade, a.origem_rotulo, a.y1, a.peso) == (
        "enganoso",
        "enganoso",
        "equipe",
        1,
        1.0,
    )


def test_carregar_padronizado_usa_o_cache_do_prompt_e_modelo(dataset, tmp_path):
    prompt_arquivo = tmp_path / "extrair_afirmacoes_v1.txt"
    prompt_arquivo.write_text("Extraia: {texto}", encoding="utf-8")
    prompt = Prompt("v1", "Extraia: {texto}")
    linhas = [
        {"id": "a", "afirmacoes": [{"texto": "Afirmação de a | G1", "quem_disse": None}]},
        {"id": "g", "afirmacoes": [{"texto": "Extraída do texto longo", "quem_disse": "X"}]},
        {"id": "h", "afirmacoes": []},  # opinião: sai
    ]
    cache = caminho_cache("v1", dataset.parent)
    cache.write_text(
        "".join(
            json.dumps({**linha, "versao": "v1", "prompt_sha1": prompt.sha1, "modelo": "qwen-x"})
            + "\n"
            for linha in linhas
        ),
        encoding="utf-8",
    )
    conjunto = carregar(
        "padronizado", dataset, prompt_arquivo, "qwen-x", anotacoes=tmp_path / "x.csv"
    )
    assert [(e.id, e.texto) for e in conjunto.splits["treino"]] == [
        ("a", "Afirmação de a"),
        ("g", "Extraída do texto longo"),
    ]
    assert conjunto.prompt == {"versao": "v1", "sha1": prompt.sha1, "modelo": "qwen-x"}
    outro_modelo = carregar(
        "padronizado", dataset, prompt_arquivo, "qwen-y", anotacoes=tmp_path / "x.csv"
    )
    assert not any(outro_modelo.splits.values())


def test_padronizado_exige_prompt_e_modelo(dataset):
    with pytest.raises(ValueError):
        carregar("padronizado", dataset)
