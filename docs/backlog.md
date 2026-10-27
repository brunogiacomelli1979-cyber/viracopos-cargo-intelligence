# Backlog incremental

## Fase A · dados e operação
1. **ANAC / SBKP**: selecionar base e dicionário; confirmar natureza, carga/correio, sentidos e unidade. Aceite: histórico mensal rastreável e reconciliado com total oficial; cobertura e duplicatas testadas.
2. **Comex / URF**: confirmar URF, via aérea e classificação NCM/SH. Aceite: recorte reproduzível, setores reconciliados com total, kg líquidos e FOB separados de carga ANAC.
3. **Brasil histórico**: importar série consolidada e implementar coleta, documentando substituição dos valores arredondados. Aceite: competências únicas e reconciliação MDIC.
4. **BCB**: retentativas limitadas, respostas brutas, backfill por intervalo e atraso por indicador. Aceite: revisões rastreáveis, histórico preservado e coleta Selic/IPCA confirmada.
5. **Automação**: confirmar coleta, testes, commit e deploy reais; acompanhar primeiro cron. Aceite: URL responde, SHA corresponde ao validado e falhas parciais visíveis.
6. **Web**: ampliar testes visuais e de acessibilidade; manter identidade aprovada. Avaliar hospedagem local de fonte/foto após licença e tamanho.

## Fase B · mercado
7. MoM, YoY e acumulados com cobertura mínima e denominadores explícitos.
8. Sazonalidade, composição setorial, NCM e países com classificação estável.
9. Relações macro/carga e Comex/carga com populações e competências compatíveis; documentar defasagens, sem inferência causal automática.

## Fase C · previsão
10. Consolidar 3–5 anos comparáveis; avaliar faltantes e quebras.
11. Baselines ingênuo/sazonal; separar treino, validação e teste temporalmente sem vazamento.
12. Comparar erros por horizonte e publicar cenários, incertezas e limites. Não produzir previsão definitiva nesta etapa.

Próxima tarefa: integrar e reconciliar a série ANAC de SBKP, indicador central ainda ausente.
