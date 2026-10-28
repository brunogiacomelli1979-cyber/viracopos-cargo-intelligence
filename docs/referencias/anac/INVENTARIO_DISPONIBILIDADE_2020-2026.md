# Inventário de disponibilidade de arquivos ANAC/RIMA — 28/10/2026

**Programa:** Viracopos Cargo Intelligence · **Escopo:** listagens oficiais anuais ANAC, a partir de 2020-01.  
**Método:** consultas HTTPS aos índices de diretório do servidor `sistemas.anac.gov.br`, extração de nomes de arquivos, **sem baixar CSV/JSON nacionais e sem gravar novos meses no acervo**.  
**Evidência:** [GitHub Actions #40687137171 — sucesso](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40687137171), artefato `inventario-anac-rima-2020-mais` (ID 12815900964, retenção 30 dias). O JSON extraído desse artefato foi conferido localmente (SHA-256 `4be0a963f553e3596bf2d91972c4c07eecce2462ab3e56e9c9940cf659b63f0b`).

## Cobertura publicada nas listagens

| Ano | Competências listadas | Índice anual | Observação |
|---|---:|---|---|
| 2020 | 12/12 | HTTP 200 | Janeiro a dezembro |
| 2021 | 12/12 | HTTP 200 | Janeiro a dezembro |
| 2022 | 12/12 | HTTP 200 | Julho somente CSV; demais CSV e JSON |
| 2023 | 12/12 | HTTP 200 | Janeiro a dezembro |
| 2024 | 12/12 | HTTP 200 | Janeiro a dezembro |
| 2025 | 12/12 | HTTP 200 | Janeiro a dezembro |
| 2026 | **não confirmadas** | **HTTP 404** | O diretório anual não respondeu; não concluir que 2026 inexiste em todas as origens oficiais |

**Consolidado, janela indicativa 2020-01 a 2026-04:** 72 meses **listados**; 0 meses não listados em anos com diretório acessível; 4 meses com **índice de 2026 inacessível**. A janela encerra 6 meses antes da consulta como margem conservadora, **não** como garantia de que um mês já deveria ter sido publicado.

O arquivo do relatório apresenta 71 meses com as extensões CSV e JSON e **2022-07 somente CSV**; não há inconsistência demonstrada, pois CSV é suficiente para nosso leitor.

## O que esta auditoria NÃO comprova

1. Existência e integridade do conteúdo completo de cada CSV/JSON; links listados podem retornar erro no download.
2. Presença de SBKP em todas as 72 competências, contagem de registros, grão ou unidades corretos.
3. Revisões históricas e datas reais de publicação (o índice não oferece automaticamente calendário da primeira divulgação).
4. Homogeneidade ANAC/RIMA x RMA da concessionária ou dados aduaneiros MDIC.
5. Disponibilidade de 2026 em outros endpoints; o HTTP 404 é restrito à listagem anual consultada.

## Pendências e decisões de qualidade (ANAC-11)

- **2020–2025:** a etapa de **descoberta de arquivos** está concluída, mas os 69 meses ainda não arquivados **não podem ser considerados cobertos** até download, validação e versionamento.
- **2026:** investigar se existe endpoint alternativo oficial, como ocorre a atualização anual das pastas, quais meses já foram efetivamente liberados e se houve mudança de publicação. **Nunca preencher 2026 com zero.**
- **Atualização mensal:** distinguir "ainda não publicado", "ausência no índice", "falha de rede" e "arquivo inválido"; somente após definir latência observada e tratamento operacional poderá ser ativado cron.
- **Automação:** não executar novos lotes históricos nem liberar `ANAC_RIMA_COLETA_AUTORIZADA` enquanto os portões da [Issue #8](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/issues/8) estiverem abertos.
- **Fontes recentes:** a série do RMA da concessionária continua independente da RIMA e pode cobrir meses mais recentes, mas sem substituição conceitual automática.

**Status ANAC-11:** **parcialmente comprovada, aberta para 2026 e data de publicação**. A auditoria registrou positivamente os meses de 2020–2025 sem acelerar a coleta indevidamente.

[Política de recorte](../../RECORTE_TEMPORAL_2020.md) · [Tratativas dos workflows](TRATATIVAS_WORKFLOWS_2026-10-28.md)
