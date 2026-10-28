# Backlog após a versão 2

## Entregue
- Interface moderna por áreas, filtros compartilhados, gráficos consultáveis por ponteiro/teclado e cobertura das bases.
- RMA oficial:20 competências operacionais, sem inventar sentidos; courier separado.
- MDIC:21 competências de Viracopos e Brasil; recorte URF 0817700/via 04 validado;3.792 linhas Comex por SH2.
- Coletores reproduzíveis e rotina mensal ampliada; fallback por fonte, revisão de grupos e recibos históricos.
- Testes de extração, somas, filtros, revisões, calendário, dados ausentes e preservação do histórico.

## Prioridade imediata
1. **Revisão visual em navegador**: uma permissão salva bloqueou a prévia mesmo após autorização no chat. Conferir desktop, tablet e celular quando esse acesso for liberado. Não registrar esse teste como aprovado antes da execução.
2. **Operação mensal**: acompanhar primeiro disparo por cron em 13/11/2026, 07:17 de Brasília; verificar competências por fonte, erros parciais e revisão dos arquivos anuais. A comprovação do fluxo ampliado fica nas execuções Actions.
3. **Manutenção de dependências**: atualizar majors das Actions para runtimes atuais, preservando o fluxo testado; revisar pin pypdf ao atualizar o contrato de extração.

## Deliberação temporal do projeto
- **Início do histórico-alvo: 2020-01**, conforme [política de recorte](RECORTE_TEMPORAL_2020.md). Isso não implica séries completas desde 2020; documentar lacunas por fonte.
- A indisponibilidade de janeiro/2019 na ANAC foi retirada do escopo operacional **por decisão metodológica**, não por conserto na origem.
- A Issue #8 segue bloqueando novos lotes ANAC até encerrar os demais incidentes, comprovar QA e governança. Preservar o dashboard vigente.

## Dados e análise
4. **ANAC etapa combinada**: implementar uma série própria, validar dicionário e sentidos, e reconciliar as diferenças de cobertura com o RMA. Não substituir ou juntar populações sem explicar.
5. **Backfill**: ampliar RMA/MDIC anteriores a 2025 e revisar anos passados de modo explícito, mantendo hashes e registros de alterações.
6. **Detalhamento**: países de origem/destino, SH4/NCM e via de transporte com universos e denominadores claros.
7. **Sazonalidade**: MoM, acumulado anual e padrões mensais com cobertura mínima. A variação anual atual exige mês correspondente válido.
8. **Previsão**: consolidar histórico comparável suficiente, baselines ingênuo/sazonal e validação temporal sem vazamento; publicar erros e incerteza. Nenhuma previsão definitiva nesta versão.
