import sys, textwrap
import pandas as pd

ARQ = "anotacoes/rodada-01_trabalho.csv"
EU = sys.argv[1] if len(sys.argv) > 1 else input("Seu nome/identificador: ").strip()
TIPOS = {"o": "opiniao", "f": "fabricado", "e": "enganoso", "n": "nenhum", "x": "fora_escopo"}
VERAC = {"v": "verdadeiro", "e": "enganoso", "f": "falso"}
SINAIS = ["pede_compartilhamento", "urgencia", "apelo_emocional", "ataque"]

df = pd.read_csv(ARQ, dtype=str, keep_default_na=False)
pend = df.index[df["anotador"] == "pre_anotacao_llm"].tolist()
print(f"{len(pend)} pendentes. Comandos: Enter=aceita, e=edita, s=pula, q=sai\n")

def salvar():
    df.to_csv(ARQ + ".tmp", index=False)
    import os; os.replace(ARQ + ".tmp", ARQ)

def pergunta(msg, opcoes, atual):
    while True:
        r = input(f"{msg} {opcoes} [{atual}]: ").strip().lower()
        if r == "":
            return atual
        if r in opcoes:
            return opcoes[r] if isinstance(opcoes, dict) else r
        if r == "-":
            return ""
        print("  inválido")

for n, i in enumerate(pend, 1):
    r = df.loc[i]
    print("=" * 80)
    print(f"[{n}/{len(pend)}] {r['id']}")
    print(textwrap.fill(r["texto_curto"].replace("\n", " ")[:700], 100))
    if r["veredito_original"]:
        print(f"\nVEREDITO ORIGINAL: {r['veredito_original']}")
    print(f"\nPRÉ: tipo={r['tipo'] or '?'} | veracidade={r['veracidade'] or '-'} | "
          + " ".join(f"{s}={r[s]}" for s in SINAIS))
    cmd = input("[Enter=aceita | e=edita | s=pula | q=sai]: ").strip().lower()
    if cmd == "q":
        break
    if cmd == "s":
        continue
    if cmd == "e" or not r["tipo"]:
        df.at[i, "tipo"] = pergunta("tipo", TIPOS, r["tipo"])
        if df.at[i, "tipo"] == "opiniao":
            df.at[i, "veracidade"] = ""
        else:
            df.at[i, "veracidade"] = pergunta("veracidade (- p/ vazio)", VERAC, r["veracidade"])
        for s in SINAIS:
            df.at[i, s] = pergunta(s, {"0": "0", "1": "1"}, r[s])
        obs = input("observacao (URL/dúvida, Enter p/ manter): ").strip()
        if obs:
            df.at[i, "observacao"] = obs
    df.at[i, "anotador"] = EU
    salvar()

print("Salvo.")