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

## 7. Perfil de serviço ANAC 2024-01 — hipótese investigada, não explicação

[GitHub Actions #40689762587](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40689762587) examinou **somente o recorte SBKP janeiro/2024 já arquivado**, agrupando `QT_CARGA` por `NR_SERVICE_TYPE` e movimento. Os totais foram **conferidos novamente** contra os 16.015.919 kg internacionais e 5.908.499 kg domésticos validados. O relatório é provisório e não publica dados.

| Service Type ANAC (código, sem interpretação de categoria ainda) | Carga internacional (kg) | Participação do total internacional ANAC |
|---|---:|---:|
| F | 12.460.311 | 77,7995% |
| J | 1.932.728 | 12,0675% |
| H | 1.539.675 | 9,6134% |
| G | 42.087 | 0,2628% |
| Y | 41.118 | 0,2567% |

Os cinco grupos perfazem os **16.015.919 kg**. A carga internacional não aparece em apenas um tipo de serviço, mas **não há evidência para excluir nenhum deles** ou afirmar que o RMA considera os mesmos códigos. Interpretar os códigos apenas mediante o dicionário IATA/ANAC e escopo específico do RMA.

**Consequência:** a divergência de **2.053,919 t** entre as duas fontes permanece sem causa demonstrada. Esta investigação não autoriza adaptar os dados para fazê-los coincidir. Código auditável: [`scripts/investigar_escopo_rima.py`](../../../scripts/investigar_escopo_rima.py) e [testes](../../../tests/test_investigar_escopo_rima.py).

## 8. Revisão regulatória e conferência de contagem de movimentos — 28/10/2026

### A relação entre os relatórios é mais direta do que a hipótese inicial

A [Resolução ANAC nº 464/2018](https://www.anac.gov.br/assuntos/legislacao/legislacao-1/resolucoes/2018/resolucao-no-464-22-02-2018), artigos **6º a 13**, regulamenta **RMA** e **RIMA** como relatórios apresentados pelos **administradores aeroportuários**, referentes aos movimentos do mês. O art. 7º exige movimento de aeronaves e cargas no RMA; o art. 10 exige os movimentos individualizados e suas cargas no RIMA; o art. 13 exige remessa mesmo havendo divergências ainda em contestação. **Não é adequado tratar essas séries como fontes institucionais independentes e dispensar sua reconciliação.**

Os [metadados oficiais RIMA](https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/operador-aeroportuario/dados-de-movimentacao-aeroportuaria/60-dados-de-movimentacao-aeroportuaria) informam que o dataset publicado reproduz as remessas do administrador aeroportuário **sem correções/interpolações empregadas nos indicadores contratuais** e que seus responsáveis podem atualizar dados. Isso oferece um **mecanismo plausível para diferenças**, mas NÃO comprova quais correções ocorreram nem por que há 2.053,919 t e 81 movimentos a mais na consulta de RIMA.

### Confronto adicional de movimentos, mesma competência

Valores ANAC do CSV SBKP 2024-01 já arquivado e validado; RMA transcrito dos PDFs publicados:

| Janeiro de 2024 | ANAC/RIMA | RMA concessionária | Desvio ANAC − RMA |
|---|---:|---:|---:|
| Movimentos domésticos | 8.407 | 8.338 | **+69** |
| Movimentos internacionais | 941 | 929 | **+12** |
| Movimentos totais | **9.348** | **9.267** | **+81** |
| Carga doméstica | 5.908,499 t | 5.908 t | +0,499 t |
| Carga internacional | 16.015,919 t | 13.962 t | **+2.053,919 t** |

**Verificação de edições:** os PDFs oficiais [RMA janeiro/2024 (elaborado fevereiro)](https://www.viracopos.com/data/files/CD/74/48/52/BD1DD810710CF7C84918E9C2/RMA%202024%20JAN%20-%20elaborado%20em%20FEV2024.pdf), [RMA julho/2024 (elaborado agosto)](https://www.viracopos.com/data/files/61/C0/D2/0B/6E741910317C2C094918E9C2/RMA%202024%20JUL%20-%20elaborado%20em%20AGO2024.pdf) e [RMA setembro/2024 (elaborado outubro)](https://www.viracopos.com/data/files/D3/E5/65/52/379B29101B8547296C1849A8/RMA%202024%20SET%20-%20elaborado%20em%20OUT2024.pdf) apresentam, **nos textos indexados**, os mesmos dados de janeiro. **Não encontramos revisão de janeiro entre essas edições**, mas isso não exclui revisão posterior e não equivale à inspeção visual/hash dos originais.

### Auditoria de competência e chave de evento

A [execução #40690622665](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40690622665) comprovou que **100% dos 9.348 eventos têm `DT_CALCO` dentro de janeiro de 2024**. Pelos [metadados ANAC](https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/operador-aeroportuario/dados-de-movimentacao-aeroportuaria/60-dados-de-movimentacao-aeroportuaria), `DT_CALCO` é o calço no pouso ou o descalço na decolagem, exatamente o critério de competência da Resolução 464.

A [execução #40690787280](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40690787280) examinou os 9.348 registros com duas chaves compostas (matrícula, tipo de movimento, data e hora). Conclusão:

- **0 colisões** na chave com `DT_CALCO` e `HH_CALCO`.
- **14 colisões potenciais** na chave com `DT_TOQUE` e `HH_TOQUE` (12 domésticas, 2 internacionais), **não qualificadas como duplicações físicas**.
- Todos os registros tiveram chave completa nos dois conjuntos; nenhum foi deduplicado, reclassificado ou excluído.

Esses achados **não explicam** o desvio de +81 movimentos. Uma exclusão arbitrária de 14 linhas seria indevida.

### Próximo passo necessário

Solicitar/obter os originais RMA completos de 2024 com hash e inspeção visual e, idealmente, uma explicação técnica da concessionária e/ou GEIC/ANAC quanto à diferença entre **RMA publicado em 2024** e **RIMA disponibilizado no portal em 2026**, especialmente sobre revisões, movimentos incluídos/excluídos, natureza do voo e carga internacional. Não ativar modelos ou dashboard ANAC enquanto a divergência de escopo não for esclarecida.

## 9. Deliberação do projeto: comparação visual permitida, sem equiparação das fontes

**Decisão do proprietário em 28/10/2026:** a divergência entre números ANAC/RIMA e concessionária/RMA **não precisa ser eliminada para exibir as duas séries graficamente**. A diferença será calculada e descrita, preservando as duas observações originais, seus recortes e suas versões. Não aplicar normalizações ad hoc para criar coincidência.

**Condição de implementação:** na aba *Carga aérea* foi preparado **painel experimental** com filtros independentes de competência, natureza (doméstica/internacional), medida (toneladas de carga ou movimentos) e fonte (ambas, ANAC ou RMA). A prévia JAN/2024 está rotulada como *transcrição RMA de PDF ainda não certificada por SHA-256*; não entra nas séries RMA principais, nem nos KPIs, nem no Comex, nem nos modelos. Os controles são válidos mesmo com apenas uma competência comparável; a ampliação por mês depende de documentação e dados oficiais validados.

### Movimentos com ou sem carga: correção conceitual

A Resolução ANAC 464/2018 (art. 3º) esclarece que aeronave de passageiros também pode transportar carga e correio (operação mista). O [dicionário oficial do RIMA](https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/operador-aeroportuario/dados-de-movimentacao-aeroportuaria/60-dados-de-movimentacao-aeroportuaria) distingue `QT_CARGA` (bens em kg, excluindo bagagem e correio), `QT_CORREIO`, três campos `QT_PAX_*` e `NR_SERVICE_TYPE` (tipo do serviço). **Movimento internacional não é automaticamente importação ou exportação aduaneira; movimento com carga não é necessariamente cargueiro.**

A [execução de perfil com dados reais #40692011727](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40692011727) classificou **todos os 9.348 movimentos de janeiro/2024**, usando `QT_CARGA > 0` para carga positiva e passageiros efetivamente registrados nos campos `QT_PAX_*`. O resultado é:

| Categoria | Doméstico | Internacional | Total |
|---|---:|---:|---:|
| Movimentos com carga positiva | 6.667 | 741 | **7.408** |
| Movimentos com `QT_CARGA = 0` | 1.740 | 200 | **1.940** |
| Com passageiros registrados e carga positiva | 6.395 | 270 | **6.665** |
| Com passageiros registrados e `QT_CARGA = 0` | 1.346 | 37 | **1.383** |
| Movimentos totais | 8.407 | 941 | **9.348** |

**Importante:** `QT_CARGA = 0` significa que a fonte registrou **zero quilogramas de carga naquele movimento**, e não que um voo nunca transporta carga nem que não houve transação aduaneira. Passageiros não registrados e aeronave cargueira não são sinônimos. Ausências devem permanecer indeterminadas.

A implementação está em [`scripts/gerar_comparativo_rima_rma.py`](../../../scripts/gerar_comparativo_rima_rma.py) e [dados de perfil e comparação](../../../data/comparativo_rima_rma.json), gerados a partir dos recortes ANAC já arquivados (SHA-256 verificado) e do RMA preliminar. O dashboard azul preserva os gráficos e filtros anteriores e acrescenta apenas dois painéis exploratórios na seção Carga aérea.

**Verificação:** [CI #40692718303](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40692718303) aprovou validação de HTML/JSON, testes de perfil, JavaScript, reconstrução offline e preparo da página. [Prévia navegável (artefato GitHub Actions)](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40692718303/artifacts/12817837694). **Ainda não foi feita inspeção visual manual em navegador real** e **nenhuma alteração foi aplicada à branch `main` ou ao Pages publicado**.

**Status ANAC-04:** tratativa da **visualização e da segregação carga/passageiros concluída em homologação**. Permanecem em aberto a conferência integral/hash do RMA 2024, eventuais regras de correção RIMA vs RMA e séries temporais coincidentes adicionais. **A divergência numérica, por si só, não é um bloqueio de visualização com ressalva; é um fato a apresentar.**
