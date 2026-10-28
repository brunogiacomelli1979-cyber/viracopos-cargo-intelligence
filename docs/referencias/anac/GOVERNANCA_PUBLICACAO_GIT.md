# ANAC-06 — Governança de publicação e concorrência Git

**Data:** 28/10/2026  
**Status:** proteção implementada e **testada com repositórios Git locais**; homologação remota de coleta real ainda pendente.  
**Branch:** `feature/anac-rima-staging-20261028`; PR #7 continua rascunho.

## Controles introduzidos

1. `.github/workflows/arquivar-anac-rima.yml` permanece **sem schedule** e requer simultaneamente `github.ref_name == 'feature/anac-rima-staging-20261028'` **e** variável de repositório `ANAC_RIMA_COLETA_AUTORIZADA == 'true'` para executar seu job. **Não configurar a variável antes de encerrar a Issue #8**. Não houve autorização de coleta no âmbito destes testes.
2. Após o download, o workflow exige auditoria integral `scripts/auditar_anac_rima.py` e verificação de somas `scripts/validar_agrupamento_rima.py`. Um erro interrompe o pipeline antes de qualquer commit.
3. A publicação passou a ser feita por `scripts/publicar_anac_git.py`, que **recusa main** e checkout divergente, mantém escopo restrito a `data/anac/rima`, bloqueia remoção/sobrescrita de `.csv.gz` já commitados, exige manifesto atualizado e só publica se a auditoria integral aprovar.
4. Antes do commit, verifica o HEAD da branch remota por `git ls-remote`. Se a branch avançou, aborta sem tentar mesclar automaticamente. O push normal (nunca `--force`) impede que uma corrida ocorrida **depois** da primeira verificação sobrescreva um commit concorrente.
5. A execução rejeitada termina com erro rastreável; operador deve conferir log, buscar branch atual e repetir a auditoria. **Sem retry automático cego**.

## O que foi testado

- Publicação válida em branch isolada; main permanece com o SHA anterior.
- Repetição sem alterações não cria outro commit.
- Manifesto corrompido e remoção de gzip antigo são rejeitados.
- Conflito prévio: outra execução avançou o HEAD antes da tentativa de publicar.
- Corrida: outra execução fez commit e push **entre** a validação e o `git push`; push do job atrasado foi rejeitado.
- Tentativa de publicação na branch main foi bloqueada.

