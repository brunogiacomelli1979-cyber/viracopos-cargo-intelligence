# Contratos dos indicadores · v2

| Arquivo / campo | Unidade | Medida |
|---|---|---|
| viracopos / carga_internacional_t | toneladas | RMA da concessionária, coluna INT*: importações + exportações |
| viracopos / carga_domestica_t | toneladas | RMA, coluna DOM |
| viracopos / courier_internacional_t | toneladas | RMA, quadro separado de cargas courier, coluna INT* |
| comex_viracopos / valor_fob_usd | US$ FOB | Soma de VL_FOB por mês × fluxo × capítulo SH2; URF 0817700 e via 04 |
| comex_viracopos / kg_liquido | kg líquidos | Soma de KG_LIQUIDO no mesmo recorte; interface divide por1.000 para toneladas líquidas |
| brasil / exportacoes_usd_bi, importacoes_usd_bi | US$ bilhões FOB | Totais nacionais dos arquivos EXP/IMP; sem filtro de via/URF |
| macro / selic_meta_pct_aa | % a.a. | SGS432: último registro disponível do mês |
| macro / dolar_venda_medio_brl | R$/US$ | SGS1: média aritmética dos dias publicados |
| macro / ipca_pct_mes | % mensal | SGS433; valores negativos são válidos |

Não há separação de embarque/desembarque no RMA usado. Não inferir esses sentidos nem somar courier automaticamente à carga comum: o documento apresenta colunas distintas sem explicar sobreposição. A versão anterior tinha somente um cabeçalho vazio com campos de sentidos; não existiam observações a migrar.

KPIs: carga internacional vem diretamente da coluna RMA; FOB de cada fluxo é a soma dos capítulos /1milhão; corrente Brasil é exportações + importações. Variação anual compara o mesmo mês de referência com o mês do ano anterior, quando existe denominador observado não nulo. Participação setorial é FOB do capítulo /total dos capítulos do fluxo na mesma competência. Denominador zero resulta em indisponível.

Uma linha por mês em carga, Brasil e macro; Comex por mês×fluxo×setor. Ausência macro é `null`/célula vazia; demais bases omitem competências ausentes. Zero só representa observação medida. Não conectar meses sem dados por uma linha contínua. A tabela setorial usa a última competência do fluxo dentro da janela, sem somar diferentes meses como se fossem uma competência.
