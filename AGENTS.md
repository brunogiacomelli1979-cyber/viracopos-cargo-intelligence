# Viracopos Cargo Intelligence — regras permanentes

## Objetivo
Observatório independente de carga aérea de SBKP, comércio exterior e contexto econômico. Hospedagem estática no GitHub Pages; Python para coleta e consolidação. Sem vínculo institucional com aeroporto ou órgãos públicos.

## Estrutura
- `index.template.html`: fonte da interface; marcador único `{{DASHBOARD_JSON}}`.
- `index.html`, `data/dashboard.json`: saídas geradas, não editar à mão.
- `index_blue.html`: URL compatível encaminhada à principal.
- `assets/*-blue.*`: identidade e comportamento aprovados; SVGs locais de apoio.
- `data/*.csv`, `data/fontes.json`: séries e proveniência.
- `scripts/`: coleta, validação e preparação de `_site/`.
- `tests/`: contratos, agregações, fallback e filtros.
- `docs/`: auditoria, fontes, método, indicadores, backlog e arquivo original.
- `.github/workflows/`: atualização mensal e publicação validada.

## Identidade aprovada
Em 27/10/2026 o proprietário solicitou explicitamente uma interface profissional, clean e moderna usando a skill Sites. A versão 2 usa fundo claro, superfícies brancas, azul-marinho institucional e amarelo discreto; título compacto e indicadores na primeira tela, sem hero fotográfico. Cabeçalho fixo com navegação horizontal por áreas; lateral auxiliar de escopo e cobertura no desktop. Preservar a leitura direta dos dados, espaços, foco acessível e responsividade. Não voltar ao layout de grandes blocos promocionais sem solicitação. Alterações visuais amplas futuras exigem solicitação do proprietário.

## Código
HTML semântico, CSS responsivo, JavaScript puro e Python >=3.11. pypdf 6.10.0 é a dependência para os relatórios oficiais; usar requirements.txt no Actions. Não introduzir frameworks, servidores ou bancos sem necessidade. Português na interface/documentação. Datas `AAAA-MM`, ponto decimal, sem separador de milhar. Escapar JSON incorporado e usar `textContent` para dados externos. Nunca adicionar credenciais, tokens, dados internos ou `.env`.

## Integridade
Nunca inventar observações. Ausência é `null` (macro) ou linha ausente, nunca zero. Rejeitar chaves duplicadas, NaN, infinito, meses abertos/futuros e negativos incompatíveis. IPCA negativo é válido. Separar carga física, kg líquidos e FOB; não tratar URF como movimento físico nem correlação como causalidade. Exigir fonte, competência, coleta/conferência, unidade, periodicidade, abrangência, tratamento e limitações. Não importar Comex sem validar URF, transporte e classificação setorial. Documentar revisões em commits.

## Atualização
Consultar meses encerrados. BCB revisa12 meses por indicador; MDIC reprocessa o ano do último mês encerrado e preserva outros anos; revisões de anos anteriores requerem backfill explícito. Comex substitui grupos mês×fluxo inteiros, inclusive removendo setores antigos. RMA escolhe o boletim anual mais completo. A fonte operacional atual é a concessionária, não ANAC; internacional/doméstica/courier não têm sentidos de embarque/desembarque. Courier não é automaticamente somado. Preservar recibos de anos anteriores. Falha não apaga histórico; registrar fonte, erros e competência. Validar CSV, JSON e HTML antes de versionar e publicar o SHA validado. Cron dia 13 às 10:17 UTC, configurável em `atualizar.yml`; mudanças em coletores também validam coleta real. Não declarar automação operacional sem execução real no Actions. Dados de pesquisa/staging e microdados grandes não entram no Git nem no site.

## Verificação
```
python scripts/validar_dados.py
python -m unittest discover -s tests -v
node --test tests/dashboard.test.cjs
node --check assets/app-blue.js
python scripts/preparar_site.py
```
Após alterar template, dados ou assets, regenerar com `python scripts/atualizar.py --offline`; o HTML recebe hashes de versão de CSS/JS. Não usar offline para alegar coleta nova. Verificar filtros, lacunas, zero observado, menu/teclado, navegação ativa e valores dos gráficos. Registrar limitações de QA. Nunca alterar `docs/archive/initial/`; conferir manifesto SHA-256. Preservar histórico Git, sem force push. Antes de mudar Pages existente, inspecionar configuração e domínio.
