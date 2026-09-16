# Project Board

Sistema de gerenciamento de projetos desenvolvido por Thiago Rocha para uso pessoal e estudo de desenvolvimento de software.

## Objetivo

Organizar projetos de trabalho com um painel Kanban, controle de horas, acompanhamento de prazos e indicadores de produtividade. O projeto também funciona como laboratório de aprendizado de desenvolvimento de software.

## Estado atual

Primeira versão funcional para execução local, com frontend conectado à API e persistência em SQLite. Os principais fluxos foram testados manualmente durante o desenvolvimento. Consulte o [diário de aprendizado](docs/learning_journal.md) para os resultados e as pendências de validação.

## Tecnologias

- **Backend:** Python, FastAPI, SQLAlchemy e SQLite.
- **Frontend:** React, TypeScript, Vite e Lucide React (ícones).

## Funcionalidades disponíveis

- Cadastro, edição e exclusão de projetos e tarefas.
- Tarefas com projeto, responsável, prioridade, prazo e tempo estimado.
- Kanban com os status A fazer, Fazendo, Em aguardo e Concluído.
- Movimentação por arrastar e soltar ou edição do status no formulário.
- Registro manual de tempo trabalhado com observação.
- Preenchimento de estimativas e registros em campos separados de horas e minutos.
- Exibição de durações como `30min`, `1h` e `1h 15min`.
- Dashboard com indicadores, distribuição das tarefas por prioridade, horas por projeto e percentual concluído.
- Busca de tarefas por título, responsável ou nome do projeto; busca de projetos por nome.
- Filtros de tarefas por projeto, prioridade e status.
- Histórico de mudanças de status.
- Layout adaptável à largura da tela.

## Como executar no Windows (PowerShell)

### Aplicativo de desktop

O aplicativo empacotado fica em `dist/ProjectBoard.exe`. Ele pode ser copiado sozinho para a Área de Trabalho ou outra pasta. Não é necessário iniciar Python, Node.js ou dois servidores manualmente. Os dados ficam em `%LOCALAPPDATA%\Project Board\project_board.db` e permanecem disponíveis após recompilar ou mover o executável.

Para gerar ou atualizar o executável a partir do código, instale Python, Node.js e npm; crie o ambiente virtual conforme a seção abaixo; e execute na raiz do projeto:

```powershell
.\build-desktop.ps1
```

O script instala as dependências, compila o React e gera `dist/ProjectBoard.exe`. Esta versão foi preparada para Windows. Para levar os dados de uma execução anterior do projeto, feche o aplicativo e copie `backend/project_board.db` para `%LOCALAPPDATA%\Project Board\project_board.db` antes de abri-lo novamente.

### Execução para desenvolvimento

#### Pré-requisitos

Tenha Python e Node.js com npm instalados. O ambiente usado na validação foi Python 3.12.0, Node.js 18.20.8 e npm 10.8.2; estas são as versões observadas, não uma recomendação de versões para produção.

Abra o terminal na pasta raiz `project-board`. Os comandos abaixo usam diretamente o Python do ambiente virtual, sem precisar ativá-lo.

#### 1. Preparar o backend

Se a pasta `backend/.venv` ainda não existir, crie o ambiente virtual:

```powershell
python -m venv backend/.venv
```

Instale as dependências:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Inicie a API a partir da raiz do projeto:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Mantenha esse terminal aberto. Endereços:

