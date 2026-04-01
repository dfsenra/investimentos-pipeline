import pandas as pd
import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX
import pmdarima as pm

def executar_simulacao_cenarios(df_treino, pct_queda, pct_alta, dias_previsao=5):
    """
    df_treino: DataFrame com colunas ['data', 'preco_acao', 'preco_exog']
    pct_queda: Valor negativo (ex: -0.05 para -5%)
    pct_alta: Valor positivo (ex: 0.05 para 5%)
    """
    
    # 1. Preparar as séries (O SARIMAX quer os valores puros)
    y = df_treino['preco_acao']
    X = df_treino[['preco_exog']]
    
    # 2. Descobrir a melhor ordem (p, d, q) automaticamente
    # O auto_arima garante que a série vire estacionária se precisar
    modelo_busca = pm.auto_arima(
        y, 
        X=X, 
        seasonal=False, 
        stepwise=True, 
        suppress_warnings=True,
        error_action="ignore"
    )
    ordem_otimizada = modelo_busca.order
    
    # 3. Treinar o modelo final com a ordem descoberta
    modelo_final = SARIMAX(y, exog=X, order=ordem_otimizada).fit(disp=False)
    
    # --- TRADUÇÃO DA ROBUSTEZ (O que combinamos sobre o p-valor) ---
    # Pegamos o p-valor da variável exógena (geralmente é o primeiro parâmetro após os AR/MA)
    # No statsmodels, podemos buscar pelo nome da coluna em .pvalues
    try:
        p_valor = modelo_final.pvalues['preco_exog']
        if p_valor < 0.05:
            confianca = "Alta"
            msg_confianca = "Relação estatística forte confirmada."
        elif p_valor < 0.10:
            confianca = "Moderada"
            msg_confianca = "Correção existente, mas com ruído."
        else:
            confianca = "Baixa"
            msg_confianca = "Atenção: O fator externo não explica bem esta ação."
    except:
        p_valor = 1.0
        confianca = "Indeterminada"
        msg_confianca = "Não foi possível validar a correlação."

    # 4. Criar os cenários para os próximos X dias
    ultimo_valor_exog = X.iloc[-1].values[0]
    
    # Cenário Estável: preço do índice parado
    exog_estavel = pd.DataFrame({'preco_exog': [ultimo_valor_exog] * dias_previsao})
    
    # Cenários de Alta/Baixa: distribuindo o percentual total pelos dias
    # Ex: se o usuário quer 5% em 5 dias, subimos 1% ao dia
    passo_queda = pct_queda / dias_previsao
    passo_alta = pct_alta / dias_previsao
    
    exog_baixa = pd.DataFrame({'preco_exog': [ultimo_valor_exog * (1 + passo_queda * i) for i in range(1, dias_previsao + 1)]})
    exog_alta = pd.DataFrame({'preco_exog': [ultimo_valor_exog * (1 + passo_alta * i) for i in range(1, dias_previsao + 1)]})
    
    cenarios = {
        'Estável': exog_estavel,
        'Queda': exog_baixa,
        'Alta': exog_alta
    }
    
    # 5. Gerar as previsões e guardar os objetos completos para o gráfico
    resultados_tabela = []
    objetos_grafico = {}
    
    for nome, dados_exog in cenarios.items():
        previsao = modelo_final.get_forecast(steps=dias_previsao, exog=dados_exog)
        
        objetos_grafico[nome] = previsao
        
        # Pegamos o último dia da previsão para a tabela de resumo
        media_final = previsao.predicted_mean.iloc[-1]
        intervalo = previsao.conf_int(alpha=0.05).iloc[-1]
        
        resultados_tabela.append({
            'Cenário': nome,
            'Preço Estimado': round(media_final, 2),
            'Min': round(intervalo.iloc[0], 2),
            'Max': round(intervalo.iloc[1], 2)
        })
    
    # Retornamos um dicionário com tudo que o app.py vai precisar
    return {
        'tabela': pd.DataFrame(resultados_tabela),
        'previsoes_completas': objetos_grafico,
        'ordem_usada': ordem_otimizada,
        'confianca': confianca,
        'mensagem': msg_confianca,
        'p_valor': round(p_valor, 4)
    }