# Acervo histórico ANAC/RIMA de Viracopos — segurança e recuperação

**Atualizado:** 28/10/2026. **Janela aprovada:** competências **2020-01 em diante**.  
**Estado:** implementação em branch isolada; PR #7 em rascunho; atualização agendada suspensa; dados ANAC ainda não publicados no dashboard.

## Situação confirmada

Arquivos oficiais filtrados para SBKP e arquivados na branch de desenvolvimento: **2020-01 (9.739 registros), 2020-02 (9.000) e 2024-01 (9.348)**. Auditoria técnica total: **28.087 registros**, SHA-256 verificados, sem erros críticos no escopo auditado. Não equivale à cobertura contínua 2020–presente nem à validação operacional contra o RMA da concessionária.

## Estrutura de armazenamento

```text
data/anac/rima/
  manifesto.json
  sbkp/
    2020/
      2020-01.csv.gz                         # legado, preservado sem sobrescrita
      2020-02.csv.gz
      versoes/
        2020-01/<sha256-do-gzip>.csv.gz       # nova versão imutável, se revisada
    2024/
      2024-01.csv.gz                         # legado, preservado sem sobrescrita
```

Cada arquivo gzip guarda **somente linhas SBKP** com as colunas originais. O manifesto identifica URL, SHA-256 do arquivo nacional original, tamanho, hash do recorte SBKP, total de registros e sucessão de versões completas em `revisoes`. **O original nacional não está armazenado**; seu hash serve para proveniência, não como cópia recuperável. Não inferir equivalência RIMA/Comex/RMA.

## Controle ANAC-08 — revisões históricas

1. Uma nova observação da ANAC com SHA-256 original idêntico é `sem_mudanca`; o arquivo arquivado é conferido antes de reutilizar.
2. Mudança no original gera registro de revisão com o recibo e caminho do snapshot anterior, preservados integralmente.
3. A versão atual usa um caminho novo baseado no hash do **gzip recortado**. Nenhum gzip existente é sobrescrito. Se a origem muda, mas os dados de SBKP continuam iguais, os recibos de origem continuam separados e o mesmo extrato pode ser reutilizado.
4. O auditor verifica a existência e hash de **cada** versão anterior, além da atual. Corrupção de versão antiga reprova auditoria.
5. Git preserva os commits, mas não substitui o manifesto e suas referências verificáveis. Não depender somente do histórico do GitHub para reconstruir revisões.

**Rollback controlado (manual, com revisão):** identificar o commit anterior validado, restaurar **somente** o manifesto desse commit em branch de correção, executar `python scripts/auditar_anac_rima.py`, confirmar paths/hashes e registrar novo commit sem `push --force`. As versões gzip permanecem arquivadas. Não reverter automaticamente a branch padrão nem editar registros em produção sem avaliação.

## Controle ANAC-09 — falhas de download e atomicidade

- O comando de lote trabalha com **cópia temporária isolada** dos dados e do manifesto. A cópia de trabalho só é consolidada após todos os arquivos esperados serem obtidos e validados.
- Se houver HTTP 404, timeout, conteúdo malformado, falha de hash ou qualquer mês reprovado: retorno de erro, **sem alterar o manifesto ou os gzip anteriormente aprovados no diretório principal**. Os resultados temporários são descartados.
- Se o lote for aprovado: arquivos novos imutáveis são copiados primeiro e conferidos; o manifesto é substituído atomicamente **por último**. Uma interrupção física entre essas operações pode deixar um gzip órfão não referenciado, mas não altera o manifesto antigo. Esses órfãos devem ser detectados antes de publicação definitiva; não são promovidos silenciosamente.
- Se um commit remoto concorrente avançar a branch, o `git push` sem force deve rejeitar o update não fast-forward; repetir apenas após conferência/rebase e nova auditoria. Esse cenário ainda exige teste de integração no GitHub (ANAC-06).
- CI de arquivamento somente faz `git add/commit/push` após o comando retornar sucesso. O histórico existente permanece no GitHub em falhas; não há publicação de lote parcial.
- Não executar retries indefinidos; a rotina de download tenta no máximo duas vezes e comunica o erro.

## Evidência de testes

[Execução de resiliência #40684513195](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40684513195): **12 testes do arquivador + 4 testes do auditor passaram**, incluindo revisão sucessiva, compatibilidade com path legado, replay idempotente, HTTP 404/timeout após download bem-sucedido, proteção de lote, corrupção de versão antiga e auditoria dos três meses reais (28.087 registros; sem erros críticos). A execução **não faz download** nem altera o painel. A [validação geral #40684498953](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40684498953) também foi aprovada.

## Portões ainda abertos

- **ANAC-02:** tratar coletor antigo Etapa Básica como sistema estatístico distinto, sem substituir RIMA.
- **ANAC-04:** conciliar RIMA/RMA, grão físico, chaves operacionais e cobertura de novas competências.
- **ANAC-05:** resolver avisos `action_required` e políticas do Actions.
- **ANAC-06:** validar integração final e conflitos de commits; somente depois decidir por cron na branch principal.
- **ANAC-07:** manter diagnósticos restritos, com alertas relevantes.
- **ANAC-10:** TLS da página da concessionária, trilha independente.
- **ANAC-11:** inventário de meses disponíveis e latência real da publicação.

**Portões do projeto:** [Issue #8](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/issues/8) e [registro de pendências](REGISTRO_PENDENCIAS_E_PORTOES_2026-10-28.md). A aprovação de testes offline **não autoriza** backfill adicional, merge nem cron ANAC.
