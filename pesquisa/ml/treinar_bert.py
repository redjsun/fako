"""Experimento 2: BERTimbau com cabeça ordinal CORAL (issue #10).

Uso (container ml, PyTorch CPU):
    python pesquisa/ml/treinar_bert.py                                     # configs/bert.toml
    python pesquisa/ml/treinar_bert.py --sementes 42 --max-epocas 2        # rodada curta
    python pesquisa/ml/avaliar.py --modelo models/2026-11/bert             # o relatório

Cabeça CORAL (Cao, Mirjalili e Raschka, 2020): o [CLS] do BERTimbau passa por uma única
camada linear g(x), e cada fronteira ordinal tem só o seu viés:
- P1 = sigmoid(g(x) + b1) = P(veracidade > falso)
- P2 = sigmoid(g(x) + b2) = P(veracidade > enganoso), cortada em P1 por segurança
Como as duas fronteiras dividem os mesmos pesos, a ordem falso < enganoso < verdadeiro é
respeitada e as saídas seguem o contrato do avaliar.py, igual à referência TF-IDF.

Perda: entropia cruzada binária nas duas fronteiras, com o peso por `origem_rotulo` de
dados.py vezes o peso "balanced" da classe (a classe verdadeiro é rara). Parada antecipada
pelo F1 macro das três classes na validação; o teste não é olhado. Com várias sementes, fica
o modelo da semente de melhor F1 na validação, e a média e o desvio vão para o config.json.

Saídas na pasta `saida` da configuração:
- `codificador/`: BERTimbau ajustado e tokenizador (`save_pretrained`);
- `cabeca_coral.pt`: pesos da camada linear e os dois vieses;
- `previsoes.jsonl` e `config.json` (contrato do avaliar.py).

Ponto de retomada: no fim de cada época, `retomada/semente-N.pt` guarda pesos, otimizador,
agenda, histórico, melhor época e o estado dos geradores aleatórios. Rodar de novo continua da
última época concluída, com o mesmo embaralhamento de uma rodada sem pausa; a assinatura
(configuração, dataset, semente, épocas) impede retomar com outra configuração. `--do-zero`
ignora os pontos salvos. A pasta `retomada/` é apagada quando o treino termina.

Dispositivo: a GPU NVIDIA (`cuda`) quando houver, senão a do Mac (`mps`), senão a CPU; fixe com
`--dispositivo` ou `treino.dispositivo`. No container, a GPU NVIDIA pede `make bert GPU=1`
(compose.gpu.yaml, PyTorch CUDA). Fora do container:
    pip install torch && pip install -r pesquisa/ml/requirements-treino.txt
    python pesquisa/ml/treinar_bert.py --dispositivo cuda
O ponto de retomada não depende do dispositivo, e a latência é sempre medida na CPU, como na API.
"""

import argparse
import random
import shutil
import statistics
import time
from datetime import date
from pathlib import Path

import numpy as np
import torch
from torch import nn
from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup

from avaliar import gravar_previsoes, metricas
from configuracao import (
    CONFIGS,
    Configuracao,
    carregar_configuracao,
    conferir_artefato,
    sha256_arquivo,
)
from dados import CLASSES, ORDEM, Exemplo, carregar

PASTA_CODIFICADOR = "codificador"
PASTA_RETOMADA = "retomada"
ARQUIVO_CABECA = "cabeca_coral.pt"
FRASES_LATENCIA = 200


class Coral(nn.Module):
    """Codificador BERT + camada linear compartilhada + um viés por fronteira."""

    def __init__(self, codificador: nn.Module, fronteiras: int = 2):
        super().__init__()
        self.codificador = codificador
        self.linear = nn.Linear(codificador.config.hidden_size, 1, bias=False)
        self.vieses = nn.Parameter(torch.zeros(fronteiras))

    def forward(self, input_ids, attention_mask):
        saida = self.codificador(input_ids=input_ids, attention_mask=attention_mask)
        cls = saida.last_hidden_state[:, 0]
        return self.linear(cls) + self.vieses  # logits das fronteiras: (lote, 2)


