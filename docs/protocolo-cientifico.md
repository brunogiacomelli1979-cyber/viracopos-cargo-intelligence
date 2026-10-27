# Protocolo científico VCP-SCI-01

## Objetivo e estimando
Explicar e, futuramente, prever a movimentação internacional mensal em toneladas do RMA da concessionária de Viracopos. Diferenciar explicação retrospectiva, associação estatística e previsão fora da amostra. Courier e carga doméstica permanecem separados. Comex (URF 0817700/via 04 aérea, valor FOB e peso líquido) mede declarações, não toneladas operacionais do RMA. Brasil é contexto nacional, não um subconjunto do aeroporto.

## Qualidade e pré-processamento
Um mês/observação nas séries RMA, Brasil e macro; Comex por mês × fluxo × setor SH2. Validar fontes, fechamento mensal, unicidade, valores, unidades, lacunas, datas de publicação e revisões. Ausências não equivalem a zero; não imputar silenciosamente. Alinhar meses por interseção e registrar tamanho da amostra. Variáveis preditoras só podem entrar se estivessem publicadas na data da origem de previsão.

## Cálculos estatísticos
Média = soma/n; desvio padrão **amostral** = raiz(soma[(x−média)²]/(n−1)); CV=100 × s/média se média diferente de zero. MoM = 100×(x_t/x_(t−1)−1) somente com meses consecutivos observados; YoY usa o mesmo mês do ano anterior e base diferente de zero. YTD deve comparar a mesma sequência completa de meses de janeiro até m nos dois anos. Sinalizar ausências e intervalos incompletos. Não inferir erro de fonte a partir de um outlier sem exame documental.

## Plano de inferência — NÃO executado
Investigar, por hipótese, atividade industrial, câmbio, Selic, IPCA e comércio exterior com definições e calendário de divulgação. Avaliar gráficos, tendência, diferenças, autocorrelação, sazonalidade, estacionariedade quando amostra suficiente, mudanças de regime e influência de outliers. Correlação em níveis pode ser espúria; não exibir p-valores ingênuos em séries autocorrelacionadas. Pré-registrar defasagens (candidatas: 0,1,3,6 meses), evitar busca oportunista e examinar múltiplas comparações. Precedência preditiva não demonstra causalidade econômica. Com 20 observações operacionais não declarar relações estatisticamente estáveis.

## Plano de previsão — NÃO validado
Baselines: naïve de último mês e seasonal naïve do mesmo mês anterior. Depois, se a base permitir, ETS/ARIMA e regressão dinâmica com fatores exógenos disponibilizados à data da previsão. Validar por origem móvel crescente, sem embaralhamento, com horizontes 1,3,6,12 avaliados em separado. Medir MAE, RMSE, WAPE (apenas quando soma das realizações >0), viés, estabilidade e cobertura de intervalos. Limiar operacional preliminar para backtest h=1: pelo menos 24 meses iniciais de treino e 12 de teste para naïve; pelo menos 36 +12 para sazonal. São regras conservadoras do projeto, NÃO provas universais de suficiência. Sem histórico suficiente, bloquear publicação de previsões.

## Estado verificável 27/10/2026
IMPLEMENTADO: contratos de dados, recibos, indicadores descritivos, comparações de meses correspondentes e testes das funções; o script auditar_metodologia.py reporta explicitamente bloqueios de modelos.
PENDENTE: revisão completa de todos os documentos originais; auditoria quantitativa independente dos microdados anuais brutos; testes de estacionariedade/ACF, inferência com variáveis externas, análises de defasagem, backtesting real, modelos calibrados e intervalos. Não confundir especificação com aplicação.

## Referências e papéis
- Hyndman, R. J. & Athanasopoulos, G. (2021). Forecasting: Principles and Practice, 3ª ed. https://otexts.com/fpp3/ ; rolling-origin https://otexts.robjhyndman.com/fpp3/toolbox.html — benchmarks, validação e métricas.
- NIST/SEMATECH e-Handbook of Statistical Methods: https://www.itl.nist.gov/div898/handbook/pmc/section4/pmc4.htm ; autocorrelação https://www.itl.nist.gov/div898/handbook/eda/section3/autocopl.htm — dependência temporal e validade inferencial.
- Fonte operacional: https://www.viracopos.com/pt_br/institucional/estatisticas-e-publicacoes.htm ; comércio: https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta ; economia: https://dadosabertos.bcb.gov.br/.
- Linhagem, escopo e versões: data/fontes.json, docs/indicadores.md e scripts/auditar_metodologia.py.
