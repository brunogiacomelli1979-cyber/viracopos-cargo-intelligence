# ANAC-04 — Conciliação exploratória RIMA × RMA, janeiro de 2024

**Data da análise:** 28/10/2026  
**Status:** `PRELIMINAR — NÃO PUBLICAR`. Não encerra ANAC-04. Sem alterações de dados, dashboards, arquivos históricos ou automação mensal.

## 1. Problema diagnosticado

O projeto publicado reúne RMA da concessionária **2025-01 a 2026-08**; o acervo ANAC/RIMA de desenvolvimento, já conferido por SHA-256, contém somente **2020-01, 2020-02 e 2024-01**. Portanto, as duas séries já armazenadas têm **zero competências coincidentes**. É incorreto confrontar meses diferentes para declarar equivalência ou estimar divergências.

Para analisar somente a **comparabilidade** sem liberar nenhum dado no painel, foi identificada uma publicação **oficial da concessionária** com janeiro/2024:
- [RMA 2024 JUL, elaborado em agosto de 2024, página 1](https://www.viracopos.com/data/files/61/C0/D2/0B/6E741910317C2C094918E9C2/RMA%202024%20JUL%20-%20elaborado%20em%20AGO2024.pdf), com janeiro: doméstica **5.908 t**, internacional **13.962 t**, courier internacional **604 t**.
- Os números acima foram **transcritos do texto público indexado do PDF**, mas não foi possível baixar, renderizar/verificar visualmente nem produzir SHA-256 do arquivo integral devido a falha de acesso HTTPS/TLS da concessionária. Por isso, a referência está em [`rma_2024_01_preliminar.json`](../rma/rma_2024_01_preliminar.json), **não certificada**. Existem diferentes edições do RMA 2024; sua comparabilidade temporal e eventuais revisões devem ser conferidas antes de atribuir confiabilidade final.

## 2. Definições e diferenças de população

| Campo | ANAC/RIMA | Concessionária/RMA |
|---|---|---|
| Grão original | Movimento de aeronave declarado pelo operador | Boletim consolidado mensal de movimentação operacional |
| Natureza | Doméstica / internacional por movimento de pouso/decolagem | Doméstica / internacional; coluna `INT*` é importações + exportações |
| Massa | `QT_CARGA` em **kg** de bens na aeronave, excluindo correio, bagagem e provisões | Carga em **toneladas** |
| Correio/courier | `QT_CORREIO` da ANAC em kg, separado de `QT_CARGA` | Courier em quadro à parte; **não** assumir equivalência a correio |
| Fluxo | Pouso e decolagem; **não** renomear como importação/exportação | Sem direção separada no boletim utilizado |
| Revisões | Arquivo por competência com hash, revisão possível | Relatórios sujeitos a atualização sem aviso prévio |

A unidade é normalizada apenas para **comparação exploratória**, dividindo os kg ANAC por 1.000. Isso **não** torna os universos equivalentes. Fonte de definição: [Metadados ANAC/RIMA](https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/operador-aeroportuario/dados-de-movimentacao-aeroportuaria/60-dados-de-movimentacao-aeroportuaria), campos `QT_CARGA` e `QT_CORREIO`.

## 3. Resultados de janeiro de 2024 (provisórios)

Os grupos ANAC/RIMA foram calculados a partir do CSV SBKP **2024-01** arquivado, validado previamente por dois cálculos independentes [GitHub Actions #40683558361](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40683558361).

| Natureza | ANAC: pouso (kg) | ANAC: decolagem (kg) | ANAC: total (t) | RMA: jan/2024 (t) | Diferença (t) |
|---|---:|---:|---:|---:|---:|
| Doméstica | 2.518.901 | 3.389.598 | **5.908,499** | **5.908** | **+0,499** |
| Internacional | 9.460.925 | 6.554.994 | **16.015,919** | **13.962** | **+2.053,919** |

A diferença internacional é **+14,7107%** do RMA; a doméstica é **+0,0084%**. O valor doméstico está dentro de meia tonelada, mas isso não demonstra igualdade de metodologia, apenas aproximação dos valores. O desvio internacional é expressivo e **não deve ser corrigido por ajuste, filtragem oportunista ou inclusão de courier sem justificativa documental**. A ANAC tem **21 kg** de `QT_CORREIO` internacional nesse mês segundo a agregação; isso não pode ser somado automaticamente aos **604 t de courier** do boletim RMA.

## 4. Possíveis causas a investigar (hipóteses, não conclusões)

- Diferentes populações: carga embarcada/desembarcada em aeronaves versus movimentação operacional da concessionária/terminal; eventuais exclusões, trânsito, transbordo ou consolidação distintas.
- Revisão de números publicada em boletins RMA posteriores.
- Códigos de serviço (`NR_SERVICE_TYPE`), tipo de operação, duplicidade lógica por voo versus movimentos de pouso/decolagem.
- Datas e eventos de contabilização distintos, incluindo carga movimentada no terminal versus aeronaves.

Não escolher uma hipótese sem teste e evidência.

## 5. Implementação e testes

- [`scripts/conciliar_rima_rma.py`](../../../scripts/conciliar_rima_rma.py) lê as três competências RIMA existentes (somente leitura), valida os arquivos, compara com `data/viracopos.csv` e recusa confrontar meses não coincidentes.
- A referência de janeiro/2024 só entra por `--referencia-preliminar` e força `liberado_dashboard: false`; não se transforma em linha oficial do `data/viracopos.csv`.
- [`tests/test_conciliar_rima_rma.py`](../../../tests/test_conciliar_rima_rma.py) testa ausência de sobreposição, conversão kg→t, discrepância, ausência de observação, prevenção de duplicações, validação da URL oficial e grupos ANAC incompletos.
- [Workflow de CI](../../../.github/workflows/conciliar-rima-rma.yml) somente lê os dados e grava resultados como artefatos temporários; **não faz download de microdados nem commit de séries**.
- Evidências: [#40689283275](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40689283275) e [#40689409036](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40689409036), ambas aprovadas.

## 6. Portões restantes — ANAC-04 aberta

1. Recuperar PDF original oficial da concessionária com TLS validado; registrar SHA-256, data e conferência visual da página do boletim. Reconciliar edições de 2024 antes de promover qualquer referência a fonte certificada.
2. Obter explicação formal do escopo de carga no RMA e comparar com a definição `QT_CARGA` da ANAC; registrar política de courier, trânsito, correio, modos e cortes de competência.
3. Investigar a distribuição por `NR_SERVICE_TYPE` e movimentos na ANAC de 2024-01 sem ajustar números para fazê-los coincidir.
4. Só então liberar outro mês coincidente mediante política de coleta autorizada ANAC-06 e QA; nunca ocultar divergências por preencher lacunas ou escolher períodos diferentes.
5. Documentar se as séries são apenas **complementares** ou se há reconciliação metodológica legítima. Qualquer divergência não explicada impede promover como indicador intercambiável.

**Conclusão:** foi resolvido o problema de **ausência de comparação válida no código**, e foi identificada uma discrepância exploratória relevante. **A causa da divergência e a certificação documental permanecem abertas**. A ANAC-04 não está encerrada, e os portões da [Issue #8](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/issues/8) continuam bloqueando publicação/automação.
