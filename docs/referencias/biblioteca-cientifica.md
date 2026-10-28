# Biblioteca de referências — v1.0

**Projeto:** VCP Insights · Viracopos Cargo Intelligence  
**Curadoria:** 28/10/2026  
**Escopo:** fatores determinantes da demanda de carga aérea, métodos de previsão e fontes de indicadores antecedentes.  
**Estado:** acervo bibliográfico inicial, **sem** estimação de modelo, coleta de novas séries ou alteração no dashboard.

> **Como ler o status:** "Resumo/metadados conferidos" significa que foram consultadas as páginas do editor ou repositório acadêmico, e **não** que o texto integral foi revisado. "Fonte institucional conferida" significa que a descrição institucional da base/metodologia foi consultada, não que o download dos dados foi auditado.

## 1. Estudos científicos — relevância direta

### REF-001 — Kupfer et al. (2017): fatores estruturais da carga aérea

- **Referência:** Kupfer, F.; Meersman, H.; Onghena, E.; Van de Voorde, E. *The underlying drivers and future development of air cargo*. Journal of Air Transport Management, 61, pp. 6–14 (2017).
- **DOI:** https://doi.org/10.1016/j.jairtraman.2016.07.002
- **Método:** modelo de correção de erros e cenários de desenvolvimento da carga aérea global.
- **Variáveis investigadas:** comércio de mercadorias, participação de manufaturados, tarifas de frete aéreo (yields) e petróleo.
- **Uso proposto:** formar o primeiro mapa de hipóteses macroeconômicas para carga internacional de Viracopos e testar relações de longo prazo.
- **Limites:** escopo global e janela histórica distinta de SBKP; elasticidades e efeitos não podem ser transferidos diretamente.
- **Status:** resumo e metadados conferidos em editora; texto integral não auditado.
- **Fonte:** https://www.sciencedirect.com/science/article/pii/S0969699715301678

### REF-002 — Alnıpak e Kale (2022): relações econômicas em painel

- **Referência:** Alnıpak, S.; Kale, S. *Determinants of Air Cargo Demand in The European Region*. Journal of Aviation, 6(2), pp. 118–125 (2022).
- **DOI:** https://doi.org/10.30518/jav.1053662
- **Método:** painel dinâmico com estimador GMM em 23 países europeus, dados de 2009–2018.
- **Variáveis investigadas:** comércio exterior, índice de produção industrial, IPC, câmbio, PIB per capita, população e investimentos aeroportuários, entre outras.
- **Resultados reportados no resumo:** persistência da demanda anterior; associação positiva com comércio exterior e produção industrial e associação inversa com a variação do IPC.
- **Uso proposto:** selecionar candidatos a indicadores antecedentes e testar defasagens por fluxo/setor, em vez de pressupor efeito contemporâneo.
- **Limites:** dados de países europeus, não de um terminal individual; associação estatística não demonstra causalidade.
- **Status:** resumo, autores e DOI conferidos na página da revista; texto integral não auditado.
- **Fonte:** https://dergipark.org.tr/en/pub/jav/article/1053662

### REF-003 — Nguyen, Tran e Ngo (2025): previsão com variáveis externas

- **Referência:** Nguyen, Q. H.; Tran, P. Q.; Ngo, P. D. *Air cargo traffic forecasting model: An empirical study in Vietnam using the SARIMA-X/(E)GARCH model*. Research in Transportation Business & Management, 59, art. 101268 (2025).
- **DOI:** https://doi.org/10.1016/j.rtbm.2024.101268
- **Método:** SARIMA-X/(E)GARCH com dados trimestrais do Vietnã, 1999–2022.
- **Variáveis investigadas:** comércio internacional, PIB, combustível aeronáutico e pandemia.
- **Uso proposto:** comparar um baseline de série temporal com modelos que adicionam regressores externos, respeitando a disponibilidade do dado na data da previsão.
- **Limites:** outra geografia e periodicidade; resultados de volatilidade não são automaticamente resultados de demanda mensal de SBKP.
- **Status:** resumo, autores e DOI conferidos na editora; texto integral não auditado.
- **Fonte:** https://www.sciencedirect.com/science/article/pii/S2210539524001706

### REF-004 — Magaña, Mansouri e Spiegler (2017): implicações operacionais

