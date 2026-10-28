# Etapa 4 — Integração ANAC/RIMA em ambiente isolado

**Data:** 28/10/2026  
**Estado:** processador offline e testes com **dados artificiais**. Ainda sem coleta ou dados reais ANAC, sem integração ao dashboard.

## Escolha da fonte

Iniciar pela família **Dados de Movimentação Aeroportuária / Operador Aeroportuário (RIMA)**, distinta de:
- ANAC Estatísticas do Transporte Aéreo: movimentos reportados por companhias aéreas;
- RMA da concessionária de Viracopos: tonelagem operacional internacional, doméstica e courier, atualmente sem separação de sentidos;
- MDIC/Comex Stat: fluxo aduaneiro em US$ FOB e kg líquidos, URF 0817700/via 04.

A família RIMA permite investigar `NR_AEROPORTO`, `NR_MOVIMENTO_TIPO`, `NR_NATUREZA`, `QT_CARGA` e `QT_CORREIO`. Não assumir que pouso/decolagem é igual a importação/exportação. A metainformação oficial indica publicação mensal com **defasagem de seis meses**, que deverá ser confirmada na prática para cada competência.

Fontes oficiais:
- [Metadados RIMA](https://www.gov.br/anac/pt-br/acesso-a-informacao/dados-abertos/areas-de-atuacao/operador-aeroportuario/dados-de-movimentacao-aeroportuaria/metadados-operador-aeroportuario-dados-de-movimentacao-aeroportuaria).
- [Catálogo CSV/JSON](https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/operador-aeroportuario/dados-de-movimentacao-aeroportuaria/operador-aeroportuario-dados-de-movimentacao-aeroportuaria-formato-csv-json).
- [Acervo documental e nota de curadoria](README.md).

## Implementação entregue

O módulo [`scripts/processar_anac_rima.py`](../../../scripts/processar_anac_rima.py) processa **um CSV mensal já obtido**, filtrando SBKP e preservando grupos por natureza (internacional/doméstica) e movimento (pouso/decolagem). Confere competência, cabeçalho, tipos de quantidade, possíveis ausências, limites de arquivo e registra SHA-256 e recibo de proveniência. Não faz download, não abre links externos, não altera `data/viracopos.csv`, `data/dashboard.json`, `data/fontes.json` ou `index.html`.

Uso após aquisição oficial verificável:

```bash
python scripts/processar_anac_rima.py --input CAMINHO/arquivo.csv --month 2025-01 --out-dir data/staging/anac_rima
python -m unittest discover -s tests -p 'test_processar_anac_rima.py' -v
```

Saída no diretório de staging ignorado pelo Git: CSV e recibo JSON. As quatro combinações de natureza/movimento são mantidas separadas. Quantidade ausente não vira zero, e subtotal com qualquer observação ausente é marcado como incompleto. Ausência de movimentos no arquivo não prova zero real. `QT_CORREIO` não é somado a `QT_CARGA` automaticamente.

Os [testes](../../../tests/test_processar_anac_rima.py) usam **somente amostras sintéticas**: agrupamento, zero observado, quantidade ausente, códigos incorretos, competência divergente, filtro SBKP, codificação CP1252 e proteção contra sobreposição. Sete testes passaram em execução local em 28/10/2026; os testes na branch ainda precisam ser conferidos pelo CI.

## Pendências obrigatórias antes de integrar a série real

1. Obter ao menos dois arquivos mensais oficiais efetivamente acessíveis, confirmando HTTPS, URL final, SHA-256, data de coleta e condições de reutilização.
2. Conferir o esquema **real**: cabeçalho, separador, codificação, categorias e sentinelas de dados ausentes. O parser atual é uma hipótese de contrato e deve ser ajustado se os originais diferirem.
3. Confirmar cobertura mensal de SBKP, duplicações, revisões e lacunas sem imputações.
4. Reconciliar período coincidente com RMA da concessionária, explicitando diferença de população, unidade, pouso/decolagem versus importações/exportações, carga versus correio e courier.
5. Executar testes no GitHub CI e validações com fonte verdadeira antes de merge, automação e exposição de quaisquer números ANAC.
6. Registrar legislação aplicável à competência e mudanças de metadados.

**Decisão:** Etapa 4 **em andamento**. O PR permanece para revisão e não será incorporado ao painel antes desses portões.
