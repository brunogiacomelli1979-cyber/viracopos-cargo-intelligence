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
Preservar azul-escuro, branco, amarelo, tipografia, cabeçalho fixo, navegação horizontal e lateral no desktop. Não redesenhar por preferência. Alterações visuais amplas exigem solicitação do proprietário. Correções funcionais e de acessibilidade devem ser incrementais; verificar desktop, tablet e celular.

## Código
HTML semântico, CSS responsivo, JavaScript puro e Python >=3.11 com biblioteca padrão. Não introduzir frameworks, servidores ou bancos sem necessidade. Português na interface/documentação. Datas `AAAA-MM`, ponto decimal, sem separador de milhar. Escapar JSON incorporado e usar `textContent` para dados externos. Nunca adicionar credenciais, tokens, dados internos ou `.env`.

## Integridade
Nunca inventar observações. Ausência é `null` (macro) ou linha ausente, nunca zero. Rejeitar chaves duplicadas, NaN, infinito, meses abertos/futuros e negativos incompatíveis. IPCA negativo é válido. Separar carga física, kg líquidos e FOB; não tratar URF como movimento físico nem correlação como causalidade. Exigir fonte, competência, coleta/conferência, unidade, periodicidade, abrangência, tratamento e limitações. Não importar Comex sem validar URF, transporte e classificação setorial. Documentar revisões em commits.

## Atualização
Consultar meses encerrados; revisar 12 meses anteriores à última competência por indicador e preservar os demais. Falha não apaga histórico. Registrar erros e a última coleta bem-sucedida por série. Validar CSV, JSON e HTML antes de versionar; publicar o SHA validado. Cron padrão dia 13 às 10:17 UTC, configurável em `atualizar.yml`. Não declarar automação operacional sem execução real no Actions. ANAC/MDIC exigem integração e recortes validados.

## Verificação
```
python scripts/validar_dados.py
python -m unittest discover -s tests -v
node --test tests/dashboard.test.cjs
node --check assets/app-blue.js
python scripts/preparar_site.py
```
Após alterar template, dados ou assets, regenerar com `python scripts/atualizar.py --offline`; o HTML recebe hashes de versão de CSS/JS. Não usar offline para alegar coleta nova. Verificar filtros, lacunas, zero observado, menu/teclado, navegação ativa e valores dos gráficos. Registrar limitações de QA. Nunca alterar `docs/archive/initial/`; conferir manifesto SHA-256. Preservar histórico Git, sem force push. Antes de mudar Pages existente, inspecionar configuração e domínio.
