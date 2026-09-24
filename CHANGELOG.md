# Changelog

Todas as alterações relevantes deste projeto serão documentadas aqui.

## [Não publicado]

### Adicionado

- Personalização do nome do quadro e da paleta de cores, persistida entre as aberturas do aplicativo.
- Modos claro e escuro persistentes, aplicados também à janela flutuante dos cronômetros.
- Edição e exclusão de registros de horas pela tela de horas registradas.
- Relatórios com filtros de período e projeto, totais consolidados e exportação em CSV.
- Suíte automatizada executável por `test-project.ps1`, cobrindo os principais fluxos do backend e as conversões de duração do frontend.
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

- Tipos, cálculos de exportação e tela de relatórios separados em módulos próprios para facilitar manutenção.
- Mensagem de falha de conexão apresentada em português, com orientação para tentar novamente.
- Indicadores reorganizados em duas colunas em telas estreitas e nome completo do quadro exibido sem reticências.
- Preenchimento de durações em campos separados de horas e minutos.
- Apresentação dos tempos nas listas, tabelas e indicadores como `30min` ou `1h 15min`, preservando o armazenamento decimal existente.
- Validação de minutos entre 0 e 59 e de registros entre 1 minuto e 24 horas na interface.
- README atualizado com instalação, execução, API, regras e limitações atuais.
- Diário de aprendizado com etapas, evidências dos testes e verificações pendentes.

### Validação

- Layout validado em quatro larguras, sem transbordamento horizontal, e recuperação de conexão validada após interrupção da API.
- Suíte completa validada com 9 testes do backend e 4 grupos de testes do frontend.
- Edição de registros validada com preservação da data original; exclusão validada pela suíte automatizada.
- Exclusões e proteções validadas por testes automatizados, incluindo preservação dos registros de horas e do histórico.
- Executável avulso iniciado a partir de outra pasta, com interface e API local respondendo.
- Compilação do frontend e verificação do TypeScript concluídas com sucesso.
- Verificações pontuais de conversão e limites de duração concluídas com sucesso.
- Fluxos principais testados manualmente pelo autor; detalhes e limites no diário de aprendizado.

## [0.0.1] - 2026-06-18

### Added

- Estrutura inicial do projeto
- README
- Git
- .gitignore
