# Método · v2

## Populações distintas

A série operacional vem dos Resumos de Movimentação Aeroportuária (RMA) publicados pela concessionária de Viracopos. O recorte internacional soma importações e exportações e não tem sentidos separados. Courier é mantido em campo próprio. Essa fonte não deve ser rotulada como ANAC.

O Comex usa URF 0817700 e via 04 aérea, conferidas nas tabelas oficiais. Soma valor FOB e kg líquidos por mês, fluxo e capítulo SH2. Não equivale à população operacional do RMA. FOB não é receita aeroportuária; kg líquidos não são peso bruto, volumétrico ou armazenagem.

Brasil agrega todas as linhas dos arquivos anuais oficiais, sem os filtros de Viracopos. Os13 meses coincidentes foram reconciliados com a tabela nacional consolidada, com tolerância de US$ 51 mil por arredondamento de publicação. Os arquivos brutos oferecem valores em dólares inteiros; o painel converte para bilhões. A tabela consolidada é fallback, com precisão de US$ 0,1 milhão documentada.

## Pipeline e revisão

1. Ler CSVs e metadados com contratos estritos; rejeitar números inválidos, duplicatas e meses abertos/futuros.
2. Consultar SGS por série, revisando12 meses anteriores à última observação. Agregar Selic pelo último registro, dólar por média diária publicada, IPCA por variação mensal.
3. Ler EXP/IMP do ano do último mês encerrado por streaming; hashes cobrem o conteúdo integral, mas microdados anuais não são armazenados no repositório. Validar URF, via e descrição SH2 nas tabelas oficiais. Uma revisão substitui todo o grupo mês×fluxo para retirar setores que desapareceram; manter histórico de outros anos.
4. Somar o total nacional dos mesmos arquivos. Na falha desse acesso, tentar a tabela consolidada e registrar a mudança de precisão.
5. Descobrir PDFs RMA no índice da concessionária. Entre boletins de um mesmo ano, selecionar a maior competência/quantidade de meses. Extrair página 1 com pypdf, exigir cabeçalho, unidade, nota INT* e12 colunas. Conferir totais mensais e somas de controle; omitir meses em branco. Fonte com mudança de estrutura falha antes da publicação.
6. Cada fonte falha independentemente, preservando seu último histórico validado. Guardar recibos de anos anteriores e registrar tentativas/erros. Nunca desativar verificação TLS; curl nativo é uma alternativa de cadeia de certificados validada, não modo inseguro.
7. Validar tudo antes de substituir saídas. Cada arquivo é trocado atomicamente; não existe transação única entre arquivos. Em interrupção, reexecutar; a validação impede deploy de CSV/JSON/HTML divergentes.
8. Gerar HTML com dados incorporados e hashes de assets. Executar testes antes do commit e publicar o SHA validado. Offline só recompila e conserva os recibos, sem alegar coleta nova.

## Consulta

A janela é de meses do calendário, encerrada na competência selecionada. A abertura usa a competência mais recente compartilhada entre as bases; se não houver interseção completa, prioriza os indicadores de Viracopos. KPIs usam a última observação na janela, com referência própria. As áreas preservam filtros e permitem consulta sem rolagem longa.

Nenhuma relação observada estabelece causalidade. Previsões exigem séries comparáveis, análise de quebras e validação fora da amostra; não são produzidas nesta versão.
