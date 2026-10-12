"""Dados iniciais do MVP: categorias, níveis e questões de exemplo já validadas."""

CATEGORIES = [
    {"name": "Saúde", "slug": "saude"},
    {"name": "Tecnologia", "slug": "tecnologia"},
    {"name": "Conhecimentos Gerais", "slug": "conhecimentos-gerais"},
]

# Níveis 1–3 em 7×7, níveis 4–6 em 6×6; a cobra acelera a cada nível.
LEVELS = [
    {"number": 1, "board_size": 7, "tick_ms": 400, "min_score_to_advance": 30},
    {"number": 2, "board_size": 7, "tick_ms": 350, "min_score_to_advance": 40},
    {"number": 3, "board_size": 7, "tick_ms": 300, "min_score_to_advance": 50},
    {"number": 4, "board_size": 6, "tick_ms": 300, "min_score_to_advance": 50},
    {"number": 5, "board_size": 6, "tick_ms": 250, "min_score_to_advance": 60},
    {"number": 6, "board_size": 6, "tick_ms": 200, "min_score_to_advance": 70},
]

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
