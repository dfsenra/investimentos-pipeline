![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![CI](https://github.com/dfsenra/investimentos-pipeline/actions/workflows/ci.yml/badge.svg)

## Objetivos do Projeto
Desenvolver uma ferramenta para gestão financeira pessoal com as seguintes funções:
```
* Interface 100% via Dashboard (Streamlit > Yfinance > SQL > Streamlit)
* Pipeline incremental para coleta de cotações dos ativos da carteira do cliente
* Dashboard com rendimentos, evolução patrimonial e índices do mercado
* Histórico de todas as transações salvas em banco de dados persistente
* Análise da série histórica e avaliação preditiva para suportar decisões
* Agente de IA especializado em finanças
```

## 🚧 Status do Projeto 🚧
Este projeto está em desenvolvimento ativo.

Andamento das ações:
```
-> Integração do pipeline com base de dados histórica - 100%
-> Normalização dos dados & Benchmarking - 100%
-> Migração de .csv para banco de dados - 100%
-> Dashboard interativo via Streamlit - 100%
-> Estatísticas da carteira & Gráficos - 100%
-> Log de registros - 100%
-> Melhorias nos layouts das abas - 100%
-> Correções de bugs - validações para dados entrada - 100%
-> Atualizar README.md - 100%
```

Próximos passos:
```
X Modelagem de séries temporais
X Análise preditiva para suportar tomada de decisões no portfolio
X Agente de IA
```

# Pipeline para coleta de preços de ativos no YFinance

## 1. Introdução: Arquitetura e Fluxo do pipeline

### 1.1 Estrutura de pastas
Escolha um local para extrair as pastas conforme estrutura abaixo:
```    
Investimentos/
│
├── dashboard
│   ├── __init__.py
│   ├── app.py
│   ├── db.py
│   ├── queries.py
│   └── tutorial_da_app.md      # Página inicial da App
│
├── docs/   
│   └── images/                 # Imagens desse README.md
│       
├── data/
│   └── indices.csv.            # Base com os indices de mercado
│
├── logs/
│   └── .gitkeep                # gerados automaticamente pelo pipeline
│
├── scripts/
│   ├── .env.example            # Renomeie para .env 
│   ├── __init__.py
│   ├── pipeline_incremental.py
│   ├── roteiro_central
│   └── sql
│       ├── schema.sql
│       └── views.sql
│
├── tests/
│   ├── test_data_files.py
│   └── test_pipeline_basic.py
│
│── README.md
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
└── .gitignore
```

### 1.2 Visão macro do fluxo

```
            ┌─────────────────┐
            │      Início     │
            │ (docker compose)│
            └───────┬─────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │     roteiro_central     │
        │                         │
        │ • criação banco SQL     │
        │ • criação tabelas/views │
        └───────────┬─────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │     pipeline_incre.   │◀──┐
        │                       │    │               
        │ • leitura indices.csv │    │
        │ • leitura banco SQL   │    │          
        │ • validações          │    │    
        │ • coleta yfinance     │    │
        │ • delay anti-rate     │    │
        │ • logging             │    │
        │ • SQL persistente     │    │
        └───────────┬───────────┘    │
                    │                ▲
                    ▼                │
            ┌────────────────┐       │   
            │   Streamlit    │       │
            │ (input manual) │       │
            │                │       │
            │ • ingestão SQL │       │            
            └───────┬────────┘       │
                    │                │
                    ▼                │
        ┌───────────────────────┐    │
        │     pipeline_incre.   │▶──┘
        └───────────┬───────────┘
                    │
                    ▼
         ┌────────────────────┐
         │        Logs        │
         │  (auditoria/hist.) │
         └────────────────────┘
```

## 2. Preparando o seu ambiente para o pipeline

### 2.1: Renomeie o arquivo .example.env

O arquivo .example.env contêm as credenciais para configuração do banco de dados postgreSQL.
Renomeie o arquivo removendo o `.example`, deixando apenas como `.env`. O arquivo ficará oculto na pasta.
Para ler o conteúdo do arquivo oculto, abra o terminal no caminho onde o arquivo está localizado e digite `cat .env`.
Caso precise editá-lo, abra o terminal no caminho onde o arquivo está localizado e digite "nano .env". Após editar, salve (`Ctrl + O`), pressione `Enter` e feche (`Ctrl + X`).

### 2.2: Criação do ambiente virtual via Docker

Abra o Docker (caso não tenha, faça o download/instalação antes de seguir).

Abra o terminal na raiz do projeto e digite o seguinte comando:
```bash
docker compose up --build
```
Serão criados três imagens e três containers para o projeto. 
#### Tela de progresso - Execução manual no terminal
![Terminal progress](docs/images/pipeline_terminal.png)

Pronto, agora a aplicação terá um ambiente dedicado para ela!
O dashboard ficará disponível em:

```bash
http://localhost:8501
```

Quando finalizar o uso da aplicação, acesse o terminal da pasta raiz do projeto e execute:
```bash
Ctrl + C                # Stop nos containers
docker compose down     # Caro queira remover os containers
```

#### Nota1:
Os dados ficam salvos dentro de um volume no Docker, então mesmo que os containers sejam removidos, ao retornar para a aplicação os seus dados estarão disponíveis.

#### Nota2:
A partir de agora as imagens e containers já estão criados no Docker e não precisam ser recriados. Para acessar a aplicação basta usar o "compose up -d" e "compose down".
```bash
docker compose up              # Iniciar os containers e rodar a aplicação
Ctrl + C                       # Stop nos containers
docker compose down            # Caro queira remover os containers
```  


Por fim, caso queira limpar o banco de dados basta remover os volumes:  
```bash
docker compose down -v         # Remove os containers e deleta os volumes
``` 

### 2.3: Como usar esta aplicação?  

Ao abrir o dashboard pelo navegador você será direcionado para a primeira aba "Como usar esta App".  
Lá você irá encontrar um breve material explicando como funciona a aplicação. No geral é muito simples, basta cadastrar as suas transações na aba "Registrar Operações" e consultar as tabelas, gráficos e log de transações gerados nas demais abas.

### 2.4: Alimentação do indices.csv  

Para índices de mercado o pipeline consulta o arquivo indices.csv. Caso queira incluir outros benckmark, edite este arquivo.  
**Nota:** Ao adicionar um novo índice atente-se ao formato dos dados, ticker utilizado pelo Yahoo Finance e potencial necessidade de limpeza e tratamento dos dados.

## 3. Testes

Testes básicos foram implementados usando `pytest` para validar:
- requisitos do arquivo indices.csv e estrutura de pastas
- lógica de execução básica do pipeline

Este testes estão integrados ao Git actions, portanto não precisam ser executados no seu ambiente.

Para rodar os testes localmente:
```bash
pytest
```

## 4. Ficou curioso? Veja algumas imagens da App em uso 

### Onde tudo começa - Registrando operações:  

#### <u>Aba "Registrar Operações"</u>
![Transacoes](docs/images/transacoes.png)


### Histórico de transações:  

#### <u>Aba "Log de Operações"</u>
![Log_operacoes](docs/images/log_operacoes.png)


### Aba de maior interesse, hehe - Performance e gráficos:  

#### <u>Aba "Dashboard de Performance" - Performance e Retornos</u>
![Performance_Retornos](docs/images/performance_retornos.png)


### Gráficos (mais bonitos que o Excel 😅)

#### <u>Aba "Dashboard de Performance" - Rentabilidade (base 100)</u>
![Rentabilidade_100](docs/images/rentabilidade_base_100.png)


#### <u>Aba "Dashboard de Performance" - Preços de ativos (R$)</u>
![Precos](docs/images/precos_ativos.png)


#### <u>Aba "Dashboard de Performance" - Evolução do Patrimônio</u>
![Patrimonio](docs/images/evolucao_patrimonio.png)

<h2>Desenvolvido por:</h2> 

Douglas Senra  
dfsenra@gmail.com

