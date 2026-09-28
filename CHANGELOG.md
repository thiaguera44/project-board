# Changelog

Todas as alterações relevantes deste projeto serão documentadas aqui.

## [Não publicado]

### Adicionado

- Atualizador integrado que consulta Releases do GitHub, avisa sobre versões novas, valida o executável baixado e reinicia o aplicativo após a substituição.
- Anexos em tarefas, com arquivos de até 20 MB, abertura pelo aplicativo padrão, remoção individual e preservação no arquivamento e backup.
- Notificações nativas do Windows para prazos próximos, tarefas atrasadas e tarefas desbloqueadas, com controle nas configurações e prevenção de alertas repetidos.
- Calendário mensal e semanal de prazos, com navegação por períodos, criação de tarefa em uma data, acesso à edição e relação de tarefas sem prazo.
- Tarefas recorrentes diárias, semanais ou mensais, com término opcional, próxima ocorrência automática e checklist reiniciado.
- Etiquetas personalizadas com cores, associação a tarefas, filtro rápido e preservação no backup.
- Anotações com autor e data dentro das tarefas, preservadas no arquivamento e no backup.
- Dependências entre tarefas, com bloqueios visíveis, validação de conclusão e proteção contra ciclos.
- Backup completo em JSON e restauração validada de projetos, tarefas, horas, histórico, cronômetros, perfil e personalização.
- Arquivamento e restauração de projetos e tarefas, preservando horas e histórico em uma área dedicada.
- Checklists nas tarefas, com criação, conclusão, reabertura, exclusão e progresso visível no Kanban.
- Avisos de prazo no cabeçalho e no Dashboard para tarefas atrasadas, com vencimento hoje ou nos próximos três dias.
- Personalização do nome do quadro e da paleta de cores, persistida entre as aberturas do aplicativo.
- Modos claro e escuro persistentes, aplicados também à janela flutuante dos cronômetros.
- Edição e exclusão de registros de horas pela tela de horas registradas.
- Relatórios com filtros de período e projeto, comparação entre estimado e realizado, atrasos, produtividade diária e exportação em CSV e PDF.
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

- Configurações da interface, cartões do Kanban, tela de etiquetas e regras de recorrência e dependências separados em módulos próprios.
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
- Suíte completa validada com 30 testes do backend e 5 grupos de testes do frontend.
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
