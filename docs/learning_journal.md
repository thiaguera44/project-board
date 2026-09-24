# Diário de aprendizado

## Primeira versão funcional — sessão de desenvolvimento e testes

### Objetivo

Construir e compreender, passo a passo, um sistema pessoal de projetos com Python/FastAPI, SQLAlchemy/SQLite e React/TypeScript/Vite, usando a imagem de referência como orientação visual.

### Etapas realizadas

1. Conferência da estrutura inicial e dos arquivos existentes.
2. Preparação do ambiente virtual Python e instalação do SQLAlchemy.
3. Inicialização da API e criação automática do banco SQLite.
4. Cadastro do projeto Project Board pela API.
5. Criação de uma tarefa, mudança de status e consulta ao histórico.
6. Registro simulado de 30 minutos pela API e consulta do resultado.
7. Instalação das dependências do frontend e verificação do TypeScript.
8. Criação dos estilos, compilação e abertura da interface conectada à API.
9. Testes manuais conduzidos pelo autor na interface, com orientação passo a passo.
10. Substituição do preenchimento decimal por campos separados de horas e minutos.

### Conceitos praticados

- **Ambiente virtual:** mantém as dependências Python do projeto separadas das demais instalações.
- **API:** recebe dados, valida os campos e oferece operações para o frontend.
- **Persistência:** o SQLite conserva os registros depois de atualizar a página ou reiniciar a aplicação.
- **Relacionamento:** cada tarefa aponta para um projeto pelo identificador `project_id`.
- **Estado da interface:** o React atualiza listas, formulários, filtros e indicadores com os dados da API.
- **Histórico:** a alteração de status cria um registro separado da tarefa.
- **Representação de duração:** a interface recebe horas e minutos; a API mantém horas decimais. Isso melhora o preenchimento sem exigir migração dos registros existentes.
- **Validação:** limites no formulário evitam valores inadequados, e a API também valida seus próprios campos.

### Resultados dos testes

Os resultados abaixo distinguem verificações executadas durante o desenvolvimento dos testes manuais relatados pelo autor. Não representam uma suíte automatizada completa.

| Fluxo | Verificação | Resultado/evidência |
|---|---|---|
| Ambiente Python | Dependências, inicialização e respostas da API | Executado: sem conflitos de dependências; API e documentação responderam |
| Primeiro projeto | Cadastro pela API e consulta ao SQLite | Executado: projeto encontrado no banco; autor confirmou a consulta |
| Tarefa pela API | Criação e mudança A fazer → Fazendo | Executado: tarefa e histórico retornados pela API |
| Horas pela API | Registro de 0,5 hora e nova consulta | Executado: lançamento vinculado à tarefa correta |
| Criação pela interface | Salvar tarefa, conferir quadro/tabela e atualizar página | Autor confirmou os três passos |
| Edição de tarefa | Alterar prioridade e estimativa | Autor confirmou o resultado |
| Kanban | Mover tarefa, consultar histórico e atualizar página | Autor confirmou a persistência |
| Horas pela interface | Registrar 30 minutos | Autor confirmou o registro na lista; a conferência inicial adicional de persistência não teve confirmação isolada antes da mudança de formato |
| Horas e minutos | Registrar 1h 15min pelo novo formulário | Autor confirmou funcionamento |
| Estimativa em minutos | Salvar 2h 45min e reabrir formulário | Autor confirmou funcionamento correto |
| Busca e filtros | Buscar título, combinar prioridade/status e limpar filtros | Autor informou teste concluído |
| Conclusão | Concluir tarefa, consultar indicadores e histórico | Autor confirmou sucesso |
| Segundo projeto | Criar projeto/tarefa e alternar filtro de projeto | Autor confirmou separação correta |
| Prazo vencido | Definir prazo anterior e depois concluir tarefa | Orientação fornecida; autor pediu o próximo passo sem confirmação específica dos valores |
| Durações inválidas | 0h 0min, 0h 60min e 24h 1min | Autor confirmou mensagens correspondentes; ausência de novos registros não foi confirmada separadamente |
| Edição de projeto | Renomear projeto e verificar tarefa vinculada | Autor confirmou sucesso |
| Compilação | TypeScript e build do Vite | Executados com sucesso após criação dos estilos e após alteração das durações |
| Conversões de duração | Formatação, limites e conversão de ida e volta de cada minuto entre 0 e 24h | Verificação automatizada pontual executada com sucesso; ainda não salva como suíte no repositório |
| Exclusões | Projeto com tarefas, tarefa com cronômetro, recursos inexistentes e preservação de horas/histórico | Cinco testes automatizados executados com sucesso |
| Layout responsivo | 1440×900, 1024×768, 740×800 e 390×844 | Sem transbordamento horizontal; grades adaptadas para 4, 2 e 1 coluna no Kanban e 2 colunas nos indicadores móveis |
| Falha de conexão | Interromper a API durante o salvamento e restaurá-la sem recarregar a tela | Mensagem em português exibida; nova tentativa concluída após a recuperação |
| Suíte automatizada | Executar `test-project.ps1` | 9 testes do backend, 4 grupos do frontend e verificação do TypeScript concluídos |

### Dificuldades e soluções

- O SQLAlchemy estava listado nas dependências, mas ainda não instalado: a instalação completou o ambiente.
- O arquivo de estilos era importado, mas não existia: foi criado antes de abrir o frontend.
- O ambiente restrito bloqueou downloads e a execução do processo auxiliar do Vite: as operações foram repetidas com permissão de execução apropriada.
- O preenchimento decimal era pouco intuitivo: foram introduzidos os campos Horas e Minutos e a formatação de duração nas telas.
- O instalador Python mostrou aviso de uma distribuição residual `~ip`; isso não impediu a instalação nem a inicialização. A limpeza desse resíduo não foi realizada.

### Limites da validação e próximos passos

- Confirmar explicitamente o resultado do teste de atraso e a ausência de registros após tentativas inválidas.
- O histórico atual cobre somente mudanças de status.
- Os dados simulados permanecem no banco local e devem ser distinguidos de trabalho real.

### Referências do projeto

- [Como iniciar e usar o sistema](../README.md)
- [Histórico de alterações](../CHANGELOG.md)
