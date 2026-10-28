# Ingestão controlada ANAC/RIMA SBKP — marco 1

**Data:** 28/10/2026
**Branch:** feature/anac-ingestao-controlada-20261028 (baseada na homologação ANAC/RIMA).
**Regra operacional:** sem novos downloads, sem cron, sem merge do PR #7 e sem indicadores ANAC no dashboard até passar os portões de qualidade.

## Diagnóstico e objetivo

O coletor atual baixa o CSV nacional inteiro em memória, separa SBKP e conserva apenas o recorte comprimido, o hash SHA-256 do original e o recibo. Isso protege a integridade do recorte, mas **não preserva o original nacional para reprocessamento**. Mudanças no parser podem exigir novos downloads e gerar retrabalho.

Adotamos as camadas: inventário -> arquivo bruto -> recorte SBKP -> auditoria -> publicação. Este marco implementa os controles offline do inventário e do arquivo bruto, sem alterar o coletor atual.

## Componentes implementados

1. **Inventário** — data/anac/rima/inventario_disponibilidade.json é uma fotografia das listagens oficiais ANAC de 28/10/2026 com evidência [Actions #40687137171](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40687137171). Há 72 competências CSV listadas em 2020–2025. Listagem **não comprova** integridade do conteúdo, existência de linhas SBKP nem download integral. O índice 2026 estava indisponível no endereço consultado.
2. **Planejador** — scripts/planejar_coleta_anac.py lê o inventário e manifesto locais, não usa rede e classifica competências como arquivado_pendente_reauditoria, listado_pendente_captura, nao_listado_no_indice, indice_indisponivel ou nao_inventariado. Para 2020–2025, resulta em 4 meses arquivados e 68 ainda pendentes de coleta.
3. **Cofre bruto offline** — scripts/acervo_bruto_anac.py recebe CSV oficial **já existente no computador**, copia o original em blocos para pasta durável **fora do Git**, calcula SHA-256, preserva versões e registra recibos imutáveis. Rejeita arquivo vazio/HTML, cabeçalho ausente, tamanho excessivo, URL incompatível e diretório de destino dentro do repositório.
4. **Downloader HTTPS isolado** — scripts/baixar_original_anac.py executa somente quando chamado explicitamente por código; usa streaming em blocos, TLS válido, rejeita HTTP 206 e respostas truncadas, limita retries para erros transitórios, distingue 404 e respeita Retry-After (até 60 s). **Não há nenhum workflow ou agendamento que o invoque.**
5. **Auditoria offline** — valida hashes, recibos, objetos órfãos e rejeita acervo vazio. Diferencia bytes preservados de dados estatisticamente validados.
6. **Testes** — tests/test_ingestao_controlada_anac.py (10 casos) e tests/test_baixar_original_anac.py (9 casos). **19 testes locais aprovados**, todos com rede simulada e sem publicação.

## Uso sem rede

~~~sh
python scripts/planejar_coleta_anac.py --inicio 2020-01 --fim 2025-12
python scripts/planejar_coleta_anac.py --inicio 2026-01 --fim 2026-04
python -m unittest discover -s tests -p test_ingestao_controlada_anac.py -v
python -m unittest discover -s tests -p test_baixar_original_anac.py -v

# Exemplo SOMENTE com original previamente obtido e volume persistente provisionado:
python scripts/acervo_bruto_anac.py registrar \
 --arquivo /originais/Movimentacoes_Aeroportuarias_202004.csv \
 --competencia 2020-04 \
 --url "https://sistemas.anac.gov.br/dadosabertos/Operador%20Aeroportu%C3%A1rio/Dados%20de%20Movimenta%C3%A7%C3%A3o%20Aeroportu%C3%A1rias/2020/Movimentacoes_Aeroportuarias_202004.csv" \
 --acervo /volume-persistente/vcp-anac-brutos

python scripts/acervo_bruto_anac.py auditar --acervo /volume-persistente/vcp-anac-brutos
~~~

O registro bruto **não baixa** arquivos, não modifica o manifesto SBKP, não publica números e informa bruto_preservado_nao_validado. Antes de qualquer aquisição, **provisionar e testar cópia durável e backup**; runner efêmero ou artefato temporário do GitHub Actions não constituem arquivo permanente.

## Portões de implementação

| Portão | Requisito | Estado |
|---|---|---|
| G0 | Sem novos lotes, main e dashboard isolados | Princípio observado nesta entrega; variáveis de Actions ainda não verificadas |
| G1 | Inventário com evidências e estados corretos | Implementado offline |
| G2 | Cofre imutável, hashes, recibos e auditoria | Implementado em código e testes locais; infraestrutura persistente não provisionada |
| G3 | Download streaming, TLS, retries seletivos e cache | Módulo streaming isolado e testes simulados aprovados; **cache/reuso online e integração ao coletor legado ainda pendentes** |
| G4 | Grão, campos, nulos, duplicatas, agregação e reconciliação RMA | **Pendente** para toda a série |
| G5 | Piloto de competência nova com auditoria local e pós-push | **Bloqueado**, não autorizado |
| G6 | Expansão 1 -> 3 -> 6 meses e cron | **Bloqueado**, não autorizado |

## Política para erros na etapa online

- 404: origem_nao_encontrada; atualizar inventário/URL e nunca insistir cegamente.
- Timeout, 429 ou 5xx: falha transitória; retries limitados, backoff e respeito a Retry-After.
- HTTP 206: não aceitar como arquivo integral sem protocolo explícito de ranges e checagem completa.
- TLS: validar certificado, nunca ignorar erros.
- Hash novo: considerar revisão e preservar as versões, sem sobrescrever.
- Layout desconhecido: preservar bruto em quarentena, sem liberar recortes.
- Inconsistência estatística: bloquear o indicador afetado até apuração; não inventar zero ou excluir linhas automaticamente.
- Falha de publicação Git: manter acervo e recibos aprovados; não repetir o download.

Diferenças legítimas ANAC/RIMA x RMA x MDIC devem ser documentadas por população, unidade e período. Nem todo voo transporta carga. Carga ausente, carga igual a zero, voo sem carga e competência não publicada são situações distintas.

## Pendências abertas

- ANAC-04: perfil quantitativo por competência e validação do grão/duplicatas.
- ANAC-06: piloto 2020-03 passou no GitHub, **sem autorizar** lotes adicionais ou cron; as variáveis temporárias de autorização precisam ser verificadas e desativadas pelo proprietário.
- ANAC-10: TLS da concessionária é uma limitação externa independente.
- ANAC-11: disponibilidade real e calendário de 2026 ainda não certificados.

[Issue de governança #8](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/issues/8) · [Inventário histórico](INVENTARIO_DISPONIBILIDADE_2020-2026.md) · [Registro de incidentes](REGISTRO_PENDENCIAS_E_PORTOES_2026-10-28.md)

**Próximo marco:** integrar a reutilização do bruto ao parser SBKP e ao planejamento de competências, provisionar armazenamento persistente com backup, testar restauração e só então desenhar piloto real autorizado. O streaming já tem testes simulados, mas **não foi executado contra a ANAC real**. Nenhuma automação de download é habilitada por este documento.


## Marco 2 — Reprocessamento offline de bruto imutável

Foi adicionado o modulo **scripts/reprocessar_bruto_anac.py** com teste **tests/test_reprocessar_bruto_anac.py**. Ele exige uma competencia e o SHA-256 exato do original guardado; confere o recibo e hash antes de processar. Le o CSV nacional em fluxo, detecta UTF-8/CP1252, respeita preambulo, valida colunas, seleciona exclusivamente SBKP, verifica competencia e codigos, e gera gzip deterministico. Em seguida reutiliza **processar_anac_rima.process_file** para verificar pesos, nulos, contagens e agregacoes do recorte. O pacote inclui hash do original, hash do CSV SBKP, hash do gzip, grupos e estado **staging_validado_local_nao_publicado**.

**Sem acesso a rede, sem alteracao do manifesto historico ou do dashboard**. Saidas so podem ficar fora do repositorio ou em data/staging (ignorado pelo Git). Uma revisao original exige SHA explicito e gera pacote distinto; replay confere integridade antes de reaproveitar. Arquivos corrompidos, preambulo desconhecido, peso invalido, ausencia de SBKP ou divergencia de SHA interrompem a operacao.

Exemplo com um bruto **ja arquivado no cofre persistente**:

~~~sh
python scripts/reprocessar_bruto_anac.py \
  --acervo /volume-persistente/vcp-anac-brutos \
  --competencia 2020-04 \
  --sha256 HASH_REAL_DO_ARQUIVO_BRUTO \
  --saida data/staging/anac-reprocessados

python -m unittest discover -s tests -p test_reprocessar_bruto_anac.py -v
~~~

**Limites:** a validação dessa etapa é local, não equivale à reconciliação com RMA nem substitui a auditoria de manifesto/gzip do arquivador oficial. A publicação versionada do pacote em data/anac/rima continua desabilitada. Ainda precisamos testar estes novos casos no CI, manter cópia persistente externa com backup e fechar a qualidade ANAC-04 antes de autorizar um novo mês.

