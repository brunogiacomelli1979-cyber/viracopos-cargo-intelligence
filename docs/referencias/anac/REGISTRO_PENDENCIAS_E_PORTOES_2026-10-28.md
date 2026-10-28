# Registro de pendências ANAC/RIMA — bloqueio da expansão histórica

**Data da auditoria:** 28/10/2026  
**Escopo:** GitHub Actions, aquisição histórica ANAC/RIMA, biblioteca documental, código de processamento e integridade inicial.  
**Decisão:** **NÃO REALIZAR novos lotes, liberar agendamento mensal, mesclar PR #7 ou publicar indicadores ANAC** até atender aos portões descritos abaixo. A existência de três competências isoladas não equivale a uma série histórica contínua.

## Evidências verificadas

- [Execução 40678591729](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40678591729): jan/2024 com 9.348 linhas SBKP arquivadas, SHA-256 validado.
- [Execução 40680165690](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40680165690): jan/2020 com 9.739 e fev/2020 com 9.000 linhas SBKP; os arquivos compactados e manifesto foram commitados na branch.
- [Execução 40679251194](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40679251194): jan/fev 2019 retornaram HTTP 404; sem alterações históricas.
- [Execução 40680102297](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40680102297): acesso parcial HTTP 206 em jan/2020–jan/2024; jan/2019 404. **HTTP 206 demonstra acessibilidade, não integridade do arquivo inteiro**.
- [Execução 40547838009](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40547838009): piloto antigo de **Etapa Básica ANAC (transportadoras)** falhou porque o ZIP consultado não apresentou CSV/TXT legível; não confundir com o pipeline RIMA que já baixou CSV real.
- [Execução 40680332556](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40680332556): Pages PR marcado `action_required`, ator `github-actions[bot]`, sem jobs executados. Requer apuração de política de execução/aprovação; não é teste de dados reprovado.

## Matriz de incidentes e ações

| ID | Gravidade | Evidência / causa | Tratativa | Situação / condição para encerrar |
|---|---|---|---|---|
| ANAC-01 | Alta | Arquivos RIMA jan/fev 2019 HTTP 404, apesar de o pacote Ipea `flightsbr` documentar disponibilidade desde jan/2019 | Listar diretório `2019/` e URLs realmente publicadas; consultar ANAC sobre remoção/renomeação, buscar cópia oficial verificável; comparar leitor `flightsbr`. Se inviável, registrar lacuna sem imputar zero, obter decisão formal para iniciar série em 2020 | **Aberta**; não considerar 2019 recuperado com base em documentação do Ipea |
| ANAC-02 | Alta | Antigo piloto `anac-sbkp-piloto.yml`, executando outra população (Etapa Básica), retornou ZIP sem CSV/TXT | Congelar seu uso para análise RIMA; só retomar em trilha distinta, corrigindo URL/contrato ZIP e amostra real | **Aberta / isolada**; não substituir RIMA pela Etapa Básica |
| ANAC-03 | Alta | Processador `processar_anac_rima.py` ainda utilizava `NR_AEROPORTO`, códigos por extenso, e não aceitava preâmbulo; o CSV real usa `NR_AEROPORTO_REFERENCIA`, P/D, D/I e `Atualizado em:` | Patch na branch e testes de contrato com cabeçalho/códigos identificados em arquivo oficial | **Correção no código preparada; aguardar CI e teste com dados reais antes de fechar** |
| ANAC-04 | Alta | Gzip/manifesto do arquivador são validados nos três meses, mas ainda sem perfil de nulos, valores inválidos, duplicidade, estabilidade dos códigos ou comparabilidade com RMA | Auditar quantitativamente cada competência, documentar denominadores/grão e reconciliar RIMA x RMA sem equiparar importação/exportação a pouso/decolagem | **Aberta**; nenhum resultado de tonelagem liberado |
| ANAC-05 | Média | `action_required` em PRs gerados por `github-actions[bot]` sem jobs e e-mails de falhas repetidas | Diagnosticar política de permissões/Actions e aprovação; reduzir disparos; monitorar separadamente `failure` e `action_required` | **Aberta**; evitar afirmar que se trata de falha de testes |
| ANAC-06 | Alta | Workflow de arquivamento tinha agendamento previsto, referência fixa à branch de desenvolvimento e default 2019 que gera 404 | Retirar agendamento até QA; usar branch atual no checkout/push e default provisório 2020-01 **sem declarar 2019 resolvido**; somente manual mediante plano aprovado | **Mitigada no código, bloqueada operacionalmente**; não ativar antes dos portões |
| ANAC-07 | Média | Pilotos de rede e histórico acionados por alterações de arquivos, gerando várias execuções/e-mails e tentativas repetidas | Alterar os três workflows de diagnóstico/piloto para `workflow_dispatch` somente, mantendo `pages.yml` como guarda de PR | **Mitigada na branch**; conferir após commit |
| ANAC-08 | Alta | Arquivos mensais nacionais não são preservados; guardamos extração SBKP mais SHA-256 de origem; revisões sobrescrevem o extrato atual | Preservar histórico Git, recibos por competência e comparação de revisões; validar imutabilidade de versões, integridade pós-clone, ausência de perda de meses e política de rollback | **Aberta** |
| ANAC-09 | Média | Coleta em lote retorna falha geral se uma URL for 404; sucessos prévios da execução ficam no runner quando o commit é condicionado ao sucesso | Descobrir competências existentes antes de baixar; fazer lotes pequenos, gerar relatório de falhas e não publicar parcialmente sem recibo/QA | **Aberta** |
| ANAC-10 | Média | Acervo documental contém pendência opcional de página da concessionária por `CERTIFICATE_VERIFY_FAILED` | Separar issue de coleta da concessionária, verificar cadeia TLS/URL alternativa oficial, sem desabilitar certificados | **Aberta não bloqueante para acervo ANAC**, mas bloqueia declaração de documentação externa 100% completa |
| ANAC-11 | Média | Base ANAC/RIMA pode ter defasagem institucional de cerca de seis meses e meses ainda não divulgados; falta inventário real | Construir inventário de competências e datas de atualização reais antes do cron e da previsão; não marcar ausência recente como erro nem zero | **Aberta** |

