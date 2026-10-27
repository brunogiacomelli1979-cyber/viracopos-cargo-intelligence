# Fontes e proveniência

Consulta documental em 27/10/2026. Metadados estruturados em `data/fontes.json`; observações com `mes` e intervalos de referência no snapshot. Compilação não equivale a coleta.

| Conjunto | Fonte primária | Escopo |
|---|---|---|
| Brasil | [MDIC / estatísticas](https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas) | Todas as vias; set/2026: 34,4 exportações e 26,7 importações em US$ bilhões FOB arredondados. Coleta original desconhecida; conferência manual documentada. |
| Brasil histórico futuro | [MDIC / consolidados](https://balanca.mdic.gov.br/balanca/publicacoes_dados_consolidados/pg.html) | Histórico oficial; documentar revisão ao substituir números arredondados. |
| SBKP | [ANAC / dados e estatísticas](https://www.gov.br/anac/pt-br/assuntos/dados-e-estatisticas) | Confirmar dicionário, sentidos, natureza e unidade; coletor pendente. |
| URF | [MDIC / dados brutos](https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta) e [Comex Stat](https://comexstat.mdic.gov.br/pt/geral) | Confirmar URF, via aérea e classificação; não equivale a movimento físico de SBKP. |
| Macro | [BCB / dados abertos](https://dadosabertos.bcb.gov.br/) | SGS 432: meta Selic; 1: dólar de venda; 433: IPCA. |

API SGS: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial=DD/MM/AAAA&dataFinal=DD/MM/AAAA`. Recibos por série registram URL consultada, número de observações, SHA-256 e instante UTC; última tentativa e erros em `dashboard.json/coleta_bcb`. Respostas brutas não são armazenadas; revisão posterior da fonte pode alterar a reprodução. A ausência nunca é preenchida artificialmente.
