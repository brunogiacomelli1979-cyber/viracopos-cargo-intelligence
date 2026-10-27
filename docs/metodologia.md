# Método e atualização

ANAC mede carga transportada; Comex representa recorte aduaneiro; FOB não é receita aeroportuária. Peso líquido não é peso bruto, volumétrico ou armazenagem. Dados nacionais não são atribuídos a Viracopos.

1. Ler CSVs com contratos estritos e metadados. Rejeitar duplicatas e valores inválidos antes de coletar.
2. Consultar SGS por indicador, somente meses encerrados. Primeira carga desde janeiro do ano do último mês encerrado menos quatro; posteriores revisam 12 meses anteriores à última observação do indicador.
3. Agregar Selic pelo último registro, câmbio por média dos dias publicados, IPCA pelo valor mensal. Não interpolar. A completude diária dentro do mês depende da resposta da API.
4. Mesclar por chave sem apagar células históricas ausentes na resposta. Rejeitar duplicatas diárias e respostas inválidas antes da mesclagem. Falha por série preserva seu histórico e recibo anterior.
5. Validar tudo e substituir cada saída atomicamente. Não há transação única entre os arquivos: em interrupções, executar novamente. A validação detecta divergências e impede deploy.
6. Gerar JSON e HTML com os mesmos dados; escapar `<` no JSON incorporado. Validar igualdade CSV ↔ JSON ↔ HTML e metadados.
7. No Actions, testar, versionar e publicar o SHA validado. Cron não garante publicação recente da fonte; mostrar competências e erros.

Offline recompila sem coleta nova. Logs distinguem tentativa, sucesso, competência e compilação. Revisões anteriores à janela sobreposta exigem backfill explícito, ainda no backlog.

**Consulta:** competência final compartilhada, janela em meses do calendário. KPI usa última observação na janela com referência própria. Setores usam a última competência do fluxo dentro da janela. Sem dados, mostrar indisponibilidade.

**Limites:** sem série operacional SBKP nem Comex validado, não atribuir relações macroeconômicas à demanda física. Sazonalidade, defasagens, causalidade e validação fora da amostra pertencem às próximas fases. Câmbio não é ponderado por valor negociado.