- **Referência:** Magaña, U.; Mansouri, S. A.; Spiegler, V. L. M. *Improving demand forecasting in the air cargo handling industry: a case study*. International Journal of Logistics Research and Applications, 20(4), pp. 359–380 (2017).
- **DOI:** https://doi.org/10.1080/13675567.2016.1263610
- **Método:** estudo de caso em empresa de movimentação de carga aérea.
- **Tema:** incerteza da demanda, limitações da previsão e impactos no dimensionamento de mão de obra e nas operações.
- **Uso proposto:** converter previsões em cenários de capacidade e recursos de terminal; definir critérios de valor operacional, além de erro estatístico.
- **Limites:** estudo de caso, não fornece parâmetros universais de demanda ou capacidade para Viracopos.
- **Status:** resumo e metadados conferidos na editora e repositório institucional; texto integral não auditado.
- **Fontes:** https://www.tandfonline.com/doi/full/10.1080/13675567.2016.1263610 · https://bura.brunel.ac.uk/handle/2438/13522

## 2. Referências metodológicas e indicadores de contexto

### REF-005 — Hyndman e Athanasopoulos (2021): validação de previsões

- **Referência:** Hyndman, R. J.; Athanasopoulos, G. *Forecasting: Principles and Practice*, 3ª ed., OTexts (2021; edição online atualizável).
- **Aplicação:** benchmarks ingênuo e ingênuo sazonal; decomposição; regressões e modelos de séries temporais; validação temporal com origem móvel; separação entre previsões *ex ante* e *ex post*.
- **Regra para VCP:** nunca usar dados futuros na construção do preditor; comparar alternativas com testes fora da amostra e horizontes explícitos.
- **Status:** conteúdo metodológico online consultado; não implementado nem testado no projeto.
- **Fontes:** https://otexts.com/fpp3/ · https://otexts.robjhyndman.com/fpp3/tscv.html · https://otexts.com/fpp3/regression.html

### REF-006 — OCDE: Composite Leading Indicators (CLI)

- **Instituição:** Organização para a Cooperação e Desenvolvimento Econômico (OCDE).
- **Aplicação:** sinais qualitativos antecipados de inflexões do ciclo econômico, incluindo série para o Brasil.
- **Limite:** o CLI não é previsão numérica da tonelagem de Viracopos; avalia movimentos relativos ao ciclo.
- **Status:** metodologia/dataset institucional conferidos; ainda não integrado.
- **Fonte:** https://www.oecd.org/en/data/datasets/oecd-composite-leading-indicators-clis.html

### REF-007 — OMC: Goods Trade Barometer

- **Instituição:** Organização Mundial do Comércio (OMC/WTO).
- **Aplicação:** indicador antecedente do comércio mundial de bens; componentes incluem pedidos de exportação, frete aéreo, contêineres, eletrônicos e matérias-primas.
- **Limite:** escala global, periodicidade e composição próprias; não substitui séries locais nem implica antecipação estatística demonstrada para SBKP.
- **Status:** descrição institucional e publicação de setembro/2026 conferidas; não integrado.
- **Fontes:** https://data.wto.org/dataset/wto_brm · https://www.wto.org/english/news_e/news26_e/wtoi_09sep26_481_e.htm

### REF-008 — IATA: Air Cargo Market Analysis

- **Instituição:** International Air Transport Association (IATA).
- **Aplicação:** tendências internacionais de demanda (CTK, toneladas-quilômetro), capacidade (ACTK) e fatores setoriais.
- **Limite fundamental:** **CTK/ACTK não são toneladas processadas no terminal**, assim como dados de transportadoras não são automaticamente dados do operador aeroportuário.
- **Status:** página da análise mensal de agosto/2026 conferida; nenhuma série importada.
- **Fonte:** https://www.iata.org/en/publications/economics/reports/air-cargo-market-analysis-august-2026/

## 3. Fontes estatísticas candidatas — catálogo inicial

