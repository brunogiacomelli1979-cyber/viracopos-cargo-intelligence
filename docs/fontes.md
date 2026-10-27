# Fontes e proveniência · v2

Dados coletados em 27/10/2026. Instantes, URLs, SHA-256, unidades e limites em `data/fontes.json`. Compilação não equivale a coleta; recibos anteriores são conservados quando uma fonte falha.

## Carga operacional · RMA da concessionária

Índice oficial: [Estatísticas e publicações de Viracopos](https://www.viracopos.com/pt_br/institucional/estatisticas-e-publicacoes.htm).

- [RMA dezembro/2025](https://www.viracopos.com/data/files/13/F7/A2/6E/FA84C9101B0E52C9F01849A8/RMA%202025%20DEZ.pdf): 12 competências. Controles publicados: internacional 184.647 t, doméstica 87.064 t, courier internacional 9.705 t.
- [RMA agosto/2026](https://www.viracopos.com/data/files/8C/12/E0/C6/265C0A10F5D2680AD41849A8/RMA%202026%20AGO.pdf): 8 competências. Controles: internacional 133.876 t, doméstica 61.357 t, courier internacional 7.542 t.

Página 1, cabeçalhos de Movimentação de Cargas e Courier, unidade toneladas e nota INT*: importações + exportações. Extração reconciliada e conferida visualmente no PDF. Não é série ANAC, não separa sentidos e não autoriza somar courier à carga comum. Os meses set–dez/2026 estão em branco no boletim consultado e são omitidos.

## Comércio exterior · MDIC

[Dados brutos oficiais](https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta). Arquivos completos lidos em streaming, sem guardar os microdados anuais no repositório:

- [Exportações 2025](https://balanca.mdic.gov.br/balanca/bd/comexstat-bd/ncm/EXP_2025.csv) e [importações 2025](https://balanca.mdic.gov.br/balanca/bd/comexstat-bd/ncm/IMP_2025.csv).
- [Exportações 2026](https://balanca.mdic.gov.br/balanca/bd/comexstat-bd/ncm/EXP_2026.csv) e [importações 2026](https://balanca.mdic.gov.br/balanca/bd/comexstat-bd/ncm/IMP_2026.csv).

Recorte validado nas tabelas [URF](https://balanca.mdic.gov.br/balanca/bd/tabelas/URF.csv):0817700 Aeroporto Internacional de Viracopos; [VIA](https://balanca.mdic.gov.br/balanca/bd/tabelas/VIA.csv):04 AEREA. Setores por capítulo SH2 e descrição da [NCM_SH](https://balanca.mdic.gov.br/balanca/bd/tabelas/NCM_SH.csv). FOB em dólares; peso líquido em kg. Importação/exportação são fluxos independentes, não sentidos do RMA.

Brasil usa todas as linhas dos mesmos arquivos, sem filtro de via/URF; soma mensal dividida por 1 bilhão. Os13 meses em comum reconciliam com a [tabela nacional consolidada](https://balanca.mdic.gov.br/balanca/publicacoes_dados_consolidados/pg.html), cujo arredondamento é de US$ 0,1 milhão e que funciona como fallback.

A API Comex estava em manutenção durante a coleta; o caminho de dados brutos oficiais foi usado com validação TLS normal. Classificações e valores podem sofrer revisões; registros aduaneiros não equivalem à movimentação física do aeroporto.

## Macroeconomia · BCB

[Dados abertos do Banco Central](https://dadosabertos.bcb.gov.br/), séries SGS 432 (meta Selic), 1 (dólar de venda) e 433 (IPCA). Recibos por indicador mantêm URL exata, quantidade de observações, SHA-256 e instante UTC. Histórico cobre jan/2022–set/2026; agregações detalhadas em `docs/indicadores.md`.

## ANAC

A integração de etapa combinada da ANAC continua sendo uma evolução futura, com validação de carga paga/grátis/correio e sentidos. Durante a pesquisa, o host apresentou falhas de certificado no cliente consultado. Nenhuma proteção TLS foi desativada; não foram fabricados dados ANAC nem rotulados os dados RMA como ANAC.
