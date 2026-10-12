"""Padroniza o texto curto do treino com o mesmo prompt de extração do uso (issue #20).

Uso:
    python pesquisa/ml/padronizar.py --prompt api/app/prompts/extrair_afirmacoes_v1.txt
    python pesquisa/ml/padronizar.py --prompt ... --limite 50     # amostra, para medir tempo e custo
    python pesquisa/ml/padronizar.py --prompt ... --splits todos  # inclui reserva e fora

Em uso, o classificador recebe afirmações extraídas pela LLM; no treino, recebia o
`texto_curto` original (manchete nos verdadeiros, alegação de checador nos falsos). Este
script passa os registros de pesquisa/data/processed/dataset.jsonl pelo mesmo prompt do uso:
por padrão, todos os de treino, validacao e teste do protocolo B (`split_produto`), com ou
sem `texto_curto`; `reserva` e `fora` não entram no modelo do jogo e ficam de fora. Quem não
tem `texto_curto` (Fake.br, verdadeiras do FakeTrue.Br, a maior parte das mensagens) é
extraído do `texto`.

Cache: pesquisa/data/processed/padronizado_<versao>.jsonl, uma linha por registro, com o `id`, as
afirmações extraídas, o hash do prompt e o modelo. A versão vem do nome do arquivo do
prompt (extrair_afirmacoes_v1.txt -> v1). Rodar de novo só chama a LLM para os ids que
faltam; se o texto do prompt mudar sem trocar a versão, ou se o modelo mudar, as linhas
antigas deixam de valer e são refeitas: o treino nunca mistura saídas de dois modelos. Cada linha é gravada assim que fica pronta, então dá para interromper e retomar.

A resposta da LLM segue o esquema da #19: {"e_opiniao": bool, "afirmacoes": [{"texto",
"quem_disse"}]}. O cache guarda as afirmações com quem disse; o treino usa só o `texto`.

Várias afirmações ou nenhuma (decisão registrada em doc/padronizacao.md): `aplicar` usa a
primeira como `texto_padronizado` e marca `n_afirmacoes`. Com zero (opinião),
`texto_padronizado` fica vazio e o registro sai do treino de frases curtas.

LLM: o Qwen pelo Ollama (ou qualquer endpoint compatível com a API de chat da OpenAI),
configurado por LLM_BASE_URL, LLM_MODEL (com a versão fixa) e LLM_API_KEY. O pedido leva o
JSON Schema da #19 em `response_format` (--sem-esquema se o provedor não aceitar), a
temperatura 0 e o texto truncado em --max-caracteres. LLM_EXTRA_BODY (JSON) entra no corpo
do pedido, para opções do provedor, como desligar o raciocínio do Qwen3. Erros 429 e 5xx e
falhas de rede ganham novas tentativas com espera crescente.
`--provedor fake` devolve o próprio texto, para testar o fluxo sem LLM.

Amostra antes do lote inteiro: `--base fakebr --limite 100` processa 100 registros só do
Fake.br, espalhados pelo dataset e com as duas notícias de cada par juntas (a falsa e a
verdadeira do mesmo assunto). `--exportar` grava pesquisa/data/conferencia/padronizacao_<versao>.csv
(fora do Git) com o texto original ao lado das afirmações extraídas, para conferir à mão.

Só biblioteca padrão, como pesquisa/dados/preparar_dados.py.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROCESSED = RAIZ / "data" / "processed"
CONFERENCIA = RAIZ / "data" / "conferencia"
DATASET = PROCESSED / "dataset.jsonl"

# O prompt recebe o texto neste marcador; sem ele, o texto vai depois do prompt.
MARCADOR_TEXTO = "{texto}"

# Splits do protocolo B que entram no modelo do jogo; `reserva` e `fora` não entram.
SPLITS_PADRAO = ("treino", "validacao", "teste")

# Cerca de 4 mil tokens em português: controla custo e tempo das matérias longas.
MAX_CARACTERES = 16_000
TENTATIVAS = 4
ESPERA_INICIAL = 2.0  # segundos; dobra a cada nova tentativa
STATUS_TRANSITORIOS = {429, 500, 502, 503, 504}

# Saída da #19, no formato estrito de `response_format` da API da OpenAI.
ESQUEMA_AFIRMACOES = {
    "type": "object",
    "properties": {
        "e_opiniao": {"type": "boolean"},
        "afirmacoes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "texto": {"type": "string"},
                    "quem_disse": {"type": ["string", "null"]},
                },
                "required": ["texto", "quem_disse"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["e_opiniao", "afirmacoes"],
    "additionalProperties": False,
}


@dataclass
class Extracao:
    afirmacoes: list[dict]  # [{"texto": str, "quem_disse": str | None}]
    tokens_entrada: int = 0
    tokens_saida: int = 0


# Recebe o texto de um registro e devolve as afirmações extraídas.
Extrator = Callable[[str], Extracao]


@dataclass
class Prompt:
    versao: str
    texto: str
    sha1: str = field(init=False)

    def __post_init__(self):
        self.sha1 = hashlib.sha1(self.texto.encode()).hexdigest()[:12]

    def preencher(self, texto: str) -> str:
        if MARCADOR_TEXTO in self.texto:
            return self.texto.replace(MARCADOR_TEXTO, texto)
        return f"{self.texto.rstrip()}\n\n{texto}"


def carregar_prompt(caminho: Path) -> Prompt:
    """extrair_afirmacoes_v3.txt -> versão v3. Exige a versão no nome do arquivo."""
    m = re.search(r"_(v\d+)$", caminho.stem)
    if not m:
        raise ValueError(f"O nome do prompt precisa terminar em _vN: {caminho.name}")
    return Prompt(versao=m[1], texto=caminho.read_text(encoding="utf-8"))


def caminho_cache(versao: str, pasta: Path = PROCESSED) -> Path:
    return pasta / f"padronizado_{versao}.jsonl"


def texto_de_entrada(registro: dict) -> str | None:
    """O texto curto, se houver; senão o texto longo, de onde a LLM extrai a afirmação."""
    for campo in ("texto_curto", "texto"):
        valor = (registro.get(campo) or "").strip()
        if valor:
            return valor
    return None


def filtrar_splits(registros: Iterable[dict], splits: Iterable[str] | None) -> Iterable[dict]:
    """Só os registros cujo `split_produto` está em `splits`; None deixa passar todos."""
    if splits is None:
        yield from registros
        return
    splits = set(splits)
    for registro in registros:
        if registro.get("split_produto") in splits:
            yield registro


def ler_cache(caminho: Path, prompt: Prompt, modelo: str) -> dict[str, dict]:
    """Linhas do cache feitas com este prompt e este modelo, por id. As demais são ignoradas."""
    if not caminho.exists():
        return {}
    cache = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        item = json.loads(linha)
        if item["prompt_sha1"] == prompt.sha1 and item.get("modelo") == modelo:
            cache[item["id"]] = item
    return cache


def _afirmacao(valor) -> dict | None:
    if isinstance(valor, dict) and isinstance(valor.get("texto"), str):
        texto, quem_disse = valor["texto"].strip(), valor.get("quem_disse")
        if texto and (quem_disse is None or isinstance(quem_disse, str)):
            return {"texto": texto, "quem_disse": (quem_disse or "").strip() or None}
    return None


def interpretar_resposta(resposta: str) -> list[dict]:
    """Lê {"e_opiniao": ..., "afirmacoes": [{"texto", "quem_disse"}]} (#19), mesmo cercado de texto.

    Uma lista vazia quer dizer opinião (nenhuma afirmação checável).
    """
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", resposta.strip())
    for inicio in (i for i, c in enumerate(texto) if c in "[{"):
        try:
            valor, _ = json.JSONDecoder().raw_decode(texto, inicio)
        except json.JSONDecodeError:
            continue
        lista = valor.get("afirmacoes") if isinstance(valor, dict) else None
        if not isinstance(lista, list):
            continue
        afirmacoes = [_afirmacao(v) for v in lista]
        if all(afirmacoes):
            return afirmacoes
    raise ValueError(f"Resposta da LLM fora do formato esperado: {resposta[:200]!r}")


def extrator_fake(texto: str) -> Extracao:
    """Sem LLM: devolve o texto como única afirmação. Serve para testar o fluxo."""
    return Extracao(afirmacoes=[{"texto": texto, "quem_disse": None}])


def requisitar(
    requisicao: urllib.request.Request,
    timeout: float,
    tentativas: int = TENTATIVAS,
    espera: float = ESPERA_INICIAL,
    dormir: Callable[[float], None] = time.sleep,
) -> dict:
    """POST com novas tentativas para limite de taxa (429), erro do servidor (5xx) e rede."""
    for tentativa in range(tentativas):
        try:
            with urllib.request.urlopen(requisicao, timeout=timeout) as resposta:
                return json.load(resposta)
        except urllib.error.HTTPError as erro:
            if erro.code not in STATUS_TRANSITORIOS or tentativa == tentativas - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if tentativa == tentativas - 1:
                raise
        dormir(espera * 2**tentativa)
    raise AssertionError("inalcançável")


def extrator_openai(
    prompt: Prompt,
    base_url: str,
    modelo: str,
    chave: str | None,
    timeout: float = 300,
    esquema: bool = True,
    max_caracteres: int = MAX_CARACTERES,
    extra: dict | None = None,
    dormir: Callable[[float], None] = time.sleep,
) -> Extrator:
    """Endpoint /chat/completions compatível com a OpenAI (o Qwen pelo Ollama, ou outro)."""
    url = base_url.rstrip("/") + "/chat/completions"
    cabecalhos = {"Content-Type": "application/json"}
    if chave:
        cabecalhos["Authorization"] = f"Bearer {chave}"

    def extrair(texto: str) -> Extracao:
        corpo = {
            "model": modelo,
            "messages": [{"role": "user", "content": prompt.preencher(texto[:max_caracteres])}],
            "temperature": 0,
            **(extra or {}),
        }
        if esquema:
            corpo["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "afirmacoes", "strict": True, "schema": ESQUEMA_AFIRMACOES},
            }
        requisicao = urllib.request.Request(url, json.dumps(corpo).encode(), cabecalhos)
        dados = requisitar(requisicao, timeout, dormir=dormir)
        uso = dados.get("usage") or {}
        return Extracao(
            afirmacoes=interpretar_resposta(dados["choices"][0]["message"]["content"]),
            tokens_entrada=uso.get("prompt_tokens", 0),
            tokens_saida=uso.get("completion_tokens", 0),
        )

    return extrair


@dataclass
class Relatorio:
    versao: str
    prompt_sha1: str
    modelo: str
    total: int = 0
    em_cache: int = 0
    processados: int = 0
    sem_texto: int = 0
    falhas: int = 0
    opinioes: int = 0
    varias_afirmacoes: int = 0
    tokens_entrada: int = 0
    tokens_saida: int = 0
    segundos: float = 0.0

    def resumo(self) -> str:
        por_item = self.segundos / self.processados if self.processados else 0
        return (
            f"prompt {self.versao} ({self.prompt_sha1}), modelo {self.modelo}\n"
            f"  registros: {self.total} | já em cache: {self.em_cache} | chamadas à LLM: "
            f"{self.processados} | falhas: {self.falhas} | sem texto: {self.sem_texto}\n"
            f"  nesta rodada: {self.opinioes} sem afirmação (opinião), "
            f"{self.varias_afirmacoes} com várias\n"
            f"  tempo: {self.segundos:.0f} s ({por_item:.2f} s por item) | tokens: "
            f"{self.tokens_entrada} de entrada, {self.tokens_saida} de saída"
        )


def padronizar(
    registros: Iterable[dict],
    prompt: Prompt,
    extrator: Extrator,
    cache_path: Path,
    modelo: str = "",
    paralelo: int = 1,
    limite: int | None = None,
    log: Callable[[str], None] = print,
) -> Relatorio:
    """Extrai as afirmações dos registros que ainda não estão no cache e grava no cache."""
    relatorio = Relatorio(versao=prompt.versao, prompt_sha1=prompt.sha1, modelo=modelo)
    cache = ler_cache(cache_path, prompt, modelo)
    pendentes = []
    for registro in registros:
        relatorio.total += 1
        if registro["id"] in cache:
            relatorio.em_cache += 1
            continue
        texto = texto_de_entrada(registro)
        if texto is None:
            relatorio.sem_texto += 1
            continue
        pendentes.append((registro["id"], texto, ordem_amostra(registro)))
    if limite is not None:
        # Amostra espalhada pelo dataset, com os registros do mesmo par lado a lado.
        pendentes = sorted(pendentes, key=lambda p: p[2])[:limite]

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    trava = threading.Lock()
    inicio = time.monotonic()

    def processar(id_: str, texto: str) -> tuple[str, Extracao]:
        return id_, extrator(texto)

    with (
        open(cache_path, "a", encoding="utf-8", newline="\n") as saida,
        ThreadPoolExecutor(max_workers=paralelo) as pool,
    ):
        futuros = [pool.submit(processar, id_, texto) for id_, texto, _ in pendentes]
        for n, futuro in enumerate(as_completed(futuros), 1):
            try:
                id_, extracao = futuro.result()
            except (OSError, ValueError, KeyError, IndexError) as erro:  # rede, timeout, JSON
                relatorio.falhas += 1
                log(f"  falha: {erro}")
                continue
            item = {
                "id": id_,
                "versao": prompt.versao,
                "prompt_sha1": prompt.sha1,
                "modelo": modelo,
                "afirmacoes": extracao.afirmacoes,
            }
            with trava:
                saida.write(json.dumps(item, ensure_ascii=False) + "\n")
                saida.flush()
            relatorio.processados += 1
            relatorio.opinioes += not extracao.afirmacoes
            relatorio.varias_afirmacoes += len(extracao.afirmacoes) > 1
            relatorio.tokens_entrada += extracao.tokens_entrada
            relatorio.tokens_saida += extracao.tokens_saida
            if n % 100 == 0:
                log(f"  {n}/{len(pendentes)} ({time.monotonic() - inicio:.0f} s)")
    relatorio.segundos = time.monotonic() - inicio
    return relatorio


def ordem_amostra(registro: dict) -> tuple[str, str]:
    """Chave da amostra: hash do par (ou do id), e o id para desempatar dentro do par."""
    grupo = registro["id"]
    if registro.get("par_id") is not None:
        grupo = f"{registro.get('base')}-par-{registro['par_id']}"
    return hashlib.sha1(f"amostra-{grupo}".encode()).hexdigest(), registro["id"]


def exportar(registros: Iterable[dict], cache: dict[str, dict], destino: Path) -> int:
    """CSV para conferência: texto original e afirmações extraídas, lado a lado."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    linhas = 0
    with open(destino, "w", encoding="utf-8-sig", newline="") as saida:
        escritor = csv.writer(saida)
        escritor.writerow(
            ["id", "base", "veracidade", "split_produto", "texto_original", "n_afirmacoes"]
            + ["afirmacao_1", "quem_disse_1", "demais_afirmacoes"]
        )
        for registro in registros:
            item = cache.get(registro["id"])
            if not item:
                continue
            afirmacoes = item["afirmacoes"]
            primeira = afirmacoes[0] if afirmacoes else {}
            escritor.writerow(
                [registro["id"], registro.get("base"), registro.get("veracidade")]
                + [registro.get("split_produto"), (texto_de_entrada(registro) or "")[:1500]]
                + [len(afirmacoes), primeira.get("texto", ""), primeira.get("quem_disse") or ""]
                + [" | ".join(a["texto"] for a in afirmacoes[1:])]
            )
            linhas += 1
    return linhas


def aplicar(registros: Iterable[dict], cache: dict[str, dict]) -> Iterable[dict]:
    """Acrescenta `texto_padronizado` e `n_afirmacoes` a cada registro (para pesquisa/ml/dados.py).

    Regra: a primeira afirmação vira o texto padronizado. Sem afirmação (opinião) ou sem
    linha no cache, `texto_padronizado` fica None e o registro não entra no treino de
    frases curtas; `n_afirmacoes` é None quando o registro não foi processado.
    """
    for registro in registros:
        item = cache.get(registro["id"])
        afirmacoes = item["afirmacoes"] if item else []
        yield {
            **registro,
            "texto_padronizado": afirmacoes[0]["texto"] if afirmacoes else None,
            "n_afirmacoes": len(afirmacoes) if item else None,
        }


def ler_dataset(caminho: Path) -> Iterable[dict]:
    with open(caminho, encoding="utf-8") as entrada:
        for linha in entrada:
            if linha.strip():
                yield json.loads(linha)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--prompt", type=Path, required=True, help="arquivo extrair_afirmacoes_vN.txt"
    )
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--provedor", choices=("openai", "fake"), default="openai")
    parser.add_argument("--paralelo", type=int, default=1, help="chamadas simultâneas à LLM")
    parser.add_argument("--limite", type=int, help="processa no máximo N itens novos")
    parser.add_argument("--sem-esquema", action="store_true", help="não envia response_format")
    parser.add_argument("--max-caracteres", type=int, default=MAX_CARACTERES)
    parser.add_argument("--base", nargs="+", help="só estas bases (ex.: fakebr)")
    parser.add_argument(
        "--splits",
        default=",".join(SPLITS_PADRAO),
        help="splits do split_produto, separados por vírgula, ou 'todos'",
    )
    parser.add_argument(
        "--exportar", action="store_true", help="CSV de conferência do que já está no cache"
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        sys.exit(f"{args.dataset} não encontrado. Rode antes: make dados")
    prompt = carregar_prompt(args.prompt)
    splits = None if args.splits == "todos" else [s.strip() for s in args.splits.split(",")]
    if args.provedor == "fake":
        extrator, modelo = extrator_fake, "fake"
    else:
        base_url, modelo = os.environ.get("LLM_BASE_URL"), os.environ.get("LLM_MODEL")
        if not base_url or not modelo:
            sys.exit("Defina LLM_BASE_URL e LLM_MODEL no .env (ou use --provedor fake).")
        extrator = extrator_openai(
            prompt,
            base_url,
            modelo,
            os.environ.get("LLM_API_KEY"),
            esquema=not args.sem_esquema,
            max_caracteres=args.max_caracteres,
            extra=json.loads(os.environ.get("LLM_EXTRA_BODY") or "{}"),
        )

    def registros():
        for registro in filtrar_splits(ler_dataset(args.dataset), splits):
            if not args.base or registro.get("base") in args.base:
                yield registro

    cache_path = caminho_cache(prompt.versao)
    if args.exportar:
        destino = CONFERENCIA / f"padronizacao_{prompt.versao}.csv"
        n = exportar(registros(), ler_cache(cache_path, prompt, modelo), destino)
        print(f"{n} registros em {destino.relative_to(RAIZ)}")
        return
    relatorio = padronizar(
        registros(),
        prompt,
        extrator,
        cache_path,
        modelo=modelo,
        paralelo=args.paralelo,
        limite=args.limite,
    )
    print(f"splits: {args.splits}")
    print(relatorio.resumo())
    print(f"Cache em {cache_path.relative_to(RAIZ)}")
    # Tempo e tokens de cada rodada, para registrar o custo do lote (critério da #20).
    with open(cache_path.with_suffix(".rodadas.jsonl"), "a", encoding="utf-8") as rodadas:
        rodadas.write(json.dumps(vars(relatorio), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
