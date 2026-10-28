# ANAC-04 — perfil de qualidade, grão e duplicidades

**Data:** 28/10/2026. **Estado:** diagnóstico offline aprovado; ANAC-04 permanece ABERTA. Sem autorização de nova coleta ou publicação.

**Código reprodutível:** scripts/perfilar_qualidade_anac04.py. **Testes:** tests/test_perfilar_qualidade_anac04.py. **Evidência:** [GitHub Actions #40721959900](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40721959900), 174 testes aprovados, linha ANAC04_RESUMO_REAL no log. Foram utilizados exclusivamente recortes ANAC SBKP previamente arquivados, com SHA-256 e somas verificadas por dois auditores.

## Escopo e resultados

**Unidade de observação:** um registro de movimentação reportado ao RIMA/ANAC, não um voo exclusivamente cargueiro, uma carga aduaneira MDIC ou movimentação do terminal no RMA.

| Competência | Movimentos | QT_CARGA positiva | QT_CARGA zero | QT_CARGA ausente | Colisões chave de toque |
|---|---:|---:|---:|---:|---:|
| 2020-01 | 9.739 | 5.006 | 4.733 | 0 | 6 |
| 2020-02 | 9.000 | 4.455 | 4.545 | 0 | 11 |
| 2020-03 | 6.881 | 3.605 | 3.276 | 0 | 12 |
| 2024-01 | 9.348 | 7.408 | 1.940 | 0 | 14 |
| **Total** | **34.968** | **20.474 (58,55%)** | **14.494 (41,45%)** | **0** | **43** |

**Chaves candidatas (não homologadas):** calço = natureza + matrícula aeronave + tipo de movimento + DT_CALCO + HH_CALCO; toque = natureza + matrícula + tipo de movimento + DT_TOQUE + HH_TOQUE. Não foram detectadas colisões adicionais na chave de calço nem DT_CALCO fora da competência nos quatro meses verificados; a chave de toque teve 43 colisões adicionais. **Colisão de chave candidata não comprova duplicidade física. Não excluir registros.**

A proporção de movimentos com QT_CARGA positiva é 58,55% do subconjunto verificado, **não** a proporção de voos exclusivamente cargueiros. Jan/2020 apresentou 51,40%, e jan/2024 79,25%: diferença meramente descritiva; não sustenta inferência de tendência, sazonalidade ou causa.

Os quatro meses não representam série completa. Permanecem 68 competências CSV 2020–2025 listadas e não arquivadas, e a disponibilidade 2026 segue pendente de evidência. Correio ANAC é distinto de courier RMA. Ausente, zero, movimentação sem carga e falta de publicação não são equivalentes.

## Incidente detectado e resolvido

A execução [#40721770749](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40721770749) falhou porque o novo código rotulava o grupo como natureza/movimento, enquanto o auditor prévio usa movimento/natureza. Corrigido o contrato sem modificar dados; a execução seguinte [#40721959900](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40721959900) passou com 174 testes. Não era erro do arquivo oficial.

## Portões necessários antes de encerrar ANAC-04

1. Confirmar dicionário oficial da ANAC: unidade de carga, granularidade da linha, papel de NR_SERVICE_TYPE e o significado de datas/horas de toque e calço.
2. Investigar a cobertura das chaves e as 43 colisões da chave de toque, sem expor matrículas em relatórios públicos e sem deduplicação automática.
3. Estender o perfil a novos meses somente após homologar armazenamento persistente independente, backup restaurado e piloto autorizado.
4. Confrontar RIMA e RMA por mesma competência e conceito, com PDFs RMA inteiramente verificados. Divergências metodológicas podem ser apresentadas lado a lado; não igualar séries artificialmente. ANAC-10 (TLS do site da concessionária) continua pendente.
5. Controlar revisões, disponibilidade 2026 e drift de esquema antes de liberar dashboard ou modelagem.

## Reproduzir offline

    python scripts/perfilar_qualidade_anac04.py --output reports/anac/anac04_perfil.json
    python -m unittest discover -s tests -p test_perfilar_qualidade_anac04.py -v

O comando não faz download e não altera manifesto ou site. O JSON produzido é diagnóstico local. O script mantém as flags liberado_dashboard=false e liberado_nova_coleta=false.

**Referências:** [Issue #8](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/issues/8) e [Plano de Ingestão](PLANO_INGESTAO_CONTROLADA_2026-10-28.md).


## Segunda passagem — anomalias de DT_TOQUE (investigação sem descarte)

O relatório de QA passou a separar chave candidata com campos preenchidos de chave com **data efetivamente reconhecida**. Comprovamos que o CSV oficial contém o marcador textual literal **null** para algumas datas DT_TOQUE. Não é um horário/código de voo nem uma data válida; tampouco devemos confundi-lo com carga zero.

| Competência | DT_TOQUE = texto null | DT_TOQUE fora do mês | Colisões chave toque (todas) | Colisões com data reconhecida | Duplicatas exatas de linha |
|---|---:|---:|---:|---:|---:|
| 2020-01 | 57 | 11 | 6 | 0 | 0 |
| 2020-02 | 70 | 0 | 11 | 0 | 0 |
| 2020-03 | 63 | 1 | 12 | 1 | 0 |
| 2024-01 | 74 | 3 | 14 | 0 | 0 |
| **Total** | **264** | **15** | **43** | **1** | **0** |

**Diagnóstico:** das 43 colisões preliminares de chave de toque, 42 deixam de ser candidatas a repetição física quando se exige a presença de data reconhecida. Resta **uma colisão de chave com DT_TOQUE reconhecido**, ainda sem interpretação documental. Repetições de uma chave incompleta não autorizam exclusão; preservam-se as 34.968 linhas. Os 15 eventos com data de toque fora do mês também não são excluídos: operações próximas à virada de mês ou erro de registro são hipóteses, não conclusões.

**Correção de contrato implementada:** o parser exploratório agora classifica string null (case-insensitive) como nao_informada, distinta de formato_nao_reconhecido, sem alterar um único byte da fonte nem substituir o valor por zero. Registra separadamente cobertura da chave com data reconhecida, colisões nesta condição e os marcadores de ausência encontrados. Testes de regressão verificam que null nunca certifica chave operacional.

**Pendências reais:** investigar a única colisão com data reconhecida, estabelecer regra de interpretação dos 15 toques em competências diferentes, validar o dicionário ANAC e confirmar critério de registros múltiplos. O status ANAC-04 continua aberto e os portões de coleta/publicação permanecem fechados.


**Validação final do ajuste:** [GitHub Actions #40722757215](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40722757215) — **176 testes Python aprovados**, validação do site aprovada e deploy ignorado no evento PR. Os 264 marcadores foram confirmados como texto literal null e aparecem agora como datas nao_informadas, não como formato_nao_reconhecido. Nenhum recorte, manifesto ou dado publicado foi modificado. ANAC-04 permanece aberta até a triagem da colisão remanescente e validação documental da semântica.


## Terceira passagem — conclusões normativas e revisão da prioridade

**Base documental oficial:**
- [Metadados ANAC de Movimentação Aeroportuária](https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/operador-aeroportuario/dados-de-movimentacao-aeroportuaria/60-dados-de-movimentacao-aeroportuaria): definições de DT_CALCO, DT_TOQUE, NR_SERVICE_TYPE, QT_CARGA, QT_CORREIO, unidade kg, origem declarada pelo administrador aeroportuário e possibilidade de atualização posterior.
- [Portaria ANAC nº 1.017/SRA/SIA/2018, texto compilado com alteração de 2019](https://pergamum.anac.gov.br/pergamum/vinculos/PA2018-1017.pdf): art. 7º (uma linha por movimento), art. 8º §1º (mês de referência determinado por **calço no pouso/descalço na decolagem**, não toque de pista); inciso VIII (SERVICE_TYPE Y = alternado, Z = retorno). DT_CALCO/HH_CALCO e DT_TOQUE/HH_TOQUE são horários **locais** do aeroporto.

**Verificação nas 34.968 linhas:**
- **15 DT_TOQUE fora do mês**: **todos são decolagens**, todos apresentam o toque **um dia após** a data do descalço, com intervalo descalço→toque **não negativo e de até 120 minutos**; DT_CALCO da totalidade dos 34.968 registros pertence à competência indicada. Isso é **compatível com a regra de reporte da ANAC**; não caracterizar como erro de competência nem mover para outro mês. Não foi realizada correção de dados.
- **264 valores textuais null** em DT_TOQUE: ausências documentadas, que não validam chave por toque. Permanecem nulos sem imputação.
- **43 colisões da chave candidata de toque**: somente **uma** persiste ao requerer data de toque reconhecida e não ausente.
- **Colisão residual (2020-03, decolagem doméstica)**: mesma chave candidata de toque, mesmo número de voo, mesmo aeroporto relacionado e mesma quantidade de carga, mas **NR_SERVICE_TYPE distinto (T versus Z)** e **HH_CALCO distinto**. O código T é teste técnico na tabela ANAC/IATA; Z é voo de retorno na Portaria. Os demais campos comparados não divergiram. Isso NÃO prova duplicidade física nem justifica excluir uma linha; é necessário obter identificador operacional confiável ou confirmação da ANAC/aeroporto.
- **Códigos de serviço examinados**: todos tiveram correspondência na tabela publicada pela ANAC ou na Portaria para Y/Z; a correspondência de domínio não certifica que cada linha foi classificada corretamente pelo operador.

**Limitação de rastreabilidade importante:** a Portaria menciona COD_RIMA, código de operação que poderia auxiliar o vínculo de movimentos, porém **o export público de dados arquivados contém NR_AEROPORTO_REFERENCIA e outros campos, mas não COD_RIMA**. Não inventar ID de voo ou somar linhas como um único movimento físico. A chave de calço pode ter zero colisões neste subconjunto, mas não está homologada como chave primária pela ANAC.

**Reprodução/anônimização:** scripts/auditar_eventos_excecionais_anac04.py e testes/test_auditar_eventos_excecionais_anac04.py executam leitura offline de dados arquivados já auditados. Os resultados e logs apresentam apenas contagens, tipos de movimento, categorias de serviço, diferenças de campos e intervalos agregados — **sem matrícula, número de voo, hora exata ou dado de movimentação individual**.

**Tratamento e status de governança:** podemos considerar **esclarecida a questão da competência** dos 15 registros sob o critério oficial, mas ANAC-04 permanece **ABERTA** pela colisão T/Z, pelos limites do identificador, pela série incompleta e pela reconciliação ANAC/RMA. O cofre persistente com backup real continua aguardando provisionamento; coletas novas, cron e dashboard permanecem bloqueados.