def fronteiras_de_logits(logits: torch.Tensor) -> tuple[np.ndarray, np.ndarray]:
    probabilidades = torch.sigmoid(logits).detach().cpu().numpy()
    p1 = probabilidades[:, 0]
    return p1, np.minimum(probabilidades[:, 1], p1)


def pesos_por_classe(exemplos: list[Exemplo]) -> dict[str, float]:
    """Peso "balanced" do scikit-learn: n / (classes × n da classe)."""
    contagem = {c: sum(e.veracidade == c for e in exemplos) for c in CLASSES}
    return {c: len(exemplos) / (len(CLASSES) * n) if n else 0.0 for c, n in contagem.items()}


def escolher_dispositivo(pedido: str | None = None) -> torch.device:
    """O `pedido` (cuda, mps ou cpu) ou, sem ele, o mais rápido disponível."""
    disponiveis = {
        "cuda": torch.cuda.is_available(),
        "mps": torch.backends.mps.is_available(),
        "cpu": True,
    }
    if pedido:
        if pedido not in disponiveis:
            raise ValueError(f"Dispositivo desconhecido: {pedido} (use cuda, mps ou cpu)")
        if not disponiveis[pedido]:
            raise ValueError(f"Dispositivo {pedido} indisponível nesta máquina")
        return torch.device(pedido)
    return torch.device(next(nome for nome, ok in disponiveis.items() if ok))


def fixar_semente(semente: int):
    random.seed(semente)
    np.random.seed(semente)
    torch.manual_seed(semente)


def lotes(textos: list[str], tokenizador, max_tokens: int, tamanho: int):
    """Lotes tokenizados com preenchimento só até a maior frase do lote."""
    for inicio in range(0, len(textos), tamanho):
        yield (
            inicio,
            tokenizador(
                textos[inicio : inicio + tamanho],
                truncation=True,
                max_length=max_tokens,
                padding=True,
                return_tensors="pt",
            ),
        )


@torch.no_grad()
def fronteiras(textos: list[str], modelo: dict, tamanho: int = 64) -> tuple[np.ndarray, np.ndarray]:
    """P1 e P2 de um modelo carregado com `carregar_modelo`."""
    rede, tokenizador = modelo["rede"], modelo["tokenizador"]
    rede.eval()
    dispositivo = next(rede.parameters()).device
    p1, p2 = [], []
    for _, entrada in lotes(textos, tokenizador, modelo["max_tokens"], tamanho):
        entrada = entrada.to(dispositivo)
        a, b = fronteiras_de_logits(rede(entrada["input_ids"], entrada["attention_mask"]))
        p1.append(a)
        p2.append(b)
    if not p1:
        return np.array([]), np.array([])
    return np.concatenate(p1), np.concatenate(p2)


def salvar_modelo(rede: Coral, tokenizador, pasta: Path, extras: dict):
    destino = pasta / PASTA_CODIFICADOR
    rede.codificador.save_pretrained(destino, safe_serialization=True)
    tokenizador.save_pretrained(destino)
    torch.save(
        {"linear": rede.linear.state_dict(), "vieses": rede.vieses.detach().cpu(), **extras},
        pasta / ARQUIVO_CABECA,
    )


def carregar_modelo(pasta: Path) -> dict:
    """Modelo salvo por este script: {"rede", "tokenizador", "max_tokens", "versao"}."""
    # weights_only: a cabeça tem só tensores, inteiros e textos; nada de pickle arbitrário.
    cabeca = torch.load(
        conferir_artefato(pasta, ARQUIVO_CABECA), map_location="cpu", weights_only=True
    )
    codificador = AutoModel.from_pretrained(pasta / PASTA_CODIFICADOR, use_safetensors=True)
    rede = Coral(codificador)
    rede.linear.load_state_dict(cabeca["linear"])
    rede.vieses.data = cabeca["vieses"]
    rede.eval()
    return {
        "rede": rede,
        "tokenizador": AutoTokenizer.from_pretrained(pasta / PASTA_CODIFICADOR),
        "max_tokens": cabeca["max_tokens"],
        "versao": cabeca["versao"],
    }


