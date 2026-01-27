import yfinance as yf
import pandas as pd
import numpy as np
from datetime import date, datetime
import logging
import os
import requests
import time
import smtplib
import sys
from email.message import EmailMessage
from dotenv import load_dotenv
import statistics

inicio_execucao = time.time()

# ===================================================================================================
# Função User Interface silencioso (prints ignorados no launchd)
# ===================================================================================================
MODO_INTERATIVO = sys.stdout.isatty()

def print_ui(msg):
    if MODO_INTERATIVO:
        print(msg)

# ===================================================================================================
# Função de Progresso - Feedback visual no terminal
# ===================================================================================================
def progresso(atual, total, prefixo="", largura=30):
    if not MODO_INTERATIVO:
        return
    percent = atual / total
    preenchido = int(largura * percent)
    barra = "█" * preenchido + "░" * (largura - preenchido)
    print(f"\r{prefixo} {barra} {int(percent*100)}% ({atual}/{total})", end="")
    if atual == total:
        print()   #quebra linha final

# ===================================================================================================
# Configuração de e-mail (autenticação via .env)
# ===================================================================================================
# Crie um arquivo .env no mesmo local do script Python com o seguinte conteúdo:
# EMAIL_SENHA_APP=SENHA_APP_DO_SEU_GMAIL (substituia pela senha app do seu gmail)
load_dotenv(dotenv_path="/Users/dfsenra/Documents/2. Documentos/Finanças/Investimentos/scripts/.env")

EMAIL_SENHA = os.getenv("EMAIL_SENHA_APP")
if not EMAIL_SENHA:
    raise RuntimeError("Defina EMAIL_SENHA_APP no arquivo .env")

EMAIL_REMETENTE = "cervejariagrajau@gmail.com"
EMAIL_DESTINO = "dfsenra@gmail.com"
SMTP_SERVIDOR = "smtp.gmail.com"
SMTP_PORTA = 587

def enviar_alerta(assunto, corpo):
    msg = EmailMessage()
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_DESTINO
    msg["Subject"] = assunto
    msg.set_content(corpo)

    with smtplib.SMTP(SMTP_SERVIDOR, SMTP_PORTA) as server:
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA)
        server.send_message(msg)

# ===================================================================================================
# Função para filtrar dividendos de FIIs
# ===================================================================================================
def validar_fechamento_por_mediana(df, ticker):
    """
    Valida se o fechamento do dia é um outlier com base nos retornos diários.
    Retorna (fechamento, erro)
    """

    try:
        fechamento = df["Close"].iloc[-1]

        # Histórico mínimo
        if len(df) < 30:
            return fechamento, None  # histórico insuficiente → aceita

        # Retornos diários
        retornos = df["Close"].pct_change().dropna()

        # Poucos retornos válidos
        if len(retornos) < 20:
            return fechamento, None

        media = retornos.mean()
        desvio = retornos.std()

        # Volatilidade muito baixa → estatística não confiável
        if desvio < 0.002:  # ~0.2% ao dia
            return fechamento, None

        retorno_dia = retornos.iloc[-1]
        z_score = abs((retorno_dia - media) / desvio)

        # Limite conservador
        if z_score > 6:
            return None, (
                f"Retorno diário fora do padrão histórico "
                f"(z={z_score:.2f}, retorno={retorno_dia:.2%})"
            )

        return fechamento, None

    except Exception as e:
        return None, f"Erro na validação estatística: {e}"

# ===================================================================================================
# Caminhos
# ===================================================================================================
TICKERS_PATH = "../data/tickers.csv"
OUTPUT_PATH = "../data/precos_fechamento.csv"
CHECKPOINT_DIR = "../data/checkpoints"
LOG_DIR = "/Users/dfsenra/Documents/2. Documentos/Finanças/Investimentos/logs"
LOG_FILE = f"{LOG_DIR}/coleta.log"

