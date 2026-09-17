# Changelog

Todas as alterações relevantes deste projeto serão documentadas aqui.

## [Não publicado]

### Adicionado

- Botões no Kanban para registrar horas manualmente ou iniciar o cronômetro da tarefa.
- Cronômetros simultâneos em tarefas diferentes, persistentes entre reinicializações, com controles individuais para registrar ou descartar.
- Pausa e retomada por cronômetro no Kanban e na janela flutuante, preservando o tempo acumulado ao fechar o aplicativo.
- Janela flutuante no aplicativo desktop para acompanhar os cronômetros enquanto o quadro está minimizado.
- Perfil local com nome de exibição editável e pedido de nome no primeiro uso.
- Nome do perfil como responsável padrão de novas tarefas, sem alterar tarefas existentes.
- Aplicativo de desktop para Windows, distribuído em um único `ProjectBoard.exe`.
- Script `build-desktop.ps1` para compilar o frontend e gerar o executável.
- Banco do aplicativo de desktop em `%LOCALAPPDATA%\Project Board`, preservado entre atualizações.
- API FastAPI para projetos, tarefas, registro de horas e consulta do painel.
- Persistência em SQLite com SQLAlchemy e criação automática das tabelas.
- Interface React com TypeScript e Vite, inspirada na referência visual.
- Cadastro, edição e exclusão de projetos e tarefas.
- Kanban com movimentação por arrastar e soltar e histórico de mudanças de status.
- Dashboard com indicadores, gráficos e tabela de tarefas.
- Busca e filtros por projeto, prioridade e status.
- Registro de tempo trabalhado com observação e estimativa por tarefa.
- Estilos adaptáveis à largura da tela.

### Alterado

- Preenchimento de durações em campos separados de horas e minutos.
- Apresentação dos tempos nas listas, tabelas e indicadores como `30min` ou `1h 15min`, preservando o armazenamento decimal existente.
- Validação de minutos entre 0 e 59 e de registros entre 1 minuto e 24 horas na interface.
- README atualizado com instalação, execução, API, regras e limitações atuais.
- Diário de aprendizado com etapas, evidências dos testes e verificações pendentes.

### Validação

- Executável avulso iniciado a partir de outra pasta, com interface e API local respondendo.
- Compilação do frontend e verificação do TypeScript concluídas com sucesso.
- Verificações pontuais de conversão e limites de duração concluídas com sucesso.
- Fluxos principais testados manualmente pelo autor; detalhes e limites no diário de aprendizado.
- Exclusões e edição/exclusão de registros de horas não devem ser consideradas validadas: estas últimas operações ainda não estão implementadas.

## [0.0.1] - 2026-06-18

### Added

- Estrutura inicial do projeto
- README
- Git
- .gitignore
