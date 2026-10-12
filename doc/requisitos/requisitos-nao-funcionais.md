# Requisitos não funcionais

Catálogo oficial do Documento de Requisitos do grupo (v1), levantado e priorizado da mesma
forma que os [requisitos funcionais](requisitos-funcionais.md): brainstorming e benchmark,
priorização MoSCoW, coluna de origem para rastreabilidade; ver
[Técnicas de elicitação](tecnicas-elicitacao.md).

| ID | Requisito | Descrição | Prioridade (MoSCoW) | Origem |
|----|---|---|---|---|
| RNF01 | Usabilidade | O sistema deve apresentar uma interface simples de compreender e utilizar, permitindo que o jogador identifique facilmente as ações disponíveis durante a partida. | Must have | Benchmark |
| RNF02 | Acessibilidade | O sistema deve utilizar elementos visuais e textuais que favoreçam a leitura e compreensão das informações apresentadas. | Should have | Benchmark |
| RNF03 | Responsividade | O sistema deve adaptar sua interface aos diferentes tamanhos de tela suportados. | Should have | Brainstorming e Benchmark |
| RNF04 | Desempenho | O sistema deve responder aos comandos do jogador sem atrasos perceptíveis durante a execução da partida. | Must have | Brainstorming |
| RNF05 | Tempo de carregamento | O sistema deve carregar as telas e elementos necessários para a execução do jogo dentro de tempo adequado para a utilização. | Should have | Brainstorming |
| RNF06 | Disponibilidade | O sistema deve permanecer disponível para utilização durante os períodos previstos para execução do jogo. | Should have | Brainstorming |
| RNF07 | Segurança da autenticação | O sistema deve proteger as credenciais dos jogadores durante o cadastro e o processo de autenticação. | Must have | Brainstorming |
| RNF08 | Proteção de senhas | O sistema não deve armazenar senhas em formato de texto puro. | Must have | Brainstorming |
| RNF09 | Controle de acesso | O sistema deve permitir que cada jogador acesse somente os dados e o progresso associados à sua própria conta. | Must have | Brainstorming |
| RNF10 | Integridade dos dados | O sistema deve preservar a integridade dos dados relacionados às contas, respostas, pontuação, níveis e progresso dos jogadores. | Must have | Brainstorming |
| RNF11 | Persistência de dados | Os dados necessários para a continuidade da jornada do jogador devem permanecer armazenados de forma consistente entre diferentes sessões. | Must have | Brainstorming |
| RNF12 | Consistência das informações | As respostas corretas, explicações, pontuação e regras apresentadas pelo sistema devem permanecer consistentes durante a execução do jogo. | Should have | Brainstorming |
| RNF13 | Compatibilidade | O sistema deve funcionar nos navegadores e ambientes definidos para a aplicação. | Must have | Brainstorming e Benchmark |
| RNF14 | Manutenibilidade | O sistema deve possuir uma estrutura que permita a manutenção e evolução das funcionalidades do jogo. | Should have | Brainstorming |
| RNF15 | Modularidade | Os componentes responsáveis por autenticação, jogo, níveis, pontuação, conteúdo e persistência devem possuir organização que facilite sua evolução. | Should have | Brainstorming |
| RNF16 | Escalabilidade | O sistema deve permitir a inclusão de novos conteúdos, afirmações e níveis sem exigir alterações estruturais em toda a aplicação. | Should have | Brainstorming |
| RNF17 | Confiabilidade | O sistema deve manter o estado da partida e os dados do jogador de forma consistente durante sua utilização. | Must have | Brainstorming |
| RNF18 | Recuperação de sessão | O sistema deve permitir a recuperação dos dados persistidos do jogador quando ele realizar uma nova autenticação. | Must have | Brainstorming |
| RNF19 | Privacidade | O sistema deve tratar os dados pessoais utilizados no cadastro e na autenticação de acordo com as regras de privacidade aplicáveis. | Should have | Brainstorming |
| RNF20 | Clareza das mensagens | As mensagens de erro, acerto, orientação e resultado devem ser apresentadas de forma clara e compreensível para o jogador. | Should have | Benchmark |
| RNF21 | Segurança da aplicação | O sistema deve adotar mecanismos de segurança destinados a reduzir riscos relacionados a acesso indevido, manipulação de dados e vulnerabilidades da aplicação. | Should have | Brainstorming |
| RNF22 | Auditabilidade | O sistema deve possibilitar o registro das informações necessárias para acompanhamento de eventos relevantes relacionados à utilização e à manutenção da aplicação. | Could have | Brainstorming |

## Resumo da priorização

| Categoria | RF | RNF | Total |
|---|---|---|---|
| Must have | 19 | 10 | 29 |
| Should have | 5 | 11 | 16 |
| Could have | 0 | 1 | 1 |

Won't have (fora do escopo atual) não consta nesta documentação: são requisitos
explicitamente postergados para iterações pós-MVP, delimitando o foco atual da equipe.
