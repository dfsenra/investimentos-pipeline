### Bem Vindo!

Esta App foi desenvolvida para resolver um problema real (e pessoal): a gestão dos meus ativos!  
Sempre utilizei uma planilha de Excel, que de fato funciona relativamente bem. Porém quando o arquivo começa a ficar grande, com muitas abas, fórmulas e gráficos, a experiência fica lenta e ruim.  
Além disso, eu não tinha uma opção automática e robusta para manter os preços dos ativos atualizados.

Espero que essa aplicação sirva de inspiração para uma ferramenta de gestão de ativos cada vez melhor!

---

### Como esta App funciona?

Esta App armazena todos as informações em um banco de dados SQL, conforme tópicos abaixo:

#### 1. Fluxo

1) O usuário registra as transações (compra e/ou venda de ativos)
2) A App irá buscar cotações dos ativos que estão presentes na carteira (preços dos últimos 5 anos) e salvá-los no banco de dados
3) O usuário clica no botão "🔄 Atualizar Cotações"
4) O banco de dados alimenta os gráficos do Dashboard

**Nota 1:** Logs de transações, retornos realizados (ganhos/perdas) e performance geral são atualizados automaticamente  
**Nota 2:** Esta App possui um banco de dados persistente com pipeline incremental. Isso significa que a cada vez que os containers são reiniciados o banco de dados é atualizado somente para os dias sem dados ao invés de baixar todo os histórico dos ativos da carteira novamente.

---

#### 2. Recursos

##### 2.1 Aba Dashboard de Performance
1) Gráficos:  
        
        * Performance normalizada (base 100): Ao selecionar um ou mais ativos e/ou índices de mercado, o gráfico exibirá a performance do item.  
        * Preços (R$): Este gráfico é válido apenas para ativos. Índices possuem apenas dados de performance normalizada.  
        * Evolução Patrimonial: Exibe a posição consolidade da carteira ao longo do tempo, considerando o preço médio do seu patrimônio de cada dia.

2) Performance da Carteira:  
        
        * Exibe a performance geral da sua carteira atual  
        * Performance por Ativo: Exibe a performance de cada ativo da sua carteira atual  
                
**Nota**: Performances exibidas para somente os ativos que estão comprados.

3) Retornos Realizados:  
        
        * Exibe o saldo realizado acumulado, ou seja, o retorno total considerando todas as transações de vendas
        * Retorno detalhado por Ativo: Exibe o retorno acumulado de todas as transações de vendas por ativo

4) Índices de mercado:  

        * Por padrão esta App vem com dois índices de mercado: Ibovespa e S&P500.  
        * Caso queira incluir novos, adicione no arquivo indices.csv, localizado em /data/indices.csv  
        
**Nota:** Ao adicionar um novo índice atente-se ao formato dos dados, ticker utilizado pelo Yahoo Finance e potencial necessidade de limpeza e tratamento dos dados.

##### 2.2 Aba Registrar Operações

É aqui onde você irá registrar as transações de compra e venda dos seus ativos.

Importante: Como os dados são baixados do Yahoo Finance é importante incluir o ".SA" ao final do ticker de cada ativo.
Exemplo: Para Petrobrás > PETR3.SA ou PETR4.SA.

Não existem validações para impedir compras e/ou vendas em datas futuras, distinção entre Mercado à Vista ou Mercado Fracionário.
Essas peculiaridades ficam por conta do usuário, afinal é um aplicação de gestão pessoal e não para transações reais.

##### 2.3 Aba Log de Operações

Use essa aba para consultar o log completo de transações e também para excluir aquelas que forem necessário caso tenha inserido dados incorretos.
**Nota:** Após uma transação ser excluída o preço médio é recalculado, assim como o patrimônio acumulado.

---

#### 3. Por onde começar...

* Inicie na aba "Registrar Operações".  
* Após clicar em "Salva Transação" o banco de dados será automaticamente atualizado.  
* Aguarde um momento (veja ícone de loading do Streamlit no canto superior direito).  
* Por fim, clique em "🔄 Atualizar Cotações" para que os gráficos reflitam a nova transação.


#### Author:

Douglas Senra

