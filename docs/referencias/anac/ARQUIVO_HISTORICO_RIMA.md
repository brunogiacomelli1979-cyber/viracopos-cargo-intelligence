# Arquivo histórico mensal ANAC/RIMA — proposta implementada

Implementação **isolada na branch** de desenvolvimento. Sem dados reais baixados ou publicados até confirmação de execução no Actions.

## Organização

```text
data/anac/rima/
  manifesto.json
  sbkp/
    2019/2019-01.csv.gz
    2019/2019-02.csv.gz
    ...
```

Cada CSV gzip preserva as colunas originais e **somente linhas SBKP**. Manifesto registra URL, SHA-256 do original nacional, hash do extrato, tamanho, competência, contagens e revisões. Hash do arquivo-fonte não significa que o CSV nacional inteiro tenha sido guardado.

## Operação

- **Backfill:** GitHub Actions > Arquivar histórico ANAC RIMA SBKP > Run workflow > mode `inicial`; lote inicial de até 12 meses, repetindo manualmente por janelas históricas (ex.: 2019-01 a 2019-12, depois 2020-01 a 2020-12).
- **Mensal:** execução dia 20, 12:23 UTC; verifica competências faltantes e os 12 meses finais elegíveis. O limite por padrão é **seis meses anteriores à data de execução**, como margem de publicação, não garantia de disponibilidade.
- O arquivo é salvo somente se houver CSV consistente e registros SBKP; se falhar, dados anteriores permanecem e o workflow reporta erro sem fazer commit de resultados parciais.
- Atualizações e correções são detectadas pelo SHA-256 do arquivo original. Atenção: uma revisão de um arquivo nacional pode gerar uma nova versão mesmo que SBKP não tenha mudado.
- Não há coleta de dados em tempo real nem junção automática com a concessionária. O PR permanece em rascunho até testar arquivos reais, esquema, volume e acesso no runner GitHub.
- Antes de aprovação, avaliar se a execução mensal deve acontecer na branch principal e revisar limites GitHub por arquivo/por repositório. Dados nacionais não são versionados no GitHub; apenas o extrato de SBKP.

**Condição obrigatória:** executar o fluxo manual, conferir logs, hashes, CSV extraído e cobertura antes de declarar a carga histórica concluída.
