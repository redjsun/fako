# Conquistas

As conquistas são marcos de progresso que o jogador libera ao fim de cada partida. Todas
aparecem na tela **Minha jornada**, com a descrição e uma barra de progresso. As metas que têm
mais de um passo mostram também o contador (por exemplo, "3 / 5 seguidas").

O catálogo e as regras ficam em `web/src/utils/achievements.ts`. O cálculo roda só no front:
as conquistas ficam salvas no navegador (`localStorage`, chave `fako_stats_<usuário>`) junto
das estatísticas locais, e a API não guarda nem devolve conquistas. Por isso, trocar de
navegador ou limpar os dados do site zera as conquistas, mesmo que o nível e a pontuação
continuem na conta.

## Catálogo

| ID | Conquista | Como liberar | Progresso na Jornada |
|---|---|---|---|
| `first_check` | Primeira Checagem | Avaliar a primeira afirmação | 0 ou 100% |
| `bullseye` | Na Mosca! | Numa partida, marcar a confiabilidade exatamente igual à referência de uma afirmação | 0 ou 100% |
| `level_up` | Subindo de Nível | Chegar ao nível 2 | 0 ou 100% |
| `imune` | Muralha Antifake | Acertar 5 afirmações seguidas na mesma partida | maior sequência / 5 |
| `perfect` | Partida Perfeita | Terminar uma partida com pelo menos 5 respostas e nenhum erro | 0 ou 100% |
| `regular` | Checador Assíduo | Jogar 10 partidas | partidas / 10 |
| `hundred` | Cem Checagens | Avaliar 100 afirmações, somando todas as partidas | afirmações / 100 |
| `master` | Mestre dos Fatos | Chegar ao nível 6 | maior nível / 6 |

## Como funciona

- **Quando libera:** ao fim de cada partida, `authService.recordMatchFinished` atualiza as
  estatísticas e chama `unlockAchievements`. Cada regra compara um valor com a meta: as
  acumuladas (`first_check`, `level_up`, `imune`, `regular`, `hundred`, `master`) usam as
  estatísticas depois da partida; `bullseye` e `perfect` olham só as respostas da partida que
  terminou.
- **Não volta atrás:** uma conquista liberada continua liberada e mantém a data
  (`unlockedAt`) da primeira vez.
- **Conquistas novas para jogadores antigos:** ao ler as estatísticas salvas, o front parte do
  catálogo atual e copia o estado das conquistas que já existiam. As novas aparecem
  bloqueadas e são conferidas na próxima partida; quem já tinha, por exemplo, 10 partidas
  ganha `regular` assim que terminar a próxima.

## Como adicionar uma conquista

1. Inclua uma entrada em `ACHIEVEMENT_RULES` (`web/src/utils/achievements.ts`) com `id`,
   `title`, `description`, `target`, `unit` (se a meta tiver mais de um passo) e `value`.
   `value(stats, match)` devolve o progresso atual; `match` só existe ao fim da partida.
2. Se a regra precisar de um dado que ainda não está em `UserStats`, acrescente o campo em
   `web/src/types.ts` e acumule-o em `recordMatchFinished`.
3. Cubra a regra em `web/src/utils/achievements.test.ts` e atualize a tabela acima.

Não troque o `id` de uma conquista existente: é por ele que o estado salvo no navegador é
recuperado.
