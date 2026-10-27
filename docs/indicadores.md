# Contratos dos indicadores

| Campos | Unidade | Definição |
|---|---|---|
| brasil / exportacoes_usd_bi, importacoes_usd_bi | US$ bilhões FOB | Totais nacionais mensais arredondados na fonte atual |
| viracopos / embarque_internacional_t, desembarque_internacional_t | toneladas | Planejado: carga aérea internacional de SBKP por sentido/mês |
| comex_viracopos / valor_fob_usd | US$ FOB | Mês × fluxo × setor; recorte aduaneiro validado |
| comex_viracopos / kg_liquido | kg líquidos | Mesmo recorte; tabela divide por 1.000 para toneladas líquidas |
| macro / selic_meta_pct_aa | % a.a. | SGS 432: último registro do mês |
| macro / dolar_venda_medio_brl | R$/US$ | SGS 1: média dos dias disponíveis |
| macro / ipca_pct_mes | % mensal | SGS 433; deflação permitida |

KPIs: carga = embarque + desembarque; FOB por fluxo = soma dos setores / 1 milhão; corrente Brasil = exportação + importação. Cada série/fluxo mantém sua própria competência. Participação = FOB do setor / soma dos setores do fluxo na última competência dentro da janela. Se total for zero, participação indisponível. Os setores precisam ser exaustivos para representar participação no total URF.

Ausência macro: `null`/célula vazia. Demais conjuntos omitem meses ausentes; números de uma observação são obrigatórios. Gráficos não conectam lacunas. MoM, YoY e acumulado anual ainda não implementados.
