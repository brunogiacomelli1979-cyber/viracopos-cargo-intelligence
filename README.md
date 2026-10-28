# VCP Insights · Viracopos Cargo Intelligence

Observatório independente de movimentação de carga, comércio exterior e economia. **[Abrir o painel](https://brunogiacomelli1979-cyber.github.io/viracopos-cargo-intelligence/)** · [Execuções e atualização](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions)

## Recorte histórico de pesquisa
**A partir de 01/01/2020** é o marco inicial planejado para estudos e consolidação histórica. **Não** representa cobertura atual de todas as bases: o painel segue usando apenas as competências oficiais confirmadas por fonte. Veja [Política do recorte temporal](docs/RECORTE_TEMPORAL_2020.md). A ANAC/RIMA permanece isolada em PR de desenvolvimento, sem publicação no painel, até encerrar a [Issue #8](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/issues/8).

## Versão 2

Interface profissional com fundo claro, azul-marinho e amarelo, indicadores na primeira tela e navegação por áreas. Filtros de competência e janela são preservados ao trocar de seção. Gráficos permitem apontar ou usar as setas do teclado; tabelas expansíveis oferecem os valores exatos apresentados. A lateral desktop mostra a cobertura de cada base. O projeto não possui vínculo ou endosso do aeroporto ou dos órgãos citados.

## Dados reais incorporados em 27/10/2026

| Base | Cobertura | Fonte e recorte |
|---|---|---|
| Carga de Viracopos | 20 meses: jan/2025–ago/2026 | RMA oficial da concessionária; carga internacional, doméstica e courier separado |
| Comex de Viracopos | 21 meses: jan/2025–set/2026; 3.792 registros | Microdados MDIC, URF **0817700** e via **04 aérea**, importações/exportações por capítulo SH2 |
| Comércio nacional | 21 meses: jan/2025–set/2026 | Soma nacional dos mesmos microdados, sem filtro de URF/via; conferida contra a publicação consolidada |
| Economia | 57 meses: jan/2022–set/2026 | BCB/SGS: Selic, dólar de venda médio e IPCA |

**A fonte de carga é o RMA da concessionária, não ANAC.** O relatório publica internacional como importações + exportações, sem separar embarque e desembarque. Courier permanece separado e não é automaticamente somado ao internacional. O antigo CSV vazio foi substituído por um contrato fiel a essa fonte.

Carga operacional, peso líquido aduaneiro e valor FOB não são equivalentes. A competência inicial do painel é a mais recente compartilhada entre as bases disponíveis: agosto/2026 na carga inicial. Cada indicador mantém sua referência explícita. Não há dados simulados nem interpolação para meses não publicados.

Proveniência, unidades, tratamentos, limitações, URLs consultadas e hashes em [`data/fontes.json`](data/fontes.json). Consulte [fontes](docs/fontes.md), [indicadores](docs/indicadores.md), [método](docs/metodologia.md) e [evolução v2](docs/evolucao-v2.md).

## Executar

Python >=3.11, Node >=22 para testes e curl com TLS validado. `pypdf` extrai os relatórios oficiais. O front-end continua HTML/CSS/JavaScript puro, compatível com GitHub Pages e abertura direta do HTML.

```sh
python -m pip install -r requirements.txt
# Recompilar os CSVs existentes, sem acessar fontes:
python scripts/atualizar.py --offline
# Coletar SGS, MDIC e RMA, com fallback independente:
python scripts/atualizar.py
# Verificar e preparar os arquivos públicos:
python scripts/validar_dados.py
python -m unittest discover -s tests -v
node --test tests/dashboard.test.cjs
node --check assets/app-blue.js
python scripts/preparar_site.py
python -m http.server 8000 --directory _site
```

Edite `index.template.html`, assets ou dados e regenere. `index.html`/`dashboard.json` são saídas; CSS/JS recebem hashes na URL para evitar cache de versões anteriores. `_site/` contém somente os arquivos públicos necessários. `data/staging/` é ignorada pelo Git e excluída da publicação: não redistribuímos os grandes microdados anuais nem PDFs intermediários.

## Atualização mensal

`atualizar.yml`: dia **13 às 10:17 UTC / 07:17 de Brasília**, configurável; execução manual disponível. Mudanças nos coletores ou dependências também executam a coleta para validar o fluxo alterado.

1. BCB: reconsulta sobreposta de 12 meses por indicador.
2. MDIC: lê os arquivos EXP/IMP do ano do último mês encerrado em streaming, valida tabelas URF/via/SH2 e substitui integralmente os grupos mês×fluxo revisados. Preserva anos anteriores; revisões históricas mais antigas exigem backfill explícito.
3. Brasil: consolida todas as linhas dos mesmos arquivos. Se o acesso aos microdados falhar, tenta a tabela mensal oficial com arredondamento documentado.
4. RMA: descobre boletins anuais no índice oficial, seleciona a versão mais completa de cada ano, extrai e reconcilia colunas e totais.
5. Valida CSVs, metadados, JSON e HTML; executa testes, versiona somente os dados validados e publica o SHA validado.

Falha de fonte preserva seu histórico e registra erro/competência. Recibos de anos anteriores são preservados. A atualização não pressupõe que o último mês já tenha sido publicado. Logs ficam no Actions e no artefato `log-coleta` por 30 dias. A execução manual verificada da v1 está registrada na auditoria; a v2 amplia as fontes. O primeiro disparo agendado está previsto para 13/11/2026 e ainda não ocorreu.

## Preservação e evolução

O pacote original está em `docs/archive/initial/`, com manifesto SHA-256 protegido por `.gitattributes`; a interface v1 permanece recuperável pelo histórico Git. `index_blue.html` mantém a URL antiga por redirecionamento.

Regras permanentes: [`AGENTS.md`](AGENTS.md). Próximos passos: aprofundar a base ANAC com seu recorte próprio, ampliar séries históricas, testar revisões anteriores ao ano corrente e evoluir a análise com validação temporal. Não há previsões definitivas nesta versão. [Backlog](docs/backlog.md).


## Ampliação controlada da série RMA (backfill)

A atualização automática mantém por padrão os boletins a partir de 2025, evitando releituras desnecessárias. Para tentar incorporar boletins anteriores, executar em um ambiente Python configurado:

```sh
python scripts/atualizar.py --rma-start-year 2021
python scripts/validar_dados.py
python -m unittest discover -s tests -v
```

O parâmetro controla somente o ano inicial da busca de PDFs RMA. **Não garante** que a concessionária tenha publicado ou mantenha acessíveis os relatórios mais antigos. A coleta respeita TLS, não preenche lacunas e preserva dados anteriores quando uma fonte falha. A flag é de execução manual; o cron não muda. Antes de versionar uma ampliação, conferir metadados, competências e total de controles publicados.
