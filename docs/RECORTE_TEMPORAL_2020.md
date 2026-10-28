# Política do recorte temporal — Viracopos Cargo Intelligence

**Decisão de escopo:** 28/10/2026  
**Marco inicial:** **1º de janeiro de 2020** (`2020-01`, competência mensal).  
**Estado:** recorte de pesquisa aprovado; cobertura efetiva continua a ser verificada por fonte.

## O que significa o marco inicial

- O horizonte histórico **alvo** para o projeto é **2020-01 até a última competência oficial validada de cada fonte**, nunca mais recente que sua data real de disponibilização.
- Este marco é comum ao programa analítico, mas **não altera retroativamente** a competência inicial das séries já publicadas. Cada base exibirá cobertura real, com lacunas explícitas.
- Para **ANAC/RIMA de Viracopos (SBKP)**, os novos lotes/arquivamento e os extratos processados deverão ser exclusivamente de `2020-01` em diante; o código rejeita pedidos com início anterior. Gatilhos automáticos e merge permanecem suspensos até a Issue #8 atender aos portões de segurança.
- O RMA da concessionária continua em sua série própria; o Comex/MDIC mantém kg líquido/FOB por fluxo, e as estatísticas ANAC seguem universos independentes.
- O período **anterior a 2020** fica fora do escopo operacional, porém investigações/artefatos históricos e seus problemas ficam preservados, sem apagar arquivos ou reescrever evidências.
- Informações públicas a respeito de 2019 poderão ser citadas como **contexto histórico**, mas não entrarão nos modelos/indicadores do recorte oficial. A indisponibilidade de janeiro/2019 **não é classificada como erro resolvido na fonte ANAC**; foi encerrada como impeditivo do projeto por decisão metodológica, não por reparo do servidor.
- A existência de 2020-01/2020-02 e 2024-01 no acervo não garante os outros meses, nem qualidade de previsão. Qualquer competência a partir de 2020 faltante ou inválida permanece **pendência obrigatória**.

## Cobertura efetiva no momento da decisão

| Fonte | Estado no projeto | Cobertura efetivamente confirmada |
|---|---|---|
| ANAC/RIMA SBKP | Três meses isolados, ambiente de desenvolvimento | `2020-01`, `2020-02`, `2024-01` (28.087 registros brutos SBKP no total) |
| Concessionária RMA | Painel principal | `2025-01` a `2026-08` (20 competências) |
| MDIC/Comex em Viracopos | Painel principal | `2025-01` a `2026-09` (21 competências) |
| MDIC Brasil | Painel principal | `2025-01` a `2026-09` (21 competências) |
| BCB/SGS macro | Painel principal | `2022-01` a `2026-09` (57 competências) |

**Cuidado:** esses intervalos são os do snapshot examinado em 28/10/2026, e não garantias de atualização futura. Não somar métricas de universos diferentes como se fossem iguais. A cobertura integral 2020–presente ainda **não** existe.

## Tratamento do incidente histórico de 2019

A [Issue #8](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/issues/8) registra as evidências: ausência de janeiro/2019 no diretório oficial (CSV/JSON HTTP 404), fevereiro/2019 somente JSON e março–dezembro/2019 em CSV, com versão alternativa em dezembro. A decisão **retira o ano 2019 do backfill obrigatório**, mas não apaga a investigação nem implica que a ANAC forneça o período inteiro. Não haverá desenvolvimento de leitor JSON para fevereiro/2019 dentro da trilha operacional 2020+.

## Portões que permanecem bloqueantes

1. **P0 — Segurança:** manter o PR #7 como rascunho, sem cron e sem alterar a visualização principal.
2. **P1 — Incidentes:** 2019 passa a ter desfecho **fora do escopo**; todos os demais itens da Issue #8 precisam de solução comprovada ou exceção documentada que não comprometa o uso do dado.
3. **P2 — Contrato:** confirmar tipos, unidades, códigos e testes com extratos reais do arquivador e processador.
4. **P3 — Qualidade:** validar todos os meses coletados e reconciliar conceitualmente o RIMA contra RMA sem igualar populações.
5. **P4 — Resiliência:** confirmar integridade, histórico de revisões, recuperação de falhas e atomicidade de commits em testes.
6. **P5 — Governança:** aprovar PR e regras de execução/alertas antes de produzir qualquer nova série pública.

**Regra de aceite:** nenhum mês depois de 2020 pode ser considerado coberto apenas por existir um URL; exigir original íntegro, recorte SBKP validado, arquivo com hash e testes. Não imputar ausências como zero.

[Registro detalhado de pendências](referencias/anac/REGISTRO_PENDENCIAS_E_PORTOES_2026-10-28.md) · [Plano RIMA](referencias/anac/PLANO_INTEGRACAO_RIMA_2026-10-28.md) · [Backlog](backlog.md).