def caminho_retomada(saida: Path, semente: int) -> Path:
    return saida / PASTA_RETOMADA / f"semente-{semente}.pt"


def gravar_retomada(caminho: Path, estado: dict):
    """Grava por cima só depois de escrever por inteiro: uma pausa no meio não corrompe."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(".tmp")
    torch.save(estado, temporario)
    temporario.replace(caminho)


def ler_retomada(caminho: Path, assinatura: dict) -> dict | None:
    if not caminho.exists():
        return None
    estado = torch.load(caminho, map_location="cpu", weights_only=False)
    if estado.get("assinatura") != assinatura:
        print(f"Ponto de retomada de outra configuração, ignorado: {caminho}")
        return None
    return estado


def treinar_semente(
    semente: int,
    treino: list[Exemplo],
    validacao: list[Exemplo],
    config: Configuracao,
    retomada: Path | None = None,
    assinatura: dict | None = None,
    dispositivo: torch.device | None = None,
) -> tuple[float, int, Coral, list[float]]:
    """Ajusta uma semente; devolve (melhor F1, época, rede na melhor época, F1 por época).

    Com `retomada`, grava o ponto de retomada no fim de cada época e, se ele já existir com a
    mesma `assinatura`, continua da época seguinte à última concluída.
    """
    parametros = config.treino
    dispositivo = dispositivo or torch.device("cpu")
    fixar_semente(semente)
    tokenizador = AutoTokenizer.from_pretrained(parametros["modelo_base"])
    rede = Coral(AutoModel.from_pretrained(parametros["modelo_base"])).to(dispositivo)
    max_tokens, tamanho = parametros.get("max_tokens", 96), parametros.get("lote", 32)
    max_epocas = parametros.get("max_epocas", 4)
    # Quantas épocas seguidas sem melhora são toleradas: o treino para na seguinte.
    paciencia = parametros.get("paciencia", 1)

    classe = pesos_por_classe(treino)
    textos = [e.texto for e in treino]
    alvos = torch.tensor([[e.y1, e.y2] for e in treino], dtype=torch.float, device=dispositivo)
    pesos = torch.tensor(
        [e.peso * classe[e.veracidade] for e in treino], dtype=torch.float, device=dispositivo
    )
    y_validacao = np.array([ORDEM[e.veracidade] for e in validacao])

    otimizador = torch.optim.AdamW(
        rede.parameters(),
        lr=parametros.get("taxa_aprendizado", 3e-5),
        weight_decay=parametros.get("weight_decay", 0.01),
    )
    passos = max_epocas * ((len(textos) + tamanho - 1) // tamanho)
    agenda = get_linear_schedule_with_warmup(
        otimizador, int(parametros.get("aquecimento", 0.1) * passos), passos
    )
    perda = nn.BCEWithLogitsLoss(reduction="none")
    modelo = {"rede": rede, "tokenizador": tokenizador, "max_tokens": max_tokens}

    historico, melhor, sem_melhora, primeira = [], None, 0, 1
    assinatura = {**(assinatura or {}), "semente": semente, "max_epocas": max_epocas}
    salvo = ler_retomada(retomada, assinatura) if retomada else None
    if salvo:
        rede.load_state_dict(salvo["rede"])
        otimizador.load_state_dict(salvo["otimizador"])
        agenda.load_state_dict(salvo["agenda"])
        historico, melhor, sem_melhora = salvo["historico"], salvo["melhor"], salvo["sem_melhora"]
        torch.set_rng_state(salvo["aleatorio"]["torch"])
        if dispositivo.type == "cuda" and "cuda" in salvo["aleatorio"]:
            torch.cuda.set_rng_state_all(salvo["aleatorio"]["cuda"])
        np.random.set_state(salvo["aleatorio"]["numpy"])
        random.setstate(salvo["aleatorio"]["python"])
        primeira = max_epocas + 1 if salvo["concluida"] else salvo["epoca"] + 1
        print(f"semente {semente}: retomando depois da época {salvo['epoca']}")

    for epoca in range(primeira, max_epocas + 1):
        rede.train()
        ordem = torch.randperm(len(textos)).tolist()
        embaralhados = [textos[i] for i in ordem]
        inicio_epoca, soma = time.perf_counter(), 0.0
        for inicio, entrada in lotes(embaralhados, tokenizador, max_tokens, tamanho):
            entrada = entrada.to(dispositivo)
            indices = ordem[inicio : inicio + tamanho]
            logits = rede(entrada["input_ids"], entrada["attention_mask"])
            valor = (perda(logits, alvos[indices]).sum(dim=1) * pesos[indices]).mean()
            otimizador.zero_grad()
            valor.backward()
            torch.nn.utils.clip_grad_norm_(rede.parameters(), 1.0)
            otimizador.step()
            agenda.step()
            soma += valor.item() * len(indices)

        p1, p2 = fronteiras([e.texto for e in validacao], modelo)
        f1 = metricas(y_validacao, p1, p2)["f1_macro"]
        historico.append(f1)
        print(
            f"semente {semente} época {epoca}: perda {soma / len(textos):.4f}, "
            f"F1 macro na validação {f1:.3f} ({time.perf_counter() - inicio_epoca:.0f} s)"
        )
        parar = False
        if melhor is None or f1 > melhor[0]:
            estado = {k: v.detach().clone() for k, v in rede.state_dict().items()}
            melhor, sem_melhora = (f1, epoca, estado), 0
        else:
            sem_melhora += 1
            parar = sem_melhora > paciencia
        if retomada:
            gravar_retomada(
                retomada,
                {
                    "assinatura": assinatura,
                    "epoca": epoca,
                    "concluida": parar or epoca == max_epocas,
                    "rede": rede.state_dict(),
                    "otimizador": otimizador.state_dict(),
                    "agenda": agenda.state_dict(),
                    "historico": historico,
                    "melhor": melhor,
                    "sem_melhora": sem_melhora,
                    "aleatorio": {
                        "torch": torch.get_rng_state(),
                        "numpy": np.random.get_state(),
                        "python": random.getstate(),
                        **(
                            {"cuda": torch.cuda.get_rng_state_all()}
                            if dispositivo.type == "cuda"
                            else {}
                        ),
                    },
                },
            )
        if parar:
            break

    f1, epoca, estado = melhor
    rede.load_state_dict(estado)
    return f1, epoca, rede, historico


def treinar(
    config: Configuracao,
    saida: Path | None = None,
    do_zero: bool = False,
    dispositivo: str | None = None,
) -> dict:
    """Treina cada semente, guarda a melhor e grava modelo, previsões e configuração."""
    saida = saida or config.saida
    dispositivo = escolher_dispositivo(dispositivo or config.treino.get("dispositivo"))
    print(f"Dispositivo: {dispositivo}")
    if do_zero:
        shutil.rmtree(saida / PASTA_RETOMADA, ignore_errors=True)
    inicio = time.perf_counter()
    torch.set_num_threads(config.treino.get("threads") or torch.get_num_threads())
    conjunto = carregar(**config.argumentos_dados())
    treino, validacao = conjunto.splits["treino"], conjunto.splits["validacao"]
    if len({e.veracidade for e in treino}) < 3 or not validacao:
        raise ValueError("O treino precisa das três classes e a validação não pode estar vazia")

    registro = config.registro(conjunto.dataset_sha256)
    assinatura = {chave: registro[chave] for chave in ("configuracao_sha1", "dataset_sha256")}
    por_semente, melhor = {}, None
    for semente in config.sementes:
        f1, epoca, rede, historico = treinar_semente(
            semente,
            treino,
            validacao,
            config,
            retomada=caminho_retomada(saida, semente),
            assinatura=assinatura,
            dispositivo=dispositivo,
        )
        por_semente[str(semente)] = {
            "f1_macro_validacao": f1,
            "epoca": epoca,
            "por_epoca": historico,
        }
        if melhor is None or f1 > melhor[0]:
            melhor = (f1, semente, rede)

    f1, semente, rede = melhor
    versao = f"{config.nome}-{date.today().isoformat()}"
    tokenizador = AutoTokenizer.from_pretrained(config.treino["modelo_base"])
    max_tokens = config.treino.get("max_tokens", 96)
    saida.mkdir(parents=True, exist_ok=True)
    salvar_modelo(rede, tokenizador, saida, {"max_tokens": max_tokens, "versao": versao})
    modelo = {"rede": rede, "tokenizador": tokenizador, "max_tokens": max_tokens}

    previsoes = {}
    for split in ("validacao", "teste"):
        exemplos = conjunto.splits[split]
        if exemplos:
            previsoes[split] = (exemplos, *fronteiras([e.texto for e in exemplos], modelo))

    rede.to("cpu")  # a API roda na CPU
    textos_latencia = [e.texto for e in validacao[:FRASES_LATENCIA]]
    inicio_latencia = time.perf_counter()
    for texto in textos_latencia:
        fronteiras([texto], modelo)
    latencia = 1000 * (time.perf_counter() - inicio_latencia) / max(len(textos_latencia), 1)

    valores = [s["f1_macro_validacao"] for s in por_semente.values()]
    resultado = {
        "versao": versao,
        "artefatos_sha256": {ARQUIVO_CABECA: sha256_arquivo(saida / ARQUIVO_CABECA)},
        "semente_escolhida": semente,
        "f1_macro_validacao": f1,
        "f1_macro_validacao_media": statistics.mean(valores),
        "f1_macro_validacao_desvio": statistics.pstdev(valores),
        "por_semente": por_semente,
        "exemplos_treino": len(treino),
        "segundos_treino": round(time.perf_counter() - inicio, 1),
        "latencia_ms_por_frase": round(latencia, 3),
    }
    gravar_previsoes(saida, previsoes, {**registro, **resultado})
    shutil.rmtree(
        saida / PASTA_RETOMADA, ignore_errors=True
    )  # treino completo: não há o que retomar
    return resultado


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--config", type=Path, default=CONFIGS / "bert.toml")
    parser.add_argument("--saida", type=Path, help="sobrescreve a pasta de saída da configuração")
    parser.add_argument("--sementes", type=int, nargs="+", help="sobrescreve as sementes")
    parser.add_argument("--max-epocas", type=int, help="sobrescreve treino.max_epocas")
    parser.add_argument(
        "--do-zero", action="store_true", help="ignora os pontos de retomada e recomeça"
    )
    parser.add_argument(
        "--dispositivo",
        choices=("cuda", "mps", "cpu"),
        help="sobrescreve treino.dispositivo; sem nenhum dos dois, o mais rápido disponível",
    )
    args = parser.parse_args()
    config = carregar_configuracao(args.config)
    if args.sementes:
        config.sementes = args.sementes
    if args.max_epocas:
        config.treino = {**config.treino, "max_epocas": args.max_epocas}
    resultado = treinar(config, args.saida, do_zero=args.do_zero, dispositivo=args.dispositivo)
    saida = args.saida or config.saida
    print(
        f"\nSemente {resultado['semente_escolhida']} (F1 macro {resultado['f1_macro_validacao']:.3f}; "
        f"média {resultado['f1_macro_validacao_media']:.3f} ± "
        f"{resultado['f1_macro_validacao_desvio']:.3f}), {resultado['segundos_treino']} s de treino, "
        f"{resultado['latencia_ms_por_frase']} ms por frase"
    )
    print(f"Gravado em {saida}; avalie com: python pesquisa/ml/avaliar.py --modelo {saida}")


if __name__ == "__main__":
    main()
