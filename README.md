# Pipeline para coleta de preços de ações, ETFs, FIIs etc no YFinance

## 1. Introdução: Arquitetura e Fluxo do pipeline

### 1.1 Estrutura de pastas
Escolha um local para extrair as pastas conforme estrutura abaixo:
```    
Investimentos/
│
├── data/
│   ├── tickers.csv             # mantenha esse arquivo com todos os ativos que deseja coletar preços.
│   ├── precos_fechamento.csv.  # gerado automaticamente pelo pipeline
│   └── checkpoints/
│       └── .gitkeep
│
├── logs/
│   └── .gitkeep                # gerados automaticamente pelo pipeline
│
├── scripts/
│   ├── coleta_precos.py
│   └── .env.example            # edite a sua SENHA_APP e renomeie para .env 
│
├── README.md
├── README_LAUNCHD.md
└── .gitignore
```

### 1.2 Visão macro da arquitetura

```
          ┌───────────────┐
          │ tickers.csv   │
          │ (input manual)│
          └───────┬───────┘
                  │
                  ▼
        ┌─────────────────────┐
        │ coleta_precos.py    │
        │                     │
        │ • leitura tickers   │
        │ • coleta yfinance   │
        │ • delay anti-rate   │
        │ • validação estat.  │
        │ • logging           │
        │ • checkpoint        │
        │ • alerta por e-mail │
        └───────┬─────────────┘
                │
        ┌───────┴───────────┐
        │                   │
        ▼                   ▼
┌──────────────────┐   ┌────────────────────┐
│ precos_fecham.   │   │ checkpoints diários│
│ (estado atual)   │   │ (auditoria/hist.)  │
└──────────────────┘   └────────────────────┘
                │
                ▼
        ┌─────────────────┐
        │ Excel / Power   │
        │ Query / Dash    │
        └─────────────────┘
```

### 1.3 Fluxo de execução do pipeline

```
1. launchd dispara automaticamente, mesmo com tela apagada/bloqueada (18:30)
2. Python inicia
3. tickers.csv é lido
4. Loop ticker a ticker
   ├── request yfinance
   ├── sleep 15s
   ├── filtro estatístico
   ├── log sucesso / descarte
5. precos_fechamentos.csv sobrescrito
6. checkpoint diário criado (se não existir)
7. e-mail enviado se houver descartes
8. logs finalizados
```

## 2. Preparando o seu ambiente para o pipeline

### 2.1: Criação do arquivo .env

Esse pipeline possui uma função que envia e-mail automaticamente em caso de erros durante a coleta de 
preços dos ativos. Não se preocupe, os e-mails são enviados somente quando ocorrem erros, ou seja, sem spam. Caso a coleta seja
concluída com sucesso, nada será enviado.
Para que o e-mail seja disparado, eu utilizei uma conta gmail como remetente. Para isso será necessário criar uma
SENHA_APP. Existem alguns tutorais na internet muitos simples mostrando como fazer isso.

Após criar a sua SENHA_APP, abra o arquivo ".env.example" com um editor de texto e substitua "SENHA_APP_DO_SEU_GMAIL" pela sua senha:
```
EMAIL_SENHA_APP=SENHA_APP_DO_SEU_GMAIL

```
Salve o arquivo e renomeie removendo o ".example". Deixe apenas como ".env". O arquivo ficará oculto na pasta.
Caso precise editá-lo, abra o terminal no caminho onde o arquivo está localizado e digite "cat .env". Edite, salve e feche.

Veja abaixo um exemplo de e-mail recebido pelo pipeline:
![Terminal progress](docs/images/pipeline_terminal.png)


#### Nota3:
Nunca versionar o arquivo .env. O repositório contêm apenas o arquivo .env.example como referência.

### 2.2: Alimentação do tickers.csv
O pipeline inicia a sua busca através dos ativos listados dentro do arquivo "tickers.csv" que deve estar na pasta "data".
Portanto, para a sua rotina, mantenha esse arquivo atualizado com os ativos do seu portfolio, sempre com o nome "tickers.csv".
Essa atualização pode ser manual ou automatizada a depender de como você faz a sua gestão financeira.

### 2.3: Automatização do pipeline no MacOS

Caso queira automatizar esse pipeline, siga as instruções do README_LAUNCHD.
Eu particularmente acho isso muito prático, pois o meu computador rodar o pipeline automaticamente todo dia
as 18:30h, após fechamento do mercado. Dessa forma, a minha base de dados é alimentada automaticamente todos os dias
com as cotações do dia anterior, sem que eu precise fazer nada.


<h2>Author:</h2> 

Douglas Senra



```python

```