- [API](http://127.0.0.1:8000/)
- [Documentação interativa](http://127.0.0.1:8000/docs)

#### 2. Preparar o frontend

Abra um segundo terminal na raiz do projeto:

```powershell
cd frontend
npm ci
npm run dev -- --port 5173 --strictPort
```

O comando `npm ci` instala as versões registradas no arquivo de dependências; só precisa ser repetido ao preparar o ambiente ou atualizar dependências.

Acesse o [Project Board](http://127.0.0.1:5173/). O Vite encaminha as chamadas `/api` para a API na porta 8000. Ambos os servidores precisam estar em execução.

Para encerrar cada servidor, pressione `Ctrl+C` no respectivo terminal. Para voltar a usar o sistema, execute novamente os comandos de inicialização da API e do frontend; não é necessário reinstalar tudo.

#### 3. Verificar a compilação do frontend

Dentro da pasta `frontend`:

```powershell
npm run build
```

Esse comando verifica o TypeScript e gera os arquivos em `frontend/dist`. A configuração atual de comunicação com a API é para o servidor de desenvolvimento; uma publicação precisa de configuração própria de hospedagem e encaminhamento de `/api`.

## Primeiro uso

1. Abra **Projetos** e cadastre um projeto.
2. Clique em **Abrir quadro** e crie uma tarefa.
3. Movimente a tarefa pelo Kanban.
4. Em **Horas registradas**, selecione a tarefa e registre o tempo trabalhado.
5. Consulte os indicadores do **Dashboard** e o **Histórico**.

Uma instalação com banco novo começa vazia. Os projetos e registros simulados usados durante os testes pertencem ao banco local, não são dados carregados automaticamente.

## Regras e limites atuais

- Minutos aceitos nos formulários: de 0 a 59, com horas e minutos inteiros.
- Cada registro de trabalho na interface deve ter entre 1 minuto e 24 horas.
- Estimativas podem ser zero e têm limite de 100.000 horas.
- A API e o banco ainda armazenam horas decimais; a conversão é feita pelo frontend. Por exemplo, 1h 30min corresponde a `1.5` na API. Valores existentes são exibidos com arredondamento ao minuto mais próximo.
- Os indicadores do dashboard consideram as tarefas filtradas. Projetos ativos são os projetos com pelo menos uma tarefa não concluída no conjunto filtrado.
- Uma tarefa é atrasada quando tem prazo anterior à data atual e não está concluída.
- Um projeto com tarefas não pode ser excluído: primeiro é necessário transferir ou excluir suas tarefas.
- Excluir uma tarefa preserva os registros de horas e as movimentações anteriores. Esses registros continuam nas respectivas listas; o dashboard soma horas das tarefas ainda presentes no conjunto filtrado.
- O histórico registra mudanças de status, não todas as alterações dos campos.
- A lista de horas apresenta o total geral, sem aplicar os filtros de tarefas.

## Dados e estrutura

Na execução para desenvolvimento, o banco `backend/project_board.db` é criado automaticamente na primeira inicialização da API. No aplicativo de desktop, o banco fica em `%LOCALAPPDATA%\Project Board\project_board.db`. Para fazer uma cópia de segurança simples, encerre a API ou o aplicativo antes de copiar esse arquivo.

```text
project-board/
├── backend/
│   ├── app/main.py          # API, modelos e regras de persistência
│   ├── requirements.txt     # Dependências Python
│   └── project_board.db     # Banco local, criado ao iniciar a API
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Telas e integração com a API
│   │   ├── duration.ts      # Conversão e apresentação de durações
│   │   ├── main.tsx         # Entrada do React
│   │   └── styles.css       # Estilos e adaptação de layout
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.ts
├── docs/learning_journal.md
├── assets/
├── README.md
├── CHANGELOG.md
└── .gitignore
```

## API disponível

| Método | Caminho | Finalidade |
|---|---|---|
| GET | `/` | Identificação da API |
| GET | `/api/board` | Consultar projetos, tarefas, horas e histórico |
| POST | `/api/projects` | Criar projeto |
| PUT | `/api/projects/{project_id}` | Atualizar projeto |
| DELETE | `/api/projects/{project_id}` | Excluir projeto sem tarefas |
| POST | `/api/tasks` | Criar tarefa |
| PUT | `/api/tasks/{task_id}` | Atualizar tarefa e registrar mudança de status |
| DELETE | `/api/tasks/{task_id}` | Excluir tarefa |
| POST | `/api/entries` | Registrar horas trabalhadas |

Os formatos dos campos e exemplos de requisição estão disponíveis na documentação interativa da API em execução.

## Pendências

- Testar exclusões e a proteção de projetos com tarefas.
- Testar falhas de conexão e diferentes tamanhos de tela de forma sistemática.
- Criar uma suíte de testes automatizados persistente.
- Permitir edição e exclusão de registros de horas.
- Implementar relatórios e exportação.
- Separar o código em módulos e componentes menores conforme o projeto evoluir.

A versão atual não possui autenticação, gestão de equipes ou configuração de produção. Seu uso previsto é local e pessoal.

## Autor

Thiago Rocha
