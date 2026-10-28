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