Todos esses testes rodam com **Git bare/clone local e amostras sintéticas**, sem rede externa e sem acesso à ANAC. Fonte de evidência: [CI de integração offline #40685181500](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40685181500).

## Exigências antes de encerrar ANAC-06 operacionalmente

- Verificar a última execução do CI geral e os testes isolados após integrar o código.
- Decidir/validar política de `action_required` para PR de bot e branch protections, sem confundir bloqueio de aprovação com erro ANAC (ANAC-05).
- Validar permissões reais de escrita no GitHub Actions e aprovação/autorização do operador, **apenas depois de fechar os demais portões**. Não habilitar cron como teste.
- Fazer **um único ensaio operacional controlado** com competência já disponível e autorizada, conferindo resultado remoto, hash, manifestos e rejeição de alterações indevidas; isso não faz parte da rodada offline.
- Verificar que a política de cadência, inventário de competências e cobertura (ANAC-11) não dispara 404 previsível.

**Decisão:** o núcleo de concorrência Git está testado em laboratório, mas **ANAC-06 permanece aberta** até comprovação operacional. Manter a expansão, o merge e a publicação no dashboard suspensos.

[Política de armazenamento e rollback](ARQUIVO_HISTORICO_RIMA.md) · [Registro de pendências](REGISTRO_PENDENCIAS_E_PORTOES_2026-10-28.md) · [Issue #8](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/issues/8).

## Ensaio de escrita remota real — aprovado em 28/10/2026

Foi introduzido o [workflow de homologação sem dados](../../../.github/workflows/ensaiar-publicacao-git-anac.yml) que roda **apenas** na branch `feature/anac-rima-staging-20261028`, com permissão `contents:write` limitada ao job e sem nenhuma requisição à ANAC. O script [`scripts/ensaiar_publicacao_git_anac.py`](../../../scripts/ensaiar_publicacao_git_anac.py) executa:

1. Verificação de contexto (`GITHUB_ACTIONS=true`, repositório e branch autorizados), de arquivos versionados intactos, manifesto/hash do acervo e correspondência entre HEAD local e branch remota.
2. Criação de uma **ref temporária de teste** em `ci/anac06-probe-<run>-<attempt>`, apontando somente para o SHA já existente da branch de homologação. Não cria commits, CSVs, relatórios RMA, nem altera `main`.
3. Leitura da referência recém-publicada diretamente no servidor para conferir o SHA.
4. Remoção da ref no mesmo job, também com conferência remota. O teste é reprovado se a limpeza falhar, se o SHA da ref não for esperado ou se `main`/homologação divergirem.
5. Testes de regressão com repositórios Git `bare` locais: criação/verificação/remoção sem alteração dos HEADs, recusa de `tracked` modificado, recusa fora do GitHub Actions, sanitização de identificadores.

**Primeira execução:** [#40695764521](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40695764521) reprovou porque um relatório temporário não versionado deixou a working tree suja. A escrita remota não foi iniciada. **Segunda:** [#40695884637](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40695884637) identificou um teste com mensagem antiga, corrigido. Nenhuma referência temporária foi criada nessa execução. Ambas as falhas foram tratadas e não omitidas.

**Execução aprovada:** [GitHub Actions #40695960222](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40695960222); [evidência JSON (artefato 12819212862)](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40695960222/artifacts/12819212862). Criou e removeu `ci/anac06-probe-40695960222-1`, verificou SHA de origem, e confirmou:
- `ref_removida=true`; nenhum prefixo `ci/anac06-probe` ficou listado entre as branches do repositório.
- `main_inalterada=true`; SHA da `main`: `6202cd22dbe47ebab34fa4f3d13b099e0975d279`.
- `homologacao_inalterada=true` durante o teste; SHA: `1b7df6505e2ab940c4523d99bd99ca3ab9ebffb4`.
- Auditoria dos **3 meses ANAC existentes** aprovada, sem coleta adicional.
- [Validação geral #40695971955](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40695971955) concluída com sucesso, sem deploy da PR.

### Escopo de aprovação e pendência residual

**Aprovado:** permissão de escrita remota do token GitHub Actions em ref de ensaio isolada, criação/leitura/remoção e preservação de `main` e homologação. Isso vai além dos testes em repositório Git local.

**Ainda não comprovado:** um `git commit` e `git push` de **novo extrato ANAC validado** pelo script real `scripts/publicar_anac_git.py` para a branch de homologação sob políticas de publicação operacionais. A coleta continua suspensa até ANAC-04/10/11 e demais portões pertinentes. A criação de uma ref temporária **não é** demonstração de backfill/cron funcional. **ANAC-06 permanece aberta**, agora com controle de permissões remotas encerrado como subetapa.

Em caso de falha futura, verificar as referências `ci/anac06-probe-*` e a evidência de limpeza antes de reexecutar. Nunca excluir uma referência cujo SHA não coincida com o commit originalmente registrado pelo teste.

## Ensaio do publicador real sem mudanças — 28/10/2026

[GitHub Actions #40696736471 — `success`](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40696736471) executou diretamente `scripts/publicar_anac_git.py` sobre os **três meses ANAC atuais**, após testes locais do publicador e auditoria do manifesto. A execução usou o repositório/branch remotos verdadeiros, mas **sem novo mês**. O script devolveu `sem_alteracoes` e não criou commit. Verificação automática confirmou byte a byte o manifesto, o objeto Git da pasta `data/anac/rima`, o `HEAD` local, o SHA remoto de `main` e o SHA remoto da branch de homologação, todos inalterados. A permissão do job era **somente leitura**; um push acidental seria recusado pela plataforma. O ensaio demonstrou **idempotência em runner real**, não a publicação de um novo CSV.

**Preparação da próxima etapa (ainda não executada):** workflow de coleta manual temporariamente restringido a **2020-03**, início=fim=2020-03, limite=**1** e modo inicial, para impedir uma solicitação acidental sem limite. Além do bloqueio original, adicionada segunda autorização explícita `ANAC_RIMA_PILOTO_202003_AUTORIZADO == 'true'`, e confirmada condição `ANAC_RIMA_COLETA_AUTORIZADA == 'true'`. Por padrão, sem ambas as variáveis habilitadas, **nenhuma coleta ocorre**. Sem cron/push automático. [Teste offline #40696946942 — aprovado](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40696946942).

**Pendente ANAC-06:** uma execução controlada do arquivador oficial para 2020-03, auditando o novo gzip e manifesto antes de qualquer commit, e depois verificando por clone remoto o registro da competência, versões anteriores, revisão/hashes e ausência de modificações na `main`. Nenhuma variável foi alterada no repositório, nem o piloto foi acionado. A aprovação do teste `noop` não prova download/publicação.

**E-mails auditados na mesma data:** Gmail retornou 9 notificações `Run failed` de commits anteriores (todas anteriores às validações atuais). As causas dos erros do ensaio de escrita e da prévia foram corrigidas, conforme os registros desta Issue; o último Pages e o último ensaio ANAC não apresentam falha ativa. As notificações foram mantidas na caixa de entrada sem manipulação.

## Novos portões integrados ANAC-06 — 28/10/2026

**Integração de ponta a ponta com origem simulada e Git real local:** [Actions #40697742344 — sucesso](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40697742344) cobriu extrato sintético 2020-03 passando por `run()` do arquivador, staging, manifesto, `inspect()`, segunda somatória `validate()`, commit real feito por `publicar_anac_git.py`, push para Git bare local, clone independente e confirmação de hashes/conteúdo, idempotência sem segundo commit, erro HTTP 404 sem alterar o acervo e peso inválido recusado. **Nenhuma requisição ao servidor ANAC e nenhum dado sintético foi colocado no repositório real.**

**Fechamento de brecha de publicação:** o publicador agora monta o conjunto de snapshots permitidos a partir do manifesto vigente e histórico de revisões. Um `.csv.gz` **órfão**, não apontado por nenhuma competência/revisão, é bloqueado mesmo quando o manifesto foi legitimamente modificado. Teste de regressão no mesmo CI.

**QA integral antes da promoção local:** o coletor passou a executar `auditar_anac_rima.inspect` e `validar_agrupamento_rima.validate` **sobre o staging**, antes de promover o lote. Se houver peso negativo, coluna inválida ou somatória divergente, encerra com erro e mantém o manifesto e os gzip existentes byte a byte idênticos, não apenas o commit remoto. Confirmado pelo [CI de resiliência #40698006049](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40698006049) e [#40698017712 (validação geral)](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40698017712).

**Auditoria pós-push já incorporada ao workflow restrito:** `scripts/verificar_publicacao_anac_rima.py` lê SHA remoto após `git fetch`, monta uma worktree destacada do commit remoto, executa auditoria de integridade e somas independentes, confirma que o único novo mês é 2020-03, compara as competências preexistentes sem alteração, restringe o diff a manifesto e novo gzip e verifica que a `main` conservou o SHA anterior. Também aceita uma repetição idempotente sem commit. Testes de push correto, alteração não autorizada e mudança da main aprovados em [Actions #40698440979](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40698440979). **Estes testes usam Git bare local; o procedimento pós-push real está instalado, não executado.**

**Portão ainda em vigor:** o workflow `arquivar-anac-rima.yml` só permite `workflow_dispatch` na branch de homologação, com competência **2020-03**, limite **1**, sem agendamento e exigindo **ambas** as variáveis `ANAC_RIMA_COLETA_AUTORIZADA=true` e `ANAC_RIMA_PILOTO_202003_AUTORIZADO=true`. **Nenhuma variável foi ativada e não houve download/commit de março de 2020.** ANAC-06 permanece **aberta para o ensaio controlado real e verificação posterior**. A `main` e o dashboard não foram modificados.

## Abertura segura do botão manual — 28/10/2026

**Bloqueio operacional corrigido:** de acordo com a [documentação oficial do GitHub](https://docs.github.com/pt/actions/how-tos/manage-workflow-runs/manually-run-a-workflow), um workflow `workflow_dispatch` precisa estar registrado na **branch padrão** para disponibilizar o acionamento manual. Até aqui, `.github/workflows/arquivar-anac-rima.yml` existia apenas em homologação — os testes de fluxo local e os ensaios em refs remotas não demonstravam que o botão de disparo estaria disponível.

Foi adicionado **somente o ponto de entrada inativo** na `main`, no [commit a06a4bcf](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/commit/a06a4bcfb12c10a2aa7e04bc434112c535b270d4). Esse arquivo contém `permissions: contents: read` e job com `if: false`, de modo que selecionar a branch `main` no menu de execução não pode baixar dados. A branch de homologação mantém, no mesmo caminho, o workflow real com controles de competência 2020-03, duas variáveis, auditoria pré e pós-push e publicação exclusiva na própria branch.

As branches foram sincronizadas por merge **sem trocar o conteúdo do workflow protegido na homologação**; o PR #7 voltou a informar `mergeable=true`. A [validação da main #40699040758](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40699040758) e a [validação da homologação #40699099835](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40699099835) terminaram com sucesso. Nenhum arquivo `data/`, `index.html`, `assets/` ou dashboard foi alterado na main.

**Melhoria de clareza:** o workflow de homologação possui agora um job de checagem **somente leitura** que avalia as autorizações sem baixar arquivos. Se alguma não estiver `true`, registra no resumo **"NÃO EXECUTADO"**, retorna `autorizado=false` e impede a execução do job de coleta. Isso não é uma execução bem-sucedida do arquivador e não deve ser contado como mês arquivado. A checagem duplicada no job `archive` permanece para defesa em profundidade.

### Instruções para disparo do piloto quando as permissões forem habilitadas

1. Em **Settings → Secrets and variables → Actions → Variables**, cadastrar ou habilitar **duas variáveis de repositório**: `ANAC_RIMA_COLETA_AUTORIZADA` = `true` e `ANAC_RIMA_PILOTO_202003_AUTORIZADO` = `true`. Não colocar tokens ou senhas nessas variáveis; são apenas chaves de autorização.
2. Em **Actions**, selecionar **“Arquivar ANAC RIMA SBKP — piloto restrito 2020-03”** e clicar em **Run workflow / Executar fluxo de trabalho**.
3. Selecionar **a branch `feature/anac-rima-staging-20261028`**, nunca `main`, e `confirmar_competencia = 2020-03`.
4. Confirmar no log que **`verificar-autorizacao` e `archive` efetivamente executaram**, que o arquivador reportou 1 novo mês, que `scripts/auditar_anac_rima.py` e `scripts/validar_agrupamento_rima.py` passaram e que a auditoria pós-push gravou `status: novo_mes_confirmado`. A existência de um run com `success` **sem job de coleta executado** não valida o piloto.
5. Após o piloto, retornar as duas variáveis a `false` (ou removê-las) e documentar na Issue #8 o run e o recibo por SHA-256. **Não iniciar outros meses nem ativar schedule automaticamente**.

**Limitação das ferramentas de integração nesta conversa:** o conector GitHub disponível permite consultar e modificar arquivos do repositório, mas não expõe operações para gerenciar variáveis de Actions nem despachar esse workflow. Por isso, nenhum dos passos acima foi efetuado automaticamente e não é correto declarar a coleta real como feita.
