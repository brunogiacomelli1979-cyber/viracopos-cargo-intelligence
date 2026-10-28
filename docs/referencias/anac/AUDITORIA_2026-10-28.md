# Auditoria de integridade do acervo ANAC — 28/10/2026

## Escopo

Verificação de leitura e integridade dos originais **já arquivados na branch `main`** e identificados em [`manifesto.json`](manifesto.json). Não representa nova coleta das URLs oficiais, interpretação jurídica de vigência ou ingestão de séries históricas no painel.

## Resultado

- Manifesto consultado: captura declarada de **27/10/2026, 21:44:34 UTC**.
- **10 referências catalogadas:** 8 essenciais e 2 complementares.
- **9 originais arquivados e conferidos:** 8 essenciais e 1 complementar.
- **0 documentos essenciais pendentes**, segundo manifesto e presença dos arquivos consultados.
- Os **9 originais conferidos** apresentaram comprimento em bytes, SHA-256 recalculado e assinatura de formato compatíveis com o manifesto.
- **1 complementar pendente:** `pagina_referencias_concessionaria_vcp`. O coletor registrou `CERTIFICATE_VERIFY_FAILED` ao tentar abrir `https://www.viracopos.com/pt_br/institucional/estatisticas-e-publicacoes.htm`. Não houve bypass de TLS.
- Uma primeira tentativa de leitura do original `02_resolucao_191_2011.html` falhou por erro transitório de conexão; leitura e hash foram concluídos em nova tentativa, sem divergência.

### Itens conferidos

| ID | Tipo | Resultado |
|---|---|---|
| `metadados_etapa_basica` | HTML | Tamanho, SHA-256 e formato consistentes |
| `resolucao_191_2011` | HTML | Tamanho, SHA-256 e formato consistentes |
| `portaria_3506_2019_compilada` | PDF | Tamanho, SHA-256 e formato consistentes |
| `portaria_3507_2019_compilada` | PDF | Tamanho, SHA-256 e formato consistentes |
| `resolucao_464_2018` | HTML | Tamanho, SHA-256 e formato consistentes |
| `portaria_1017_2018_compilada_2176_2019` | PDF | Tamanho, SHA-256 e formato consistentes |
| `metadados_movimentacao_aeroportuaria` | HTML | Tamanho, SHA-256 e formato consistentes |
| `portaria_3902_2019_alteracao` | PDF | Tamanho, SHA-256 e formato consistentes |
| `metadados_movimentacao_anac_govbr` | HTML | Tamanho, SHA-256 e formato consistentes |

**Método:** leitura dos originais binários via integração GitHub, decodificação e cálculo independente de SHA-256, conferência do tamanho e das assinaturas HTML/PDF contra os valores declarados no manifesto. A rotina Python `scripts/validar_acervo_anac.py` **não foi executada localmente nesta auditoria**; também não se declara uma nova execução bem-sucedida do workflow Actions. Os hashes íntegros estão no manifesto, que permanece como referência primária.

## Pendências para a próxima etapa

1. **Vigência normativa:** confrontar documentos de 2011/2018/2019 e suas alterações com a regulamentação efetivamente aplicável ao período de cada dado. A integridade do arquivo não comprova vigência.
2. **Universos estatísticos:** manter separadas a Etapa Básica (trechos informados por empresas aéreas), a Movimentação Aeroportuária (operadores aeroportuários), o RMA da concessionária e o Comex/MDIC. Não somar ou substituir populações sem conciliação.
3. **Dicionários e ausências:** documentar unidades, grão, carga/correio, sentidos e interpretação de valores ausentes antes da ingestão da nova base ANAC.
4. **Fonte complementar da concessionária:** investigar cadeia de certificados TLS/alternativa oficial verificável; nunca desabilitar a validação HTTPS. Esta pendência não bloqueia a etapa documental essencial ANAC.
5. **Validação operacional:** antes de usar as novas séries no painel, executar o validador do acervo e testes de dados no ambiente de CI, com evidência de execução.

## Decisão de passagem

**Acervo documental essencial apto para iniciar a especificação da Etapa 2 (ANAC)**, sem autorização implícita para publicar indicadores ou previsões. Qualquer ingestão permanece condicionada aos dicionários, conciliação entre fontes e testes de integridade das séries.

Referências internas: [nota de curadoria](NOTA_DE_CURADORIA.md), [inventário](README.md), [manifesto](manifesto.json), [backlog](../../backlog.md).