**Nota operacional:** a aprovação de 2020/2024 demonstra integridade de **recorte, competência, presença e hash**; ainda não houve avaliação de completude estatística ou equivalência com tonelagem do terminal.

## Alternativas de acesso à série 2019

1. **Preferida:** recuperar URL específica por enumeração de arquivos no servidor oficial (não construir nomes por suposição). Testar tamanho, cabeçalho, HTTPS e SHA-256.
2. **Segunda:** inspecionar `flightsbr::get_airport_movement_dates_available()` / `read_airport_movements(date=201901)` em ambiente R com acesso a rede, acompanhando o URL final e comprovando que o arquivo é de RIMA. O pacote não é fonte estatística independente.
3. **Terceira:** pedir à ANAC arquivo histórico original ou localização oficial alternativa; registrar protocolo e procedência.
4. **Contingência:** se a indisponibilidade for confirmada, registrar 2019 como indisponível na RIMA, sem inventar competências e sem substituir com RMA/MDIC/Etapa Básica. A adoção de 2020 como início precisa de decisão documentada.

## Portões obrigatórios para autorizar nova coleta

- **P0. Segurança operacional:** gatilhos de diagnóstico excessivos desativados e agendamento de produção pausado; PR #7 continua *draft*, branch main e dashboard intactos.
- **P1. Incidentes antigos:** cada ID tem status, evidência, responsável/ação e desfecho; resolver 2019 ou formalizar contingência de cobertura autorizada e tratar piloto de Etapa Básica separadamente.
- **P2. Contrato de dados:** testes verdes do arquivador **e processador**, com arquivo real, dicionário de códigos, unidades e política de ausência.
- **P3. Qualidade por competência:** contagem, integridade gzip, hash, datas, aeroportos, códigos, nulos, duplicidades, granulosidade e comparação entre meses, mais reconciliador RMA (comparação informativa, não igualação).
- **P4. Confiabilidade:** simular 404 isolado, timeouts, revisão do mesmo mês, colisão de commits, preservação dos meses já arquivados e alertas; definir falha parcial explícita.
- **P5. Governança:** revisar PR, resolver bloqueios do Actions/Pages e **somente então** aprovar fase de expansão.

O monitoramento diário existente deve continuar reportando falhas novas, sem acionar lotes por conta própria. Este documento não encerra as pendências: registra a suspensão e o caminho verificável de resolução.

## Evidências adicionais — sondagens e auditoria de 28/10/2026

