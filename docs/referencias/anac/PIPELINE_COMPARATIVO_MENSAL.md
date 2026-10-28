# Pipeline mensal do comparativo ANAC × RMA

**Escopo:** a partir de 2020-01, **sem download nesta fase**, somente leitura dos extratos aprovados na branch de homologação.

O gerador `scripts/gerar_comparativo_rima_rma.py` percorre todas as competências listadas no manifesto ANAC/RIMA, verifica tamanho/hash de cada arquivo gzip e do conteúdo, reconcilia contagens com `validar_agrupamento_rima.py` e classifica cada movimento por `QT_CARGA` e `QT_PAX_*`. Não fixa mais 2024-01, apenas utiliza a referência documental preliminar de 2024 quando existe.

O contrato de saída `data/comparativo_rima_rma.json` versão **2** contém:

- `perfil_voos`: todos os meses RIMA já arquivados e tecnicamente aprovados, mesmo sem RMA correspondente.
- `serie_mensal`: união esparsa dos meses RIMA e RMA, separada por natureza doméstica/internacional. Meses ausentes têm valor `null`, nunca 0.
- `recortes`: apenas os pares de mesma competência e natureza com **carga observada nas duas fontes**; toda diferença permanece visível.
- `meses_anac` e `meses_com_duas_fontes`: controles de cobertura.
- `qualidade_rima`, `qualidade_rma`, hashes e URL oficial quando conhecida: identificação da origem de cada número.
- `liberado_para_indicadores: false`: mantém os dados exploratórios separados dos KPIs e dos modelos enquanto restarem portões.

A série RMA já validada no dashboard não deve ser descrita como PDF individual verificado por hash quando a verificação documental específica não existe. Uma transcrição de 2024 ainda não certificada continua rotulada como tal.

**Política de apresentação:** mostrar RMA e RIMA como conjuntos distintos, sem deduplicar voos, somar `QT_CORREIO` ao courier ou classificar automaticamente carga internacional como aduaneira. Um movimento com `QT_CARGA > 0` pode ter passageiros.

**Dependências abertas:** ANAC-06 (segurança de publicação remota), ANAC-10 (TLS dos PDFs RMA), ANAC-11 (2026 e cadência oficial), ANAC-04 (documentação e versões). Não liberar cron, backfill, merge do PR #7 ou publicação do dashboard a partir do gerador.
