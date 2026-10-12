# Requisitos não funcionais

Catálogo oficial do Documento de Requisitos do grupo (v1), levantado e priorizado da mesma
forma que os [requisitos funcionais](requisitos-funcionais.md): brainstorming e entrevista,
priorização MoSCoW, coluna de origem para rastreabilidade; ver
[Técnicas de elicitação](tecnicas-elicitacao.md).

| ID | Requisito | Descrição | Prioridade (MoSCoW) | Origem |
|----|---|---|---|---|
| RNF01 | Usabilidade | O sistema deve apresentar uma interface simples de compreender e utilizar, permitindo que o jogador identifique facilmente as ações disponíveis durante a partida. | Must have | Entrevista |
| RNF02 | Acessibilidade | O sistema deve utilizar elementos visuais e textuais que favoreçam a leitura e compreensão das informações apresentadas. | Should have | Entrevista |
| RNF03 | Responsividade | O sistema deve adaptar sua interface aos diferentes tamanhos de tela suportados. | Should have | Brainstorming e Entrevista |
| RNF04 | Desempenho | O sistema deve responder aos comandos do jogador sem atrasos perceptíveis durante a execução da partida. | Must have | Brainstorming |
| RNF05 | Tempo de carregamento | O sistema deve carregar as telas e elementos necessários para a execução do jogo dentro de tempo adequado para a utilização. | Should have | Brainstorming |
| RNF06 | Disponibilidade | O sistema deve permanecer disponível para utilização durante os períodos previstos para execução do jogo. | Should have | Brainstorming |
| RNF07 | Segurança da autenticação | O sistema deve proteger as credenciais dos jogadores durante o cadastro e o processo de autenticação. | Must have | Brainstorming |
| RNF08 | Proteção de senhas | O sistema não deve armazenar senhas em formato de texto puro. | Must have | Brainstorming |
| RNF09 | Controle de acesso | O sistema deve permitir que cada jogador acesse somente os dados e o progresso associados à sua própria conta. | Must have | Brainstorming |
| RNF10 | Integridade e consistência dos dados | O sistema deve preservar a integridade dos dados relacionados às contas, respostas, pontuação, níveis e progresso dos jogadores, mantendo o estado da partida e as informações exibidas (respostas corretas, explicações, pontuação, regras) consistentes durante toda a utilização. | Must have | Brainstorming |
| RNF11 | Persistência e recuperação entre sessões | Os dados necessários para a continuidade da jornada do jogador devem permanecer armazenados de forma consistente entre sessões e ser recuperados quando ele realizar uma nova autenticação. | Must have | Brainstorming |
| RNF13 | Compatibilidade | O sistema deve funcionar nos navegadores e ambientes definidos para a aplicação. | Must have | Brainstorming e Entrevista |
| RNF14 | Manutenibilidade | O sistema deve possuir uma estrutura que permita a manutenção e evolução das funcionalidades do jogo. | Should have | Brainstorming |
| RNF15 | Modularidade | Os componentes responsáveis por autenticação, jogo, níveis, pontuação, conteúdo e persistência devem possuir organização que facilite sua evolução. | Should have | Brainstorming |
| RNF16 | Escalabilidade | O sistema deve permitir a inclusão de novos conteúdos, afirmações e níveis sem exigir alterações estruturais em toda a aplicação. | Should have | Brainstorming |
| RNF19 | Privacidade | O sistema deve tratar os dados pessoais utilizados no cadastro e na autenticação de acordo com as regras de privacidade aplicáveis. | Should have | Brainstorming |
| RNF20 | Clareza das mensagens | As mensagens de erro, acerto, orientação e resultado devem ser apresentadas de forma clara e compreensível para o jogador. | Should have | Entrevista |
| RNF21 | Segurança da aplicação | O sistema deve adotar mecanismos de segurança destinados a reduzir riscos relacionados a acesso indevido, manipulação de dados e vulnerabilidades da aplicação. | Should have | Brainstorming |
| RNF22 | Auditabilidade | O sistema deve possibilitar o registro das informações necessárias para acompanhamento de eventos relevantes relacionados à utilização e à manutenção da aplicação. | Could have | Brainstorming |

## Resumo da priorização

Contagem após a fusão de duplicatas descrita em [Revisão v1 → v2](#revisao-v1-v2): RF13
(Controle das posições da cobra, Must have) saiu do catálogo funcional; RNF12 (Should have)
e RNF17 (Must have) saíram deste catálogo.

| Categoria | RF | RNF | Total |
|---|---|---|---|
| Must have | 18 | 8 | 26 |
| Should have | 5 | 10 | 15 |
| Could have | 0 | 1 | 1 |

Won't have (fora do escopo atual) não consta nesta documentação: são requisitos
explicitamente postergados para iterações pós-MVP, delimitando o foco atual da equipe.

## Revisão v1 → v2

### Duplicatas removidas

Três requisitos descreviam a mesma propriedade do sistema com o mesmo conteúdo em ordem
diferente:

- **RNF10 (Integridade dos dados), RNF12 (Consistência das informações) e RNF17
  (Confiabilidade)** diziam, cada um à sua maneira, que os dados e o estado do jogo devem
  permanecer corretos e consistentes durante o uso. Foram fundidos em um único RNF10
  (Integridade e consistência dos dados), que soma as entidades citadas nos três: contas,
  respostas, pontuação, níveis, progresso, estado da partida, explicações e regras.
- **RNF18 (Recuperação de sessão)** descrevia a mesma relação de persistência do RNF11
  (Persistência de dados), só invertendo a ênfase (RNF11 partia do armazenamento, RNF18
  partia da recuperação). Foi fundido no RNF11, renomeado para Persistência e recuperação
  entre sessões.

### Lacunas candidatas (v2)

O catálogo v1 não cobre requisitos não funcionais específicos de um produto com um
classificador de aprendizado de máquina no centro, categoria de requisito que só se aplica
desde que `pesquisa/ml/` entrou no projeto. Com base nos mesmos fundamentos de engenharia de
produto para IA usados para estruturar esta documentação (requisitos de dados, de modelo e
de confiabilidade/explicabilidade), faltam:

| ID proposto | Requisito | Descrição | Origem |
|---|---|---|---|
| RNF23 | Explicabilidade do classificador | Toda classificação exibida ao jogador ou ao admin deve poder expor os sinais que a embasaram (RF24), não só o resultado. | Sistema |
| RNF24 | Portão de qualidade do modelo | Nenhum modelo novo substitui o publicado sem comparação de métricas com o modelo em produção. | Sistema (`doc/planejamento-retreino.md`) |
| RNF25 | Resistência a atalhos | O classificador não deve aprender fonte, autor ou data como atributo; medido pelo teste de atalho a cada modelo novo. | Sistema (`pesquisa/ml/atalho.py`) |
| RNF26 | Desempenho da classificação | A geração diária de questões e a classificação sob demanda devem responder dentro de um tempo compatível com os jobs agendados. | Sistema |
| RNF27 | Reprodutibilidade dos experimentos | Cada modelo publicado deve ser rastreável até a versão exata dos dados, da configuração de treino e do código que o gerou. | Sistema |

Essas propostas ficam como insumo para a próxima revisão do Documento de Requisitos (v2).
