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
"""

import argparse
import random
import statistics
import time
from datetime import date
from pathlib import Path

import numpy as np
import torch
from torch import nn
from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup

from avaliar import gravar_previsoes, metricas
from configuracao import CONFIGS, Configuracao, carregar_configuracao
from dados import CLASSES, ORDEM, Exemplo, carregar

PASTA_CODIFICADOR = "codificador"
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
    p1, p2 = [], []
    for _, entrada in lotes(textos, tokenizador, modelo["max_tokens"], tamanho):
        a, b = fronteiras_de_logits(rede(entrada["input_ids"], entrada["attention_mask"]))
        p1.append(a)
        p2.append(b)
    if not p1:
        return np.array([]), np.array([])
    return np.concatenate(p1), np.concatenate(p2)


def salvar_modelo(rede: Coral, tokenizador, pasta: Path, extras: dict):
    destino = pasta / PASTA_CODIFICADOR
    rede.codificador.save_pretrained(destino)
    tokenizador.save_pretrained(destino)
    torch.save(
        {"linear": rede.linear.state_dict(), "vieses": rede.vieses.detach().cpu(), **extras},
        pasta / ARQUIVO_CABECA,
    )


def carregar_modelo(pasta: Path) -> dict:
    """Modelo salvo por este script: {"rede", "tokenizador", "max_tokens", "versao"}."""
    cabeca = torch.load(pasta / ARQUIVO_CABECA, map_location="cpu", weights_only=False)
    codificador = AutoModel.from_pretrained(pasta / PASTA_CODIFICADOR)
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


def treinar_semente(
    semente: int, treino: list[Exemplo], validacao: list[Exemplo], config: Configuracao
) -> tuple[float, int, Coral, list[float]]:
    """Ajusta uma semente; devolve (melhor F1, época, rede na melhor época, F1 por época)."""
    parametros = config.treino
    fixar_semente(semente)
    tokenizador = AutoTokenizer.from_pretrained(parametros["modelo_base"])
    rede = Coral(AutoModel.from_pretrained(parametros["modelo_base"]))
    max_tokens, tamanho = parametros.get("max_tokens", 96), parametros.get("lote", 32)
    max_epocas = parametros.get("max_epocas", 4)
    paciencia = parametros.get("paciencia", 1)

    classe = pesos_por_classe(treino)
    textos = [e.texto for e in treino]
    alvos = torch.tensor([[e.y1, e.y2] for e in treino], dtype=torch.float)
    pesos = torch.tensor([e.peso * classe[e.veracidade] for e in treino], dtype=torch.float)
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

    historico, melhor, sem_melhora = [], None, 0
    for epoca in range(1, max_epocas + 1):
        rede.train()
        ordem = torch.randperm(len(textos)).tolist()
        embaralhados = [textos[i] for i in ordem]
        inicio_epoca, soma = time.perf_counter(), 0.0
        for inicio, entrada in lotes(embaralhados, tokenizador, max_tokens, tamanho):
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
        if melhor is None or f1 > melhor[0]:
            estado = {k: v.detach().clone() for k, v in rede.state_dict().items()}
            melhor, sem_melhora = (f1, epoca, estado), 0
        else:
            sem_melhora += 1
            if sem_melhora > paciencia:
                break

    f1, epoca, estado = melhor
    rede.load_state_dict(estado)
    return f1, epoca, rede, historico


def treinar(config: Configuracao, saida: Path | None = None) -> dict:
    """Treina cada semente, guarda a melhor e grava modelo, previsões e configuração."""
    saida = saida or config.saida
    inicio = time.perf_counter()
    torch.set_num_threads(config.treino.get("threads") or torch.get_num_threads())
    conjunto = carregar(**config.argumentos_dados())
    treino, validacao = conjunto.splits["treino"], conjunto.splits["validacao"]
    if len({e.veracidade for e in treino}) < 3 or not validacao:
        raise ValueError("O treino precisa das três classes e a validação não pode estar vazia")

    por_semente, melhor = {}, None
    for semente in config.sementes:
        f1, epoca, rede, historico = treinar_semente(semente, treino, validacao, config)
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

    textos_latencia = [e.texto for e in validacao[:FRASES_LATENCIA]]
    inicio_latencia = time.perf_counter()
    for texto in textos_latencia:
        fronteiras([texto], modelo)
    latencia = 1000 * (time.perf_counter() - inicio_latencia) / max(len(textos_latencia), 1)

    valores = [s["f1_macro_validacao"] for s in por_semente.values()]
    resultado = {
        "versao": versao,
        "semente_escolhida": semente,
        "f1_macro_validacao": f1,
        "f1_macro_validacao_media": statistics.mean(valores),
        "f1_macro_validacao_desvio": statistics.pstdev(valores),
        "por_semente": por_semente,
        "exemplos_treino": len(treino),
        "segundos_treino": round(time.perf_counter() - inicio, 1),
        "latencia_ms_por_frase": round(latencia, 3),
    }
    gravar_previsoes(saida, previsoes, {**config.registro(conjunto.dataset_sha256), **resultado})
    return resultado


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--config", type=Path, default=CONFIGS / "bert.toml")
    parser.add_argument("--saida", type=Path, help="sobrescreve a pasta de saída da configuração")
    parser.add_argument("--sementes", type=int, nargs="+", help="sobrescreve as sementes")
    parser.add_argument("--max-epocas", type=int, help="sobrescreve treino.max_epocas")
    args = parser.parse_args()
    config = carregar_configuracao(args.config)
    if args.sementes:
        config.sementes = args.sementes
    if args.max_epocas:
        config.treino = {**config.treino, "max_epocas": args.max_epocas}
    resultado = treinar(config, args.saida)
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
