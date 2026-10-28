# Catálogo de Indicadores — v1.0

**Projeto:** VCP Insights · Viracopos Cargo Intelligence  
**Criado em:** 28/10/2026  
**Situação:** especificação inicial, **não** comprovação de relações causais ou resultado de modelo.  
**Base:** [Biblioteca Científica](biblioteca-cientifica.md) e [auditoria da Etapa 2](AUDITORIA_BIBLIOTECA_2026-10-28.md).

## 1. Pergunta central e decisões

**Problema:** antecipar oscilações da demanda de carga em Viracopos e entender os possíveis determinantes por setor, fluxo e contexto econômico sem confundir populações estatísticas.

**Decisões apoiadas (futuras):** monitorar mudanças da demanda, priorizar investigações setoriais e dimensionar cenários de capacidade. Não automatizar decisões operacionais com modelos ainda não validados.

### Horizontes exploratórios

- **Curto prazo:** 1–3 meses à frente (prioridade inicial para capacidade e alertas).
- **Médio prazo:** 4–12 meses (planejamento tático e avaliação de ciclos).
- **Longo prazo:** 13–36 meses (cenários estruturais, dependentes de histórico mais extenso).
- Tais intervalos são escolhas de projeto, **não** defasagens demonstradas. Uma variável pode conter informação útil em mais de um horizonte. Testar cada hipótese com validação temporal.

## 2. Métricas-alvo prioritárias

| ID | Nome e unidade | Regra / grão | Fonte / campo | Frequência e cobertura atual | Limite e estado |
|---|---|---|---|---|---|
| ALVO-01 | **Carga internacional operacional**, toneladas | Competência mensal; valor publicado em INT* (importações + exportações) | Concessionária RMA; `data/viracopos.csv:carga_internacional_t` | Mensal, jan/2025–ago/2026 (20 meses) | **Alvo principal monitorado.** Não separa fluxos; não somar courier. Histórico insuficiente para previsão robusta |
| ALVO-02 | **Peso líquido aduaneiro por fluxo**, kg | Soma de `KG_LIQUIDO` por mês × importação/exportação (eventualmente SH2); URF 0817700, via 04 aérea | MDIC; `data/comex_viracopos.csv:kg_liquido` | Mensal, jan/2025–set/2026 (21 meses) | Alvo **secundário e distinto**; declaração aduaneira não equivale a tonelagem no RMA |
| ALVO-03 | **FOB aduaneiro setorial**, US$ | Soma `VL_FOB` por mês × fluxo × SH2 no mesmo recorte | MDIC; `data/comex_viracopos.csv:valor_fob_usd` | Mensal, jan/2025–set/2026 (21 meses) | Valor comercial, não receita do aeroporto nem peso físico |
| ALVO-04 | **Movimentação ANAC**, unidade conforme dicionário | Série separada por universo, sentido e medida | ANAC: Etapa Básica ou Movimentação Aeroportuária | A especificar / não integrada | **Candidato bloqueado** até contrato, vigência, ausências e reconciliação |

## 3. Indicadores explicativos candidatos

**Estado:** "integrado" significa presente na base atual, não que possua poder preditivo comprovado; "candidato" significa ainda sem integração/validação para o estudo.

| ID | Indicador, unidade e agregação desejada | Fonte e identificador | Cadência original → análise | Horizonte a testar | Hipóteses | Estado / cuidado |
|---|---|---|---|---|---|---|
| X01 | **Câmbio dólar venda**, R$/US$, média aritmética dos registros diários publicados | BCB/SGS 1; `data/macro.csv:dolar_venda_medio_brl` | Diária → mensal | 1–12m | H03 | Integrado desde jan/2022; testar comparabilidade com outros conceitos de câmbio |
| X02 | **Meta Selic**, % a.a., último registro disponível do mês | BCB/SGS 432; `data/macro.csv:selic_meta_pct_aa` | Diária → mensal | 3–12m | H03 | Integrado desde jan/2022; estoque de taxa e canal de transmissão com defasagem |
| X03 | **IPCA**, % mensal (não transformar em taxa anual sem definição) | BCB/SGS 433; `data/macro.csv:ipca_pct_mes` | Mensal | 3–12m | H03 / controle | Integrado desde jan/2022; taxa negativa válida |
| X04 | **Produção industrial Brasil**, índice base da publicação, com/sem ajuste sazonal identificados | IBGE PIM-PF | Mensal → mensal | 1–6m | H01 | Candidato; escolher série/setor, base e política de revisões |
| X05 | **Importações brasileiras por SH2**, US$ FOB e kg líquidos, fluxos separados | MDIC microdados EXP/IMP, sem filtro URF/via | Mensal | 1–12m | H02 | **Derivado futuro**, embora microdados já alimentem agregado Brasil; exige série setorial independente |
| X06 | **Exportações brasileiras por SH2**, US$ FOB e kg líquidos, fluxos separados | MDIC microdados EXP/IMP, sem filtro URF/via | Mensal | 1–12m | H02 | Derivado futuro; separar exportações/importações |
| X07 | **Comércio Brasil agregado**, exportação e importação US$ bilhões FOB; cada fluxo e eventual corrente | MDIC; `data/brasil.csv` | Mensal | 1–12m | H02 | Integrado jan/2025–set/2026; não é movimento de Viracopos |
| X08 | **Índice antecedente OCDE (CLI)**, índice e metodologia oficial | OCDE CLI, Brasil | Mensal → mensal | 1–12m | H04 | Candidato; série, revisões e interpretação ainda a validar |
| X09 | **WTO Goods Trade Barometer**, pontos do indicador e componentes, série conforme publicação | OMC/WTO | Periodicidade de divulgação própria → alinhamento temporal controlado | 1–12m | H04 | Candidato; global e com janela de divulgação específica, não interpolar automaticamente |
| X10 | **CTK/ACTK e fatores internacionais IATA**, toneladas-quilômetro e índices publicados | IATA Air Cargo Market Analysis | Mensal → mensal, se obtida série histórica licenciada | 1–12m | H04 | Candidato; CTK ≠ toneladas em terminal |
| X11 | **Preço do combustível / petróleo**, unidade a definir conforme série oficial | Fonte pública a selecionar | A definir | 1–12m | H02 / controle | Candidato ainda sem fornecedor/contrato; não inserir dados fictícios |
| X12 | **Custo de frete aéreo (yield/índice)**, unidade a definir | Fonte confiável a selecionar e verificar direitos de uso | A definir | 1–12m | H02 | Candidato sem fonte contratada; dados possivelmente proprietários |