**ANAC-01:** A listagem oficial do diretório 2019/ retornou HTTP 200 e revelou cobertura **irregular**, não ausência geral de 2019. Janeiro/2019 não consta da lista e `201901.csv` / `201901.json` retornaram HTTP 404. Fevereiro/2019 consta como **JSON apenas** (`201902.json`): amostra HTTP 206 e tamanho original informado de **147.291.769 bytes**; a amostra contém `NR_NATUREZA: null` em registro de outro aeroporto, o que exige contrato de faltantes e leitura em streaming antes de qualquer uso. Março/2019 tem CSV acessível (HTTP 206, **23.713.701 bytes** indicados). Dezembro/2019 apresenta as variantes `201912.csv` e `201912.csv.csv`, com acesso parcial da segunda (29.070.579 bytes indicados). Não escolher uma sem comparar seus hashes e conteúdo.

**Alternativas para 2019:** (a) listar URLs oficiais e tratar março–dezembro como CSV após concluir os portões; (b) desenvolver leitor JSON em streaming e validar fevereiro; (c) solicitar janeiro à ANAC e registrar sua ausência se não recuperável; (d) se necessário, decidir formalmente uma cobertura a partir de fevereiro ou março de 2019, com lacunas explicitadas. O pacote Ipea `flightsbr` usa o mesmo padrão de URL e não provê cópia alternativa de janeiro.

**ANAC-04:** A auditoria [40682407452](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40682407452) examinou **28.087 linhas SBKP** de 2020-01, 2020-02 e 2024-01, confirmou SHA-256, tamanho, cabeçalho e competência; apurou **0 pesos vazios ou inválidos, 0 linhas inteiramente duplicadas e 0 erros críticos**. Não encerra avaliação de chave de voo, qualidade dos demais meses nem conciliação com RMA.

**ANAC-03:** O processador corrigido passou nos testes do CI [40681363536](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40681363536), mas falta teste de agregação com extrato oficial. **ANAC-07:** diagnósticos e piloto estão restritos a execução manual. **ANAC-05:** `action_required` apareceu em PRs do `github-actions[bot]` sem jobs; não equivale a falha estatística ANAC.

**Evidência detalhada 2019:** [execução 40682498262](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40682498262). Nenhuma série nova foi coletada ou incorporada nesta auditoria. A expansão permanece **bloqueada**.


## Deliberação posterior — recorte temporal oficial 01/01/2020

**Decisão do projeto:** a janela histórica obrigatória começa na competência **2020-01**. A busca de 2019 está **encerrada para o escopo operacional** e suas evidências permanecem para auditoria, sem declarar que o arquivo de janeiro/2019 foi recuperado ou corrigido na ANAC. Não haverá leitor JSON de fevereiro/2019 como requisito do pipeline 2020+.

**ANAC-01 — desfecho: fora do escopo (decisão de cobertura).** Não bloqueia mais P1 por si só. Os demais incidentes **ANAC-02 a ANAC-11** seguem sujeitos aos portões P0–P5 e não foram dispensados. No arquivador e no processador, datas anteriores a 2020-01 passaram a ser recusadas, com testes de regressão. Sem liberação de cron, sem novos downloads, sem alteração do painel.

Documento de referência: [Política do recorte 2020](../../RECORTE_TEMPORAL_2020.md).

## Encerramento de ANAC-03 — processador de registros reais

