# Diagnóstico de acesso à base ANAC — 28/10/2026

## Resumo executivo

**Não há evidência suficiente de que o conjunto ANAC/RIMA esteja globalmente indisponível, corrompido ou extinto.** A dificuldade documentada combina caminhos de download em servidores diferentes, restrições de acesso automatizado neste ambiente, uma coletora ANAC/RIMA ainda não implementada e defasagem de publicação inerente à fonte. Não atribuir falhas da concessionária à ANAC.

## O que foi observado

| Camada | Evidência | Conclusão permitida |
|---|---|---|
| Portal de metadados | Página oficial da ANAC de dados RIMA acessível por resultados indexados, definindo campos e atualização mensal com atraso de 6 meses | Documentação existe; não demonstra que o arquivo CSV esteja acessível agora |
| Página índice de arquivos | Link oficial de arquivos CSV/JSON redireciona para `https://sistemas.anac.gov.br/dadosabertos/Operador%20Aeroportu%C3%A1rio/Dados%20de%20Movimenta%C3%A7%C3%A3o%20Aeroportu%C3%A1rias/` | Há redirecionamento entre portais e servidor de arquivos; ferramenta de consulta não abriu destino |
| Portal gov.br | Em tentativa de leitura automática de metadados, resposta retornou desafio de verificação humana | Proteção anti-robô observada nesta sessão; não comprova indisponibilidade para navegador |
| Ambiente de execução local | Teste de rede não conseguiu resolver DNS para `sistemas.anac.gov.br` e `www.gov.br`; também falhou para `github.com` | **Restrição de rede do ambiente local de teste**, não evidência de queda dos sites |
| Catálogo documental próprio | Nove documentos originais arquivados com SHA-256 correto; uma pendência opcional era a página de **Viracopos/concessionária** com `CERTIFICATE_VERIFY_FAILED` | Falha TLS registrada para concessionária, **não** para o dataset RIMA |
| Processamento atual | `scripts/processar_anac_rima.py` aceita CSV mensal local, mas não possui função de download nem foi validado contra CSV oficial | Não há até agora pipeline ANAC real completo; testes sintéticos não provam compatibilidade real |

## Caminho técnico conhecido de arquivos

O pacote aberto [flightsbr do Ipea](https://github.com/ipea/flightsbr) possui função `read_airport_movements()` e documenta arquivos mensais desde jan/2019, com convenção de nomes:

```text
https://sistemas.anac.gov.br/dadosabertos/Operador%20Aeroportu%C3%A1rio/Dados%20de%20Movimenta%C3%A7%C3%A3o%20Aeroportu%C3%A1rias/{ANO}/Movimentacoes_Aeroportuarias_{AAAAMM}.csv
```

Isto é um **padrão identificado no código de terceiro, não uma URL cuja disponibilidade atual foi verificada por download nesta sessão**. O projeto não deve publicar ou afirmar cobertura de qualquer competência antes de obter o arquivo, verificar HTTP/TLS, conteúdo e hashes. O pacote `flightsbr` é alternativa técnica para testar descoberta e download; não é fonte estatística independente, pois consulta a ANAC.

Referências públicas:
- ANAC RIMA metadados: https://www.gov.br/anac/pt-br/acesso-a-informacao/dados-abertos/areas-de-atuacao/operador-aeroportuario/dados-de-movimentacao-aeroportuaria/metadados-operador-aeroportuario-dados-de-movimentacao-aeroportuaria
- ANAC índice de dados: https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/operador-aeroportuario/dados-de-movimentacao-aeroportuaria/
- Ipea flightsbr código: https://github.com/ipea/flightsbr/blob/main/R/utils_airport_movement.R
- Ipea documentação do leitor: https://rdrr.io/cran/flightsbr/man/read_airport_movements.html

## Distinções estatísticas e restrição temporal

- ANAC/RIMA: movimentação declarada pelos operadores aeroportuários; meses com **defasagem institucional de 6 meses**. Não é indicador tempestivo para monitoramento do mês anterior.
- ANAC Dados Estatísticos Transporte Aéreo: registros de transportadoras por trecho/etapa, outra população. Não usar como substituição automática do RIMA.
- Concessionária Viracopos RMA: boletins próprios de movimentação operacional. No projeto atual, jan/2025–ago/2026, mais atuais que o RIMA potencial. Sem separar importação e exportação.
- Comex/MDIC: operação aduaneira, kg líquidos e FOB. Distinto de peso operado em aeronaves ou terminal.

## Roteiro de resolução com portões de qualidade

1. Testar **fora deste ambiente restrito** uma única competência histórica fechada, primeiro com HTTPS/TLS rigoroso e HTTP de resultado documentado; usar caminho de arquivo sustentado pelo `flightsbr`.
2. Se o servidor oficial continuar falhando, reproduzir com `flightsbr::read_airport_movements(date=202401)` em ambiente R conectado; registrar logs e erro sem desabilitar certificados, e avaliar solicitação à GEIC/ANAC (`geic@anac.gov.br`).
3. Guardar apenas recibos e amostras de esquema apropriadas em desenvolvimento: URL final, horário UTC, SHA-256, tamanho, cabeçalho, separador, codificação e categorias. Não redistribuir microdados sem conferir a licença e as condições de uso.
4. Adaptar `processar_anac_rima.py` ao **CSV real**, especialmente nomenclatura/valores das colunas, categorias, sentinelas de ausência e regras de competência. Testar meses diferentes e revisões.
5. Comparar SBKP por natureza e pouso/decolagem com RMA, expressando divergências e impossibilidade de equiparar conceitos; preservar as séries separadas.
6. Integrar somente após validação no CI com rastreabilidade. Sem misturar com `data/viracopos.csv` ou publicar números não validados.

## Estado formal

**Causa do bloqueio principal:** dados reais RIMA ainda **não acessados nem validados** pelo nosso pipeline. Um redirecionamento e bloqueio de acesso automatizado foram observados, mas nenhum teste confirma indisponibilidade global da ANAC. **Não** marcar a Etapa 4 concluída. O PR permanece em rascunho.
