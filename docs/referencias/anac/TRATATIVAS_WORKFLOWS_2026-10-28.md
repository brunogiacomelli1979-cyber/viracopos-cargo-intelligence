# Tratativas de GitHub Actions e notificações — 28/10/2026

**Projeto:** Viracopos Cargo Intelligence  
**Escopo:** ANAC-02 (legado Etapa Básica), ANAC-05 (`action_required`), ANAC-07 (gatilhos de diagnóstico)  
**Situação:** revisão aprovada **na branch de desenvolvimento**; a branch principal ainda contém versões antigas de alguns workflows. Não autoriza merge do PR #7 nem retomada de downloads.

## Evidência de validação

- [Execução #40686532757](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40686532757): validação geral **success**, **77 testes Python aprovados**, incluindo quatro novos testes de proteção dos workflows.
- [Execução #40686525828](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40686525828): auditoria **success**, preservando os três meses reais do acervo.
- Nenhum novo mês ANAC foi coletado nesta mudança; nenhum arquivo do dashboard foi alterado.

## Mudanças implementadas em homologação

| Workflow | Tratativa | Situação |
|---|---|---|
| `anac-sbkp-piloto.yml` | Piloto antigo **Etapa Básica**: desativado, sem gatilhos de push nem permissão de escrita | **Desativado na branch; ainda presente na main** |
| `piloto-anac-rima-2019.yml` | Piloto de coleta que poderia contornar a autorização: desativado, preservado para rastreio | Desativado na branch |
| `testar-acesso-anac-rima.yml` | Diagnóstico antigo que fazia download e commit sem a autorização do novo arquivador: desativado | Desativado na branch |
| `inspecionar-anac-2019.yml` | Investigação fora do recorte aprovado 2020+: desativada; removeu gatilho automático | Desativado na branch |
| `auditar-pendencias-anac.yml` | Removidas consultas ao servidor de 2019; passou a auditar somente dados locais | **Execução confirmada sem rede da ANAC** |
| `sondar-disponibilidade-anac-rima.yml` | Sondagem manual passa a olhar de 2020 em diante | Configuração ajustada; não executada após mudança |
| `arquivar-anac-rima.yml` | Continua protegido por branch específica e variável `ANAC_RIMA_COLETA_AUTORIZADA`; sem cron/push | Bloqueado |

## Sobre os avisos `action_required` (ANAC-05)

Há eventos anteriores de `Validar e publicar Pages` para pull requests atualizados por `github-actions[bot]`, com `conclusion=action_required` e **nenhum job iniciado** (ex.: [#40680332556](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40680332556)). A política oficial do GitHub, atualizada em junho de 2026, exige aprovação de usuário com acesso de escrita para CI em PRs criados/atualizados por `GITHUB_TOKEN`. Isso não é falha do parser ANAC ou de testes estatísticos.

**Tratativa segura:** manter aprovação humana; evitar PRs/execuções do bot não necessárias; revisar no GitHub a página do PR e usar **Approve workflows to run** apenas após inspecionar os arquivos do PR. Não sugerir desativar requisitos de aprovação por segurança e não atribuir `action_required` a um erro de coleta. Nas últimas execuções criadas pelo usuário, o Pages validou normalmente.

Documentação oficial:
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow
- https://github.blog/changelog/2026-06-11-bot-created-pull-requests-can-run-workflows-if-approved/

**Pendente de decisão humana:** aprovar, cancelar ou ignorar eventos `action_required` antigos; não aprovar automaticamente a execução de código ainda não revisado. O monitoramento diário continua distinguindo esse estado de `failure`.

## Portões e responsabilidades

- **ANAC-02:** desativação do coletor obsoleto comprovada na branch. Só pode ser encerrada em todo o repositório após incorporar a mudança à main ou formalizar a descontinuação do arquivo da main. Seu problema original (ZIP da Etapa Básica) **não foi corrigido**, porque é outra população estatística.
- **ANAC-05:** classificação dos eventos confirmada pela documentação oficial; ainda exige decisão de aprovação no próprio GitHub, quando aplicável. Sem autocorreção do código para contornar política de segurança.
- **ANAC-07:** gatilhos perigosos desativados e teste de regressão no CI aprovado para a branch. Pode ser encerrada como **controle de homologação**, sem implicar liberação de produção.
- **ANAC-06:** ainda aberta, pois testes locais de concorrência não substituem execução autorizada e monitorada em repositório remoto.
- **ANAC-11:** inventário oficial dos meses 2020+ ainda pendente; não confundir a retirada de 2019 com cobertura concluída.

[Issue #8](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/issues/8) · [Política de recorte 2020+](../../RECORTE_TEMPORAL_2020.md) · [Governança de publicação](GOVERNANCA_PUBLICACAO_GIT.md)
