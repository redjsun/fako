import pytest

from app.ml.normalizacao import limpar, motivo_descarte, normalizar_autor, normalizar_manchete

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
        ("O que muda com a nova regra do Pix?", "https://x.com/a", "pergunta ou explicativa"),
        ("Ministro diz que inflação vai cair este ano", "https://x.com/a", "relata fala"),
        ("Reforma avança na Câmara dos Deputados hoje", "https://x.com/opiniao/a", FORA),
        ("Vídeo: veja o momento em que o foguete decola", "https://x.com/a", FORA),
    ],
)
def test_filtros_de_manchete(manchete, url, motivo):
    assert motivo_descarte(manchete, url) == motivo


@pytest.mark.parametrize(
    "alegacao, motivo",
    [
        ("Foto mostra eleitores com tornozeleira eletrônica", "depende de imagem, vídeo ou áudio"),
        (
            "Cantor mostra áudio sobre o fim do feriado nacional",
            "depende de imagem, vídeo ou áudio",
        ),
        ("Anúncio de corte no Pé-de-Meia é 'deepfake'", "traz a conclusão da checagem"),
        ("Remédio caseiro que cura a dengue é falso", "traz a conclusão da checagem"),
        ("Eu tenho um irmão exilado nos Estados Unidos", "fala ou trecho recortado"),
        ("Recorde de empresas fechadas [em 2026] no país", "fala ou trecho recortado"),
        ("Vacina contra a gripe contém chip de rastreamento", None),
        ("Médico diz que chá de boldo cura a covid?", None),  # pergunta e fala ficam no boato
    ],
)
def test_filtros_das_alegacoes_checadas(alegacao, motivo):
    assert motivo_descarte(alegacao, checagem=True) == motivo


def test_filtro_de_politica_so_quando_pedido():
    for alegacao in ("PCC e CV declararam apoio a Lula no segundo turno", "PT vai taxar o Pix"):
        assert motivo_descarte(alegacao, checagem=True) is None
        assert motivo_descarte(alegacao, checagem=True, sem_politica=True) == "política ou eleição"
    assert (
        motivo_descarte("Água com limão em jejum cura o câncer", checagem=True, sem_politica=True)
        is None
    )


@pytest.mark.parametrize(
    "manchete",
    [
        "Palmeiras x Corinthians: horário e onde assistir ao clássico do Brasileirão",
        "Mega-Sena 3069 pode pagar R$ 112 milhões neste domingo; g1 transmite",
        "Confira os documentos necessários para tirar o novo RG",
    ],
)
def test_manchete_de_servico_sai(manchete):
    assert motivo_descarte(manchete) == "serviço"


@pytest.mark.parametrize(
    "manchete",
    [
        "Por que espremer cravos dá tanto prazer? A ciência explica o fenômeno",
        "Fim da hemodiálise? Cientistas descobrem como regenerar rins danificados",
        "O que se sabe sobre o caso do jovem morto em São Paulo",
        "Você não inveja o bilionário, mas se incomoda com a promoção do colega: entenda",
    ],
)
def test_manchete_explicativa_sai(manchete):
    assert motivo_descarte(manchete) == "pergunta ou explicativa"


@pytest.mark.parametrize(
    "bruto, autor",
    [
        ("Boato de internet", "redes sociais"),
        ('"Boato de internet"', "redes sociais"),
        ("Várias fontes", "redes sociais"),
        ("[site:name]", "redes sociais"),
        ("Imagem viral", "redes sociais"),
        ("Posts no Facebook", "Facebook"),
        ("Usuários do WhatsApp", "WhatsApp"),
        ("Postagens no X", "X (Twitter)"),
        ("X", "X (Twitter)"),
        ("Jair Bolsonaro", "Jair Bolsonaro"),
        ("Jornal da Cidade Online", "Jornal da Cidade Online"),
        ("", None),
        (None, None),
    ],
)
def test_normalizar_autor(bruto, autor):
    assert normalizar_autor(bruto) == autor