os.makedirs(CHECKPOINT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ===================================================================================================
# Logging
# ===================================================================================================
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logging.info("==== Início da coleta de preços ====")
print_ui("▶ Iniciando coleta de preços")

# ===================================================================================================
# Leitura dos tickers
# ===================================================================================================
tickers = pd.read_csv(TICKERS_PATH)["ticker"].tolist()
total = len(tickers)

print_ui(f"✔ Tickes carregados ({total} ativos)")

registros = []
ativos_descartados = []

print_ui("\n▶ Processamento individual dos tickers com time sleep (15s)")

# ===================================================================================================
# Coleta de preços - Ticker por ticker
# ===================================================================================================
for i, ticker in enumerate(tickers):
    try:
        logging.info(f"Processando {ticker}")

        df = yf.Ticker(ticker).history(
            period="3mo",
            auto_adjust=False,
            actions=False
        )

        # Remove candle do dia atual
        df = df[df.index.date < date.today()]

        if df.empty:
            raise ValueError("Sem dados válidos após filtros")
            print_ui(f"{ticker}: Sem dados válidos após filtros")

        # ============================================================================
        # Validação da cotação do ativo por mediana (evita coletar preço do dividendo)
        # ============================================================================
        fechamento, erro = validar_fechamento_por_mediana(df, ticker)

        if erro:
            logging.error(f"{ticker}: descartado - {erro}")
            ativos_descartados.append(f"{ticker} | motivo: {erro}")
            print_ui(f"{ticker}: descartado - {erro}")
            continue

        data_fechamento = df.index[-1].date()

        #Registra os ativos com valores válidos
        registros.append({
            "data": data_fechamento,
            "ticker": ticker,
            "fechamento": round(fechamento, 2)
        })

    except Exception as e:
        msg = str(e)
        logging.error(f"{ticker}: descartado - {msg}")
        ativos_descartados.append(f"{ticker} | motivo: {msg}")
        print_ui(f"{ticker}: descartado - {msg}")

    progresso(i + 1, total, prefixo="Processando")

    # =================================
    # Atraso agressivo anti-rate-limit
    # =================================
    time.sleep(15)

# ===================================================================================================
# Escrita CSV + Checkpoint
# ===================================================================================================
if registros:
    print_ui("\n▶ Salvando preços")
    df_out = pd.DataFrame(registros)

    df_out.to_csv(
        OUTPUT_PATH,
        index=False,
        sep=";",
        decimal=",",
        encoding="utf-8-sig"
    )

    data_execucao = datetime.now().strftime("%Y-%m-%d")
    checkpoint_path = f"{CHECKPOINT_DIR}/{data_execucao}_precos.csv"

    if not os.path.exists(checkpoint_path):
        df_out.to_csv(
            checkpoint_path,
            index=False,
            sep=";",
            decimal=",",
            encoding="utf-8-sig"
        )

    logging.info(f"Arquivo salvo com {len(registros)} registros")
    logging.info("==== Fim da coleta de preços ====")
    print_ui("✔ CSV principal salvo")
    print_ui("✔ Checkpoint diário salvo")

# ===================================================================================================
# Envio de alerta via e-mail, somente se houver erros
# ===================================================================================================
if ativos_descartados:
    corpo = "Os seguintes ativos foram descartados na coleta:\n\n"
    corpo += "\n".join(ativos_descartados)

    enviar_alerta(
        assunto="Alerta – Ativos descartados na coleta de preços",
        corpo=corpo
    )

    logging.warning("Alerta por e-mail enviado")
    print_ui(f"⚠ {len(ativos_descartados)} ativo(s) descartado(s) — Sugestão: atualize a base csv manutalmente")

# ===================================================================================================
# Resumo Executivo
# ===================================================================================================
tempo_total = time.time() - inicio_execucao
logging.info(f"Tempo total de execução: {tempo_total}")

print_ui("\n================ RESUMO DA EXECUÇÃO ================")
print_ui(f"✔ Ativos coletados : {len(registros)}")
print_ui(f"Ativos descartados: {len(ativos_descartados)}")
print_ui(f"Tempo total       : {tempo_total:.1f} segundos")
print_ui("===================================================")

