# Viracopos Cargo Intelligence · VCP Insights

Observatório independente de carga aérea, comércio exterior e contexto econômico. Projeto de portfólio sem afiliação ou endosso institucional do Aeroporto de Viracopos.

**[Abrir o observatório](https://brunogiacomelli1979-cyber.github.io/viracopos-cargo-intelligence/)** · [Repositório](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence) · [Primeira atualização completa verificada](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40523186877)

A variante azul aprovada é a interface principal: **`index.html`**. Mantém azul-escuro, branco, amarelo, navegação horizontal fixa e índice lateral no desktop. `index_blue.html` encaminha à principal. O pacote recebido está preservado byte a byte em [`docs/archive/initial/`](docs/archive/initial/), com manifesto SHA-256; não integra a publicação Pages.

## Estado dos dados

| Base | Estado auditado | Tratamento |
|---|---|---|
| Brasil / MDIC | Set/2026: exportações 34,4 e importações 26,7 US$ bilhões | Conferidos no [painel oficial MDIC](https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas); arredondamento da divulgação mantido |
| SBKP / ANAC | Sem observações | Integração pendente, sem volumes simulados |
| Comex / URF | Sem observações | Validar URF, transporte e agrupamento antes de coletar |
| Macro / BCB | Coletor SGS 432, 1 e 433 implementado | Disponibilidade por série em `data/fontes.json` e `data/dashboard.json`; falhas preservam histórico |

A primeira coleta local em 27/10/2026 obteve câmbio com falhas de Selic/IPCA; a segunda coletou as **três séries com sucesso: 57 competências (jan/2022–set/2026)**. O reprocessamento de câmbio revisou 13 meses sobrepostos sem apagar o histórico. O teste local não comprova o agendamento no GitHub; consulte os metadados atuais e a [auditoria](docs/auditoria.md).

## Executar e atualizar

Python >=3.11; Node >=22 para testes. Nenhum pacote externo precisa ser instalado. O site funciona por duplo clique, com o mesmo snapshot do JSON incorporado.

```sh
python scripts/atualizar.py --offline
# Coletar BCB pela internet:
python scripts/atualizar.py
# Verificações:
python scripts/validar_dados.py
python -m unittest discover -s tests -v
node --test tests/dashboard.test.cjs
node --check assets/app-blue.js
# Montar somente arquivos publicáveis e servir prévia:
python scripts/preparar_site.py
python -m http.server 8000 --directory _site
```

Abra `http://localhost:8000`. Fontes web e foto remota são opcionais; há fontes de sistema e ilustração SVG local. O modo offline apenas recompila, sem coletar dados novos.

## Consulta histórica

**ATÉ** define a competência final; **JANELA** limita meses do calendário. KPIs, gráficos e setores seguem esse período e mostram suas próprias competências. Lacunas não são interpoladas; fluxo Comex ausente não vira zero. Pontos SVG têm valores ao passar o cursor, com tabelas expansíveis para teclado/leitores de tela. Há link para pular ao conteúdo, foco visível, menu móvel com Escape e navegação ativa.

## Estrutura e edição

```
index.html                  # saída gerada
index.template.html         # editar interface aqui
index_blue.html             # URL antiga compatível
assets/                     # CSS, JS e SVGs aprovados
data/                       # CSVs, fontes.json e dashboard.json
scripts/                    # atualizar, validar e preparar_site
tests/                      # contratos Python e regressões JavaScript
docs/                       # auditoria, método, fontes e backlog
.github/workflows/           # atualizar.yml e pages.yml
AGENTS.md                   # regras permanentes
requirements.txt            # somente biblioteca padrão
```

Edite CSVs/metadados e regenere. Não edite as saídas à mão. CSVs têm cabeçalho estrito; ausência macro é célula vazia e demais conjuntos omitem meses sem dados. Números usam ponto decimal sem separador de milhar. Chave Comex: mês × fluxo × setor; demais: mensal. Novas importações exigem fonte, coleta/conferência documentada, recorte e unidade. Veja [indicadores](docs/indicadores.md) e [metodologia](docs/metodologia.md).

## Publicação e rotina mensal

`pages.yml` valida o snapshot, executa testes e publica somente `_site/`. Pull requests passam pelos checks sem publicar. `atualizar.yml` coleta BCB, testa, versiona as saídas e chama a publicação com o SHA validado. Assim não depende de um push do `GITHUB_TOKEN` para disparar outra Action.

Agenda: **dia 13, 10:17 UTC / 07:17 em Brasília**, configurável no cron. Fontes podem atrasar; executar manualmente quando necessário. Reconsulta 12 meses anteriores à última competência por indicador, preservando o restante. Primeira carga desde janeiro do ano correspondente a quatro anos antes do último mês encerrado. Logs ficam na execução e no artefato `log-coleta` por 30 dias.

Em 27/10/2026, o ciclo real disparado manualmente no Actions concluiu **coleta das três séries, 15 testes, commit automático `fcd101b` e publicação**. O primeiro disparo por cron está previsto para 13/11/2026 e ainda não ocorreu. A rotina automática cobre BCB; ANAC, Comex e Brasil permanecem sem coletor automático.

Configuração de um repositório novo, depois do envio:

1. **Settings → Pages → GitHub Actions**; verificar antes configuração existente/domínio.
2. Executar **Validar e publicar Pages** para o snapshot atual.
3. Executar **Atualizar indicadores mensais**, conferindo coleta, testes, commit e deploy.
4. Considerar automação operacional apenas após execução real; conferir também cada fonte, pois fallback é permitido.

Referência: [workflow oficial Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages). Site e repositório públicos: não incluir dados internos ou segredos.

## Fontes e evolução

Fontes primárias em [`docs/fontes.md`](docs/fontes.md), proveniência estruturada em `data/fontes.json`. Toneladas de carga física, FOB e kg líquidos medem fenômenos diferentes. Brasil inclui outras vias e aeroportos. Não tratar correlação como causalidade nem prever demanda sem histórico suficiente e validação temporal.

Fotografia remota de Mike Peel, [Wikimedia Commons / CC BY-SA 4.0](https://commons.wikimedia.org/wiki/File:Viracopos-Campinas_International_Airport_2017_003.jpg), atribuída na interface quando carregada. Não é redistribuída; `assets/terminal-art.svg` é o fallback do protótipo. Não reproduzimos marca/logotipo oficial.

Próximas fases e critérios de aceite em [`docs/backlog.md`](docs/backlog.md).
