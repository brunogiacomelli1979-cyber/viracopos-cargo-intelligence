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

Foi introduzido o [workflow de homologação sem dados](../../../../.github/workflows/ensaiar-publicacao-git-anac.yml) que roda **apenas** na branch `feature/anac-rima-staging-20261028`, com permissão `contents:write` limitada ao job e sem nenhuma requisição à ANAC. O script [`scripts/ensaiar_publicacao_git_anac.py`](../../../scripts/ensaiar_publicacao_git_anac.py) executa:

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