**Critérios mínimos antes de integrar um X:** nome exato da série, publicador, URI estável, unidade, região, escopo, agregação, vigência/revisões, data da primeira divulgação, horário de coleta, tratamento dos nulos, regra de atraso e contrato de redistribuição.

## 4. Três KPIs de pesquisa e controles (não metas inventadas)

| Papel | Indicador | Fórmula/decisão |
|---|---|---|
| KPI primário 1 | Carga internacional operacional mensal | `ALVO-01` em t; analisa oscilação no universo operacional do RMA |
| KPI primário 2 | Peso líquido do Comex por fluxo e setor | `ALVO-02` em kg; identificar segmentos que mudam no universo aduaneiro, sem atribuir tonelagem de terminal |
| KPI primário 3 | Erro de previsão fora da amostra | MAE/MASE, por horizonte, quando houver histórico suficiente; comparar modelos com baseline ingênuo/sazonal |
| Guardrail 1 | Cobertura e disponibilidade | Contar meses observados, ausentes, revisados e defasagem da publicação; sem preenchimento automático de meses |
| Guardrail 2 | Consistência de universo e vazamento | Rejeitar mistura RMA–Comex–ANAC/IATA como medida homogênea e regressores indisponíveis na data da previsão |

**Sem metas numéricas nesta versão:** não há baseline validado de erro de previsão, nem série operacional extensa o suficiente.

## 5. Dicionário operacional e política de dados

- **Competência:** `AAAA-MM`; toda junção entre fontes deve preservar o mês da medida e também a data/hora de divulgação relevante na origem.
- **Grão:** uma linha/mês para RMA, Brasil e macro; mês × fluxo × SH2 para Comex; não somar meses ao apresentar um único mês ou misturar granularidades.
- **Unidades:** RMA em toneladas operacionais; MDIC em kg líquidos e US$ FOB; IATA em toneladas-quilômetro; índices macro não medem peso.
- **Faltantes:** ausência `null` para macro ou linha inexistente conforme contrato; não tratar indisponibilidade como zero.
- **Revisões:** guardar versão/recibo, coleta UTC e política de reconsulta; dados históricos revisados não simulam necessariamente conhecimento disponível na época.
- **Setores:** SH2 como recorte inicial; NCM/SH4 somente após mapear classificação temporal e critérios de harmonização.
- **População e geografia:** operações em Viracopos RMA, registros aduaneiros URF 0817700/via 04, Brasil nacional e mercados globais permanecem separados.
- **Atualização de pesquisa:** documentar série, último mês encerrado e latência real. Não considerar um mês conhecido antes de publicação efetiva.
- **Interpretação:** correlação não demonstra causalidade; testar estabilidade, quebras, pandemia e confundidores.

## 6. Protocolo de estudo a construir

1. **Ampliar históricos** de `ALVO-01` e `ALVO-02` e confirmar cobertura comparável, sem inventar competências.
2. Fixar **origem temporal de cada previsão**, horizonte em meses e disponibilidade real dos indicadores externos; proibir *look-ahead*.
3. Baselines: ingênuo e sazonal (somente com ciclos completos suficientes); separar conjunto de treino/teste por tempo.
4. Testar defasagens a partir de hipóteses documentadas, sem escolher a melhor defasagem no conjunto de teste.
5. Comparar regressão dinâmica/SARIMAX e outras técnicas proporcionais ao volume de dados; medir erro e incerteza.
6. Verificar comportamento por fluxo/setor quando a amostra permitir e traduzir o desempenho em cenários de demanda.
7. Registrar resultados negativos, instabilidade e intervalos; não publicar previsões operacionais sem qualidade comprovada.

## 7. Backlog para a v1.1

- Confirmar calendários históricos e revisões das séries IBGE/OCDE/OMC/IATA.
- Fechar contratos de petróleo, frete e eventuais indicadores de parceiros comerciais.
- Reconciliar conceitos e sentidos ANAC x concessionária antes de novas séries.
- Aumentar amostra histórica e testar fluxo de publicação com dados realmente disponíveis na época.
- Formalizar **matriz H01–H05 × indicadores × sinais esperados × explicações alternativas**, sem declarar efeitos como certos.

**Documentos relacionados:** [contratos vigentes](../indicadores.md) · [fontes operacionais](../fontes.md) · [backlog](../backlog.md) · [acervo ANAC](anac/README.md).