**Status: concluída tecnicamente em 28/10/2026.** Na [execução #40683558361](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40683558361), os testes offline do processador (10) e de validação cruzada (3) passaram. Os três CSVs SBKP arquivados (2020-01, 2020-02 e 2024-01) foram descompactados com conferência de SHA-256 e processados. Um segundo cálculo independente confirmou as **contagens e somas por natureza e movimento** nos **28.087 registros**, sem divergência registrada. Dados ausentes são mantidos como não informados; grupos sem movimentos não são classificados como tonelagem zero automaticamente.

**Limites do encerramento:** ANAC-03 refere-se exclusivamente ao contrato técnico de leitura/agregação dos três meses existentes. A validação dos demais meses, a comparação com RMA, a governança de revisões e a atualização contínua permanecem abertas (ANAC-04/06/08/09/11). **Não foi liberada publicação nem retomada da carga histórica.**

## Controles ANAC-08 e ANAC-09 — implementação e evidências

**Situação: controles técnicos implementados e aprovados em CI; operação real continua bloqueada pelo ANAC-06 e demais portões.**

- **ANAC-08, versões/rollback:** o arquivador deixa de sobrescrever o arquivo antigo de uma competência quando recebe uma revisão; mantém versões gzip endereçadas por SHA-256, registra recibo e caminho completo de cada versão anterior e audita todos os hashes históricos. Testou inclusive revisão de arquivo **legado** no caminho fixo existente, duas revisões sucessivas e detecção de corrupção de uma versão histórica. **A versão nacional original não é conservada**; guardamos o recorte SBKP e hash/proveniência nacional.
- **ANAC-09, falha parcial/retomada:** o lote é processado em diretório temporário, com publicação do manifesto apenas após validação de todos os meses; simulações isoladas de HTTP 404 e timeout **após um mês bem-sucedido** não modificaram nenhum gzip ou byte do manifesto pré-existente. Em GitHub, o commit só é feito no passo seguinte ao sucesso do script; o `git push` é sem force.
- **Exceções conhecidas:** eventual interrupção física durante cópia de snapshots pode produzir um novo arquivo órfão, não referenciado no manifesto. Não constitui competência validada; requer limpeza/auditoria. Colisões de commit remotas, execução manual da nova rotina e revisão verdadeiramente publicada pela ANAC **ainda não** foram testadas ponta a ponta; permanecem sob **ANAC-06**.
- **Evidência:** [teste de resiliência Actions #40684513195](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40684513195), 12 testes do arquivador, 4 do auditor e leitura de **28.087 registros reais** nas três competências já existentes, todos aprovados. [Validação geral #40684498953](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40684498953) aprovada.
- **Manual de recuperação:** [ARQUIVO_HISTORICO_RIMA.md](ARQUIVO_HISTORICO_RIMA.md).

**Decisão:** encerrar os itens ANAC-08 e ANAC-09 como **controles de código testados**, sem liberar expansão histórica, agendamento ou publicação. A certificação operacional permanece vinculada a ANAC-06/04/11 e ao fechamento dos portões P0–P5.

## Rodada adicional — 28/10/2026 (ANAC-02, ANAC-10, ANAC-11)

**ANAC-02 — encerrada por aposentadoria operacional do piloto Etapa Básica.** O workflow legado `.github/workflows/anac-sbkp-piloto.yml` foi desativado diretamente na `main` no [commit 6202cd22](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/commit/6202cd22dbe47ebab34fa4f3d13b099e0975d279): removido gatilho `push`, job `if: false`, apenas permissão de leitura. [Validação e Pages #40687872477](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40687872477) finalizada com sucesso. **A falha original no ZIP da Etapa Básica não foi corrigida**, pois essa fonte não será usada no pipeline RIMA. Arquivos históricos preservados em Git.

**ANAC-11 — sondagem adicional:** [Actions #40687999846](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40687999846) comprovou pasta-base ANAC HTTP 200 e dezembro/2025 HTTP 206 (controle com `Atualizado em: 2026-10-01`, não necessariamente publicação inicial). Diretório `2026/` e CSV/JSON de janeiro–abril/2026 retornaram HTTP 404, restritos aos caminhos consultados. Consulta técnica à GEIC/ANAC foi preparada como **rascunho não enviado**. [Inventário atualizado](INVENTARIO_DISPONIBILIDADE_2020-2026.md). **ANAC-11 segue aberta**, sem considerar ausência de 2026 como zeros.

**ANAC-10 — certificado TLS da concessionária:** [Actions #40688267605](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40688267605) reproduziu `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate` no Python/Ubuntu para `www.viracopos.com`, `viracopos.com` e página de dados de carga. A página pública de [Estatísticas e Publicações](https://www.viracopos.com/pt_br/institucional/estatisticas-e-publicacoes.htm) está indexada e oferece relatórios RMA em PDF, mas indexação/crawl não substituem HTTPS verificável no nosso pipeline. **Não desabilitar verificação TLS.** Alternativas: correção da cadeia de certificados pela concessionária, endpoint oficial equivalente com certificado válido ou uso apenas de documentos já obtidos e validados; manter a cópia documental opcional pendente. ANAC-10 continua aberta como limitação técnica externa, não bloqueante para o acervo **exclusivamente ANAC**.

**Status de governança:** o painel `main` não recebeu dados ANAC nem alterações visuais. O PR #7 ainda não deve ser mesclado, o arquivador não tem agendamento e seus gatilhos de produção permanecem bloqueados.

## ANAC-06 — validação operacional real de competência única

[Run #40701473352](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40701473352) aprovado: ANAC SBKP **2020-03, 6.881 registros**, manifesto versionado e auditado após `git push` remoto, com 34.968 registros acumulados (2020-01, 2020-02, 2020-03 e 2024-01). Todos os meses anteriores e a `main` foram preservados. Execução por workflow temporário de uso único, removido após sucesso; controle de execução mensal/revisões ainda não autorizado. As duas variáveis de autorização precisam ser redefinidas como **false** manualmente pelo proprietário. [Evidência detalhada](GOVERNANCA_PUBLICACAO_GIT.md).
