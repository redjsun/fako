# Diretório de Anotações (FAKO)

Este diretório contém os arquivos de anotação de equipe do projeto FAKO.
As anotações são versionadas no Git e associadas ao dataset pelo campo `id`.

## Estrutura esperada por registro
- `id`: identificador do registro no dataset
- `veracidade`: 'falso', 'enganoso', 'verdadeiro' (quando anotada/revisada)
- `tipo`: tipo de conteúdo desinformativo (ex: 'fabricado', 'manipulado', 'falso_contexto', 'enganoso', 'nenhum')
- `tipo_secundario`: opcional
- `pede_compartilhamento`: 0 ou 1
- `urgencia`: 0 ou 1
- `apelo_emocional`: 0 ou 1
- `ataque`: 0 ou 1
- `anotador`: identificador do anotador
- `observacao`: anotações complementares
