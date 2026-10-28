# Consulta técnica à ANAC — identificação operacional de colisão T/Z no RIMA SBKP

**Estado:** MINUTA, NÃO ENVIADA. Data: 28/10/2026. Aguardando revisão humana e, caso apropriado, envio institucional. Não inclui matrícula, número de voo, horários de operação ou dados pessoais.

**Área ANAC sugerida:** GEIC — geic@anac.gov.br (contato publicado nos metadados dos Dados de Movimentação Aeroportuária).

**Assunto sugerido:** Esclarecimento metodológico RIMA: movimentos SBKP com mesma chave de toque e códigos T/Z distintos

## Contexto técnico

Realizamos auditoria exclusivamente offline de quatro arquivos oficiais de dados abertos de movimentação aeroportuária SBKP: janeiro, fevereiro e março de 2020 e janeiro de 2024, totalizando 34.968 linhas. Conferimos SHA-256, competência, somas, linhas, valores ausentes, duplicatas exatas e chaves operacionais candidatas.

No recorte de março de 2020, observamos duas linhas classificadas como decolagem doméstica com a mesma matrícula, mesma data/hora de toque, mesmo número de voo informado e mesmo aeroporto relacionado, mas diferentes entre si quanto a SERVICE_TYPE (T e Z) e HH_CALCO. A variável QT_CARGA não difere entre as duas linhas. Não encontramos duas linhas integralmente idênticas. Os exemplos não são apresentados aqui em nível identificável.

A Portaria nº 1.017/SRA/SIA/2018, alterada pela Portaria nº 2.176/2019, estabelece COD_RIMA como código da operação, NR_SERVICE_TYPE Z para voo de retorno e o movimento da competência referenciado ao calço/descalço. Já o dicionário da base pública ANAC classifica T como teste técnico, mas o arquivo aberto examinado não dispõe do campo COD_RIMA.

## Perguntas objetivas para esclarecimento pela GEIC

1. Qual é o **grão físico efetivo** da base aberta de Movimentação Aeroportuária (RIMA): uma linha por movimento de pouso/decolagem ou há hipóteses legítimas de múltiplas linhas para um mesmo toque de rodas?
2. Em uma decolagem identificada pelo mesmo horário de toque, mesma matrícula e mesmo número de voo, é válida a existência de duas linhas com SERVICE_TYPE distintos, incluindo **T (teste técnico)** e **Z (retorno)**? Em quais cenários operacionais?
3. O campo **COD_RIMA** descrito na Portaria pode ser consultado, total ou parcialmente anonimizado, para confirmar se as duas linhas correspondem à mesma operação de pátio, a eventos distintos ou a uma revisão de registro? Há identificador equivalente na extração aberta?
4. A ANAC considera **NR_VOO_NUMERO** (inclusive valor 0, quando não se aplica) uma chave para unicidade? Quais campos formam a chave operacional recomendada para auditoria do RIMA?
5. Quando duas linhas têm a mesma chave candidata de toque mas diferentes valores de **HH_CALCO**, qual é a política de correção, classificação ou contagem recomendada? O procedimento deve preservar ambas até conferência com o administrador aeroportuário?
6. Existe documentação de regras de **revisão histórica** para os arquivos nacionais mensais, inclusive como distinguir republicação/correção de operação anteriormente registrada?

## Política até resposta oficial

- Preservar ambas as linhas exatamente como publicadas e suas somas. Não deduplicar ou imputar.
- Marcar a colisão como **sem_criterio_de_unicidade_homologado**.
- Não usar o número de movimentos como proxy de voos exclusivamente cargueiros.
- Publicação de indicadores, novas coletas ou cron permanecem bloqueados pelos portões do projeto.
- Registrar eventual resposta institucional com data, procedência, critério e teste de regressão antes de mudar a transformação.

## Referências oficiais

- Metadados ANAC: https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/operador-aeroportuario/dados-de-movimentacao-aeroportuaria/60-dados-de-movimentacao-aeroportuaria
- Portaria nº 1.017/2018 (texto compilado com alterações de 2019): https://pergamum.anac.gov.br/pergamum/vinculos/PA2018-1017.pdf
- Relatório técnico do projeto: ANAC04_PERFIL_QUALIDADE_2026-10-28.md
- Evidências: logs de CI no PR #9 (não inserir identificadores de voos em mensagens públicas).

**Controle:** este arquivo é somente uma proposta de pergunta institucional; não aciona Gmail, rede ANAC, workflow, publicação ou downloads.
