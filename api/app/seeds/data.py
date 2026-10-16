"""Dados iniciais do MVP: categorias, níveis e questões de exemplo já validadas."""

CATEGORIES = [
    {"name": "Saúde", "slug": "saude"},
    {"name": "Tecnologia", "slug": "tecnologia"},
    {"name": "Conhecimentos Gerais", "slug": "conhecimentos-gerais"},
]

# Regras de cada nível (doc/jogo/niveis.md). A dificuldade cresce pela mecânica, não pelas
# afirmações: tabuleiro menor, cobra mais rápida, menos tempo, menos tolerância, erro mais
# caro, paredes sólidas e maçãs que somem ou estragam.
_LEVEL_COLUMNS = (
    "number",
    "board_size",
    "tick_ms",
    "min_score_to_advance",
    "match_seconds",
    "question_seconds",
    "reliability_tolerance",
    "wrong_answer_penalty",
    "growth_per_error",
    "solid_walls",
    "apple_lifetime_seconds",
    "rotten_apples",
)
_LEVEL_ROWS = [
    (1, 16, 160, 30, 120, 45, 15, 0, 1, False, None, 0),
    (2, 16, 145, 40, 120, 40, 15, 0, 1, False, None, 0),
    (3, 14, 130, 50, 110, 35, 12, 0, 2, False, None, 0),
    (4, 14, 125, 50, 100, 30, 10, 5, 2, True, 12, 0),
    (5, 12, 115, 60, 90, 25, 10, 5, 2, True, 10, 2),
    (6, 12, 105, 70, 90, 20, 8, 10, 3, True, 8, 4),
]
LEVELS = [dict(zip(_LEVEL_COLUMNS, row, strict=True)) for row in _LEVEL_ROWS]

QUESTIONS = [
    {
        "category": "saude",
        "statement": "Vacinas causam autismo.",
        "is_true": False,
        "reliability_reference": 5,
        "explanation": (
            "O estudo de 1998 que sugeriu essa relação foi retratado por fraude, e "
            "pesquisas com milhões de crianças não encontraram ligação entre vacinas e autismo."
        ),
        "source": "Organização Mundial da Saúde (OMS)",
    },
    {
        "category": "saude",
        "statement": "Lavar as mãos com água e sabão reduz a transmissão de doenças infecciosas.",
        "is_true": True,
        "reliability_reference": 95,
        "explanation": (
            "A higiene das mãos remove microrganismos e é uma das medidas mais eficazes "
            "para prevenir infecções."
        ),
        "source": "Organização Mundial da Saúde (OMS)",
    },
    {
        "category": "tecnologia",
        "statement": "O modo anônimo do navegador impede que o provedor de internet veja os sites acessados.",
        "is_true": False,
        "reliability_reference": 10,
        "explanation": (
            "O modo anônimo apenas não salva histórico e cookies no aparelho; o provedor, "
            "a rede da escola ou do trabalho e os próprios sites ainda podem ver o acesso."
        ),
        "source": "Central de Ajuda do Google Chrome",
    },
    {
        "category": "tecnologia",
        "statement": "Senhas longas são mais difíceis de descobrir por tentativa e erro do que senhas curtas.",
        "is_true": True,
        "reliability_reference": 90,
        "explanation": (
            "Cada caractere a mais multiplica o número de combinações possíveis, por isso o "
            "comprimento é um dos fatores mais importantes de uma senha forte."
        ),
        "source": "NIST SP 800-63B — Digital Identity Guidelines",
    },
    {
        "category": "conhecimentos-gerais",
        "statement": "A Grande Muralha da China pode ser vista a olho nu da Lua.",
        "is_true": False,
        "reliability_reference": 5,
        "explanation": (
            "A muralha é longa, mas estreita demais para ser vista da Lua; nem da órbita "
            "baixa da Terra ela é facilmente visível sem auxílio."
        ),
        "source": "NASA",
    },
    {
        "category": "conhecimentos-gerais",
        "statement": "O Brasil é o maior país da América do Sul em área territorial.",
        "is_true": True,
        "reliability_reference": 100,
        "explanation": (
            "Com cerca de 8,5 milhões de km², o Brasil ocupa quase metade do território "
            "da América do Sul."
        ),
        "source": "IBGE",
    },
]
