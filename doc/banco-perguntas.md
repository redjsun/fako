# Banco de perguntas do jogo

> **Status:** decisões tomadas; nada implementado. Faltam escolher a API de notícias e
> ajustar o modelo `Question` da API e o mock do web (ver "Pendências").

## A pergunta é a afirmação

No jogo, o jogador vê uma afirmação entre aspas e responde "Qual é a confiabilidade desta
informação?" num slider de 0 a 100 (acerta a até 15 pontos da referência). A explicação e
a fonte só aparecem depois da resposta (`web/src/components/QuestionModal.tsx`).

**A afirmação mostrada é o mesmo texto que o classificador recebe e o mesmo formato do
treino.** Ela sai do prompt de extração (`api/app/prompts/extrair_afirmacoes_vN.txt`, #19),
que também padroniza o treino (`doc/padronizacao.md`):

- uma frase, de 12 a 25 palavras, autocontida: quem (nome completo e cargo), o quê e os
  detalhes que tornam o fato verificável, com o mesmo sentido da manchete;
- sem referência de tempo relativa, sem pontuação final, sem caixa alta.

Não há uma segunda reescrita para o jogo. Reescrever separa o texto que o jogador lê do
texto que o modelo avaliou, e no teste com o Fake.br uma versão mais longa chegou a trocar o
sujeito da notícia ("O governador de SP ajudou a planejar…", quando o texto acusava Dilma
Rousseff), o que invalida o rótulo.

## O contexto vai para a revelação

O que não cabe nas 25 palavras vai para os campos que aparecem depois da resposta:

| Campo | Conteúdo | Quando aparece |
|---|---|---|
| `afirmacao` | a frase extraída, ≤ 25 palavras | na pergunta |
| data | "circulou em 2024", da data da notícia ou da checagem | na pergunta (opcional) |
| `explicacao` | quem disse, onde circulou e o que a checagem concluiu, escrita pela LLM a partir do veredito e da URL da checagem, nunca da memória do modelo | depois da resposta |
| `fonte` | a agência que checou ou o veículo da notícia | depois da resposta |

A data pode aparecer para o jogador, mas **nunca entra no texto do treino nem no
classificador**: as classes têm épocas diferentes, e a data vira atalho.

## De onde vêm as perguntas

O banco é feito do zero, separado do dataset de treino:

- **Notícias** de uma API externa, **rotuladas pelo nosso classificador**.
- **Checagens** recentes da Fact Check API, que já é coletada todo dia
  (`coletar_factcheck.py --incremental`, `doc/planejamento-retreino.md`), com o veredito da
  agência. Garantem falsas e enganosas no banco: notícia de veículo quase sempre sai
  "verdadeira" no classificador.
- O Fake.br e as demais bases do dataset servem **só para o treino**. O Fake.br é política
  de 2016–2018, já datada, e não tem checagem para escrever a explicação.

Não há categorias: o banco é uma lista só (o mock com Saúde, Tecnologia e Conhecimentos
Gerais está desatualizado nisso).

## Referência

| Origem | Referência |
|---|---|
| notícia da API | nota do classificador, `100 × (P1 + P2) / 2` (`api/app/integrations/classificador_client.py`), conferida pelo revisor |
| checagem com veredito falso | ~10 |
| checagem com veredito enganoso (fora de contexto, exagerado...) | ~50 |

Cuidados por a referência das notícias vir do modelo:

- **Revisão humana obrigatória.** O revisor confirma ou corrige a nota antes de `validated`;
  sem isso o jogo ensina os erros do modelo como verdade.
- **Só nota firme vira pergunta.** Nota `incerto` (confiança abaixo do limiar `admin`) fica
  como rascunho para o revisor decidir, ou é descartada.
- **Sem volta para o treino.** Notícia rotulada pelo classificador não entra no dataset como
  rótulo, a não ser a que o revisor validou (aí com `origem_rotulo = equipe`); senão o modelo
  treina nos próprios palpites e reforça os erros.
- **Formato igual ao do treino.** A afirmação que o classificador avalia sai do mesmo prompt
  que padroniza o treino, então a nota vale para o formato que o modelo conhece.

## Fluxo

1. Em lote, fora da partida (o Qwen no Ollama leva ~10–13 s por texto): coletar as notícias
   e as checagens, extrair a afirmação com o prompt da #19, classificar a afirmação das
   notícias e escrever a explicação.
2. Tudo entra como `draft` (`QuestionStatus`, `api/app/models/question.py`) e só chega ao
   jogador depois da revisão humana (`validated`). O revisor confere sobretudo se a
   afirmação é fiel à manchete ou à alegação checada.
3. Registros que viram opinião (nenhuma afirmação checável) não viram pergunta.

## Pendências

- Escolher a API de notícias (termos de uso, limite de requisições, cobertura brasileira).
- API: `Question` guarda `is_true` e uma categoria obrigatória; precisa da referência de 0 a
  100 (ou da veracidade em três classes), da data e de deixar a categoria de lado.
- Web: o mock (`web/src/services/questionService.ts`) ainda tem categorias e perguntas fixas.
- A explicação das notícias não tem checagem por trás: escrever só o que a notícia diz
  (quem, onde, quando) e a nota do modelo, sem afirmar que foi verificada.
