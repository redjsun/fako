import pytest

from app.integrations.normalizacao import limpar, motivo_descarte, normalizar_manchete

FORA = "opinião, vídeo, ao vivo ou publicidade"


@pytest.mark.parametrize(
    "bruto, limpo",
    [
        ("Governo anuncia novo programa | G1", "Governo anuncia novo programa"),
        ("(Reuters) - Bolsa fecha em alta", "Bolsa fecha em alta"),
        ("Chuva atinge o Sul. Com informações da Agência Brasil", "Chuva atinge o Sul."),
        ("Veja: vídeo mostra enchente", "Veja: vídeo mostra enchente"),
        ("Leia em https://exemplo.com/x agora", "Leia em agora"),
    ],
)
def test_limpar_igual_ao_treino(bruto, limpo):
    assert limpar(bruto) == limpo


def test_manchete_perde_veiculo_do_agregador_e_entidades():
    titulo = "Prefeitura abre 500 vagas em creches &amp; escolas - Diário do Litoral"
    assert (
        normalizar_manchete(titulo, "Diário do Litoral")
        == "Prefeitura abre 500 vagas em creches & escolas"
    )


@pytest.mark.parametrize(
    "manchete, url, motivo",
    [
        ("Prefeitura abre 500 vagas em creches", "https://x.com/a", None),
        ("Curto demais", "https://x.com/a", "tamanho"),
        ("Ao vivo: acompanhe a votação no Senado", "https://x.com/a", FORA),
        ("O que muda com a nova regra do Pix?", "https://x.com/a", "pergunta"),
        ("Ministro diz que inflação vai cair este ano", "https://x.com/a", "relata fala"),
        ("Reforma avança na Câmara dos Deputados hoje", "https://x.com/opiniao/a", FORA),
        ("Vídeo: veja o momento em que o foguete decola", "https://x.com/a", FORA),
    ],
)
def test_filtros_de_manchete(manchete, url, motivo):
    assert motivo_descarte(manchete, url) == motivo
