# Viracopos Cargo Intelligence

**Observatório independente de demanda logística, comércio exterior e indicadores econômicos.**

## Identidade visual · edição editorial v2

O website foi redesenhado inspirado na linguagem institucional de Viracopos Cargo — marinho, laranja, sinalética aeroportuária e fotografia — **sem copiar o logotipo oficial**. Navegação horizontal, faixa de dados, números grandes sem cartões genéricos, painéis com bordas finas, leitura de pesquisa por capítulos.

**Referências visuais:**
- [Viracopos Cargo — portal oficial](https://www.viracopos.com/pt_br/cargo/) — contexto aeroportuário, comunicação de serviços e identidade.
- [Identidade Viracopos — estudo de Flavio Treiger](https://www.flaviotreiger.com/viracopos) — princípio das trilhas luminosas e da marca aeroportuária.
- [SkyCargo UI — Odama / Dribbble](https://dribbble.com/shots/25678359-SkyCargo-Air-Freight-Management-Dashboard) — informação logística e hierarquia de dados.
- [Air Cargo UX/UI — Valmax](https://valmax.agency/case-studies/aircargo/) — organização de conteúdos e redução de complexidade.

**Fotografia:** a imagem de aeronave cargueira em Viracopos, captada em 2017 por **Mike Peel**, é referenciada por URL do Wikimedia Commons sob licença **CC BY-SA 4.0**, com atribuição e link para a [página de licença e crédito](https://commons.wikimedia.org/wiki/File:Viracopos-Campinas_International_Airport_2017_003.jpg). A fotografia não é redistribuída dentro do ZIP. Quando a imagem online estiver indisponível, o site exibe a ilustração autoral `assets/terminal-art.svg`. A imagem e a marca oficial da concessionária não implicam parceria ou vínculo institucional.


Painel em HTML/CSS/JavaScript puro, pronto para GitHub Pages, com atualização mensal via GitHub Actions e script Python sem pacotes externos.

## Status inicial

- **Brasil/MDIC:** valor FOB de exportações (US$ 34,4 bilhões) e importações (US$ 26,7 bilhões) referente a **setembro de 2026**, conforme [nota mensal MDIC/Secex](https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas). Valores arredondados na publicação de origem, não somatório de microdados.
- **BCB/SGS:** sincronização automática (primeira execução **on-line** no GitHub Actions) das séries: `432` (meta Selic, último registro do mês, % a.a.), `1` (taxa de câmbio dólar de venda, média aritmética dos dias disponíveis, R$/US$) e `433` (IPCA, variação mensal, %).
- **ANAC/Viracopos:** arquivo-base criado, mas **sem observações numéricas**. Falta agregar por aeroporto `SBKP`, natureza internacional e sentido embarque/desembarque, conforme metodologia escolhida.
- **MDIC/URF Viracopos:** arquivo-base criado, mas **sem observações numéricas**. O código URF e seu escopo devem ser verificados nas tabelas auxiliares do MDIC, antes do carregamento.

Nenhuma observação de Viracopos é simulada e nenhuma série é preenchida artificialmente.

## Publicar no GitHub Pages

1. Crie um repositório **público**, por exemplo `viracopos-cargo-intelligence`, com a branch padrão chamada **`main`**.
2. Extraia o ZIP, envie **todo o conteúdo da pasta**, inclusive `.github/workflows/publicar.yml`, para a raiz do repositório. No computador: `git add . && git commit -m "Dashboard inicial" && git push`.
3. No GitHub, vá em **Settings → Pages → Build and deployment → Source → GitHub Actions**.
4. Entre em **Actions → Atualizar indicadores e publicar GitHub Pages → Run workflow** (ou faça um push na branch `main`). Essa execução online tentará buscar as séries do BCB, gerar os dados e publicar.
5. Acesse o endereço indicado em **Settings → Pages → Visit site**. Um caminho usual para repositórios de projeto é `https://SEU-USUARIO.github.io/viracopos-cargo-intelligence/` (substitua o usuário; o endereço só existe após publicação).

> GitHub Pages publica as informações para qualquer visitante: **não suba dados internos, confidenciais ou de clientes**. O projeto foi desenhado para dados públicos.

## Atualização mensal

- **Automática (parcial):** dia 13 de cada mês, às 10:17 UTC, a Action consulta as três séries do BCB, valida o CSV e refaz o painel. O workflow também pode ser executado manualmente.
- **Arquivos consolidados externos (ainda manuais):** atualize os arquivos CSV de Viracopos, COMEX e Brasil com os dados oficiais publicados, respeitando o escopo e o mês de competência. Faça `git commit`/`push` para publicar imediatamente.
- **Histórico:** versões dos CSVs e do painel ficam no GitHub, permitindo comparação e eventual revisão de períodos anteriores.
- **Atualização em atraso:** quando a fonte não publicou determinado mês, o painel preserva o último dado validado. A competência de cada série permanece visível.
- **Agenda:** o cron mensal depende do funcionamento do GitHub Actions. Workflows agendados de repositórios públicos podem ser desabilitados se houver 60 dias sem atividade; verifique a aba Actions se pararem. O workflow deste projeto registra mensalmente o snapshot no Git para documentar atualizações.

### Arquivos editáveis

| Arquivo | Unidade | Granularidade | Significado |
| --- | --- | --- | --- |
| `data/brasil.csv` | US$ **bilhões**, FOB | 1 linha por mês | Exportações/importações **do Brasil**, não de Viracopos |
| `data/viracopos.csv` | toneladas | 1 linha por mês | Carga aérea internacional **embarcada** e **desembarcada** em SBKP, apurada segundo ANAC/RIMA |
| `data/comex_viracopos.csv` | US$ FOB e **kg líquidos** | 1 linha por mês × fluxo × setor | Comércio registrado no **recorte URF validado**; importação/exportação e setor |
| `data/macro.csv` | % a.a.; R$/US$; % no mês | 1 linha por mês | Séries macroeconômicas do BCB; populadas pela Action |
| `data/dashboard.json` | snapshot gerado | — | Saída automatizada; não editar manualmente |
| `index.template.html` | HTML | — | Template fonte do site, com marcador dos dados |
| `index.html` | HTML gerado | — | Página pronta para hospedar ou abrir localmente |

**Exemplo de preenchimento (não é dado real; NÃO copie como observação):**

`viracopos.csv` tem colunas `mes,embarque_internacional_t,desembarque_internacional_t`. Em `mes` use `AAAA-MM`. Um número usa ponto para casas decimais e **não** usa separador de milhar. Para registrar ausência de dados, deixe a linha do mês **fora do arquivo** — não registre zero, que significa volume observado nulo.

`comex_viracopos.csv` tem `mes,fluxo,setor,valor_fob_usd,kg_liquido`. Em `fluxo` use `importacao` ou `exportacao`; o campo `setor` deve seguir uma classificação estável e documentada (ex.: capítulos SH ou agregados do MDIC). `valor_fob_usd` está em dólares, **não em milhões**. `kg_liquido` está em quilos, **não em toneladas**. Uma linha por mês, fluxo e setor.

**Atenção às diferenças metodológicas:**

- A ANAC RIMA reporta carga transportada nas aeronaves, não necessariamente toda carga armazenada, desembaraçada ou transitada pelo recinto aeroportuário.
- O dado **URF** da Secex identifica o local de registro/controle aduaneiro no recorte da base. Não se pode dizer que todos os itens correspondam a peso fisicamente movimentado pelo terminal ou que o valor FOB seja receita aeroportuária.
- O `KG_LIQUIDO` do Comex não equivale a peso bruto, volumétrico ou capacidade operacional. Para planejar armazenagem, serão necessárias outras métricas.
- Dados do MDIC podem ser revisados retroativamente; preserve e, quando aplicável, atualize períodos anteriores. A série mensal consolidada não é um dado de “agora”.
- A correlação entre Selic, câmbio, setores e demanda não implica causalidade. A previsão exigirá série comparável, tratamento de sazonalidade e teste fora da amostra.

## Executar localmente

```bash
# Sem internet, recompila somente os CSVs já disponíveis:
python scripts/atualizar.py --offline

# Com internet, consulta as APIs do Banco Central:
python scripts/atualizar.py
```

O script reescreve `data/dashboard.json` e incorpora o mesmo conteúdo em `index.html`. Isso permite abrir `index.html` diretamente por duplo clique, inclusive sem servidor local.

## Fontes primárias

- [MDIC/Secex — dados abertos do comércio exterior](https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta).
- [Comex Stat — consultas detalhadas e tabelas auxiliares](https://comexstat.mdic.gov.br/pt/home).
- [ANAC — dados de movimentação aeroportuária/RIMA](https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/operador-aeroportuario/dados-de-movimentacao-aeroportuaria/60-dados-de-movimentacao-aeroportuaria).
- [BCB — série 432, meta Selic](https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom).
- [BCB — série 1, dólar de venda](https://dadosabertos.bcb.gov.br/dataset/1-taxa-de-cambio---livre---dolar-americano-venda---diario).
- [BCB — Portal de Dados Abertos](https://dadosabertos.bcb.gov.br/).
- [GitHub Pages — publicação com GitHub Actions](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

## Roadmap

1. Selecionar e validar o recorte aduaneiro de Viracopos no Comex Stat.
2. Montar o ETL da base ANAC RIMA por SBKP, natureza internacional, embarque/desembarque.
3. Importar 3 a 5 anos completos de séries comparáveis, com revisão de unidades e competência.
4. Criar painel setorial por SH2/SH4, origem/destino e indicadores de sazonalidade.
5. Desenvolver modelos de previsão com defasagens e validação temporal (sem fazer afirmações causais automáticas).

Projeto acadêmico/independente, sem afiliação oficial ao Aeroporto de Viracopos, à ANAC ou ao MDIC.


## Variantes visuais

- `index.html` — versão institucional clara já existente
- `index_blue.html` — nova versão com predominância de azul, detalhes em branco e amarelo, cabeçalho fixo e navegação lateral auxiliar no desktop

Arquivos adicionais da nova variante:
- `assets/style-blue.css`
- `assets/app-blue.js`