| ID | Fonte oficial | Medidas relevantes | Uso pretendido | Cuidado |
|---|---|---|---|---|
| REF-009 | [MDIC/Comex Stat — dados abertos](https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta) | FOB em US$, kg líquidos, NCM, país, via e URF | Importação/exportação e composição setorial | Dados aduaneiros **não** representam tonelagem operacional; conferir tabelas de códigos e revisões |
| REF-010 | [IBGE — PIM-PF](https://www.ibge.gov.br/estatisticas/economicas/industria/9294-pesquisa-industrial-mensal-producao-fisica-brasil.html) | Índices mensais da produção industrial | Proxy de atividade manufatureira | Respeitar calendário de publicação, revisões e ajuste sazonal |
| REF-011 | [BCB/SGS — Selic meta 432](https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom) | Meta Selic diária (% a.a.) | Condições monetárias | Última observação do mês ≠ média mensal; data de disponibilização |
| REF-012 | [BCB/SGS — dólar venda 1](https://dadosabertos.bcb.gov.br/dataset/1-taxa-de-cambio---livre---dolar-americano-venda---diario) | Câmbio diário R$/US$ | Preço relativo das operações | Definir média/fechamento e distinguir da PTAX quando pertinente |

**IPCA mensal (SGS 433)** já está descrito em [indicadores](../indicadores.md) e em [fontes](../fontes.md) do projeto; permanece em uso, com verificação de metadados da série a aprofundar na etapa de catálogo. Este inventário bibliográfico não reprocessa nem substitui as bases hoje utilizadas.

## 4. Hipóteses para Viracopos (não testadas)

Horizontes abaixo são **faixas operacionais propostas**, não resultados dos artigos:

| ID | Hipótese falsificável | Horizonte inicial | Fonte candidata / variável-alvo |
|---|---|---|---|
| H01 | Mudanças na produção industrial precedem mudanças no peso líquido de importações de grupos SH relevantes | 1–6 meses | PIM-PF + MDIC kg líquido |
| H02 | Comércio internacional e composição de manufaturados ajudam a explicar variação de carga internacional, além de modelos apenas sazonais | 3–12 meses | MDIC + RMA da concessionária (populações separadas) |
| H03 | Câmbio e juros contribuem com informação preditiva incremental para setores selecionados | 3–12 meses | SGS 1/432 + MDIC setorial |
| H04 | Pedidos de exportação/CLI/atividade mundial antecipam alguma mudança da demanda aérea local | 1–12 meses | OMC/OCDE + série de interesse, sob validação temporal |
| H05 | Previsões por faixa de demanda podem contribuir para dimensionamento operacional | 1–3 meses | Carga operacional RMA + critérios futuros de capacidade, sem inferir horas de equipe existentes |

**Importante:** o RMA atual da concessionária registra carga internacional sem separação de importações e exportações; o Comex é por fluxo aduaneiro. H02 é uma comparação entre **medidas distintas**, não uma identidade. Para relações por modalidade física, precisaremos da família ANAC apropriada e conciliação documental.

## 5. Protocolo para aceitar uma hipótese como resultado do projeto

1. Fixar variável-alvo, universo estatístico, unidades, período e frequência antes de comparar números.
2. Mapear competência **e data real de disponibilização** de cada regressor; impedir vazamento temporal e revisar mudanças metodológicas.
3. Observar sazonalidade, quebras estruturais, pandemia e revisões históricas; registrar meses ausentes, sem imputação automática.
4. Analisar defasagens, estabilidade por subperíodo e confundidores; correlação isolada não permite linguagem causal.
5. Comparar com baseline ingênuo e sazonal, seguidos de modelos com variáveis externas, usando validação temporal e horizontes de 1, 3, 6 e 12 meses **somente se o histórico permitir**.
6. Reportar MAE/MASE e, quando apropriado, RMSE, intervalos e comparação fora da amostra. Descrever claramente quando dados insuficientes inviabilizam uma comparação.
7. Validar todo achado na unidade e no fluxo operacional correspondente antes de qualquer publicação no dashboard.

**Restrição inicial:** a série RMA operacional do painel tem somente 20 competências (jan/2025–ago/2026); isso é insuficiente para tratar sazonalidade anual e estabilidade de previsão como comprovadas. Antes de modelos mais sofisticados, priorizar [backfill e reconciliação](../backlog.md).

## 6. Priorização de leitura e decisões

1. **REF-001, REF-002 e REF-004:** definir mecanismo econômico e tradução operacional.
2. **REF-005:** desenhar protocolo de validação temporal e benchmarks.
3. **REF-003:** avaliar modelos com variáveis externas apenas após ampliar o histórico.
4. **REF-006 a REF-012:** especificar cadastro das séries com frequência, unidade, defasagem de publicação e revisões.

Próximo entregável: **Catálogo de Indicadores — v1.0** com alvo, fonte, unidades, disponibilidade, população e hipótese associada. Nenhum modelo foi ajustado nesta etapa.

Consulte também o [acervo ANAC](anac/README.md) e a [auditoria de integridade de 28/10/2026](anac/AUDITORIA_2026-10-28.md).
