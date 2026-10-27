# Auditoria inicial · 27/10/2026

## Inventário recebido
11 arquivos: `index_blue.html`, `README.md`, quatro assets (JS/CSS e dois SVGs) e cinco arquivos de dados (JSON/quatro CSVs). Não havia `index.html`, template, scripts, testes, workflows, dependências ou metadados de Git/remote. O README afirmava que esses componentes existiam e que a atualização mensal estava pronta, sem arquivos que sustentassem a afirmação.

Todos os arquivos recebidos foram lidos. Cópia byte a byte em `docs/archive/initial/`, com SHA-256 em `docs/archive/manifest.json`. Nenhum histórico Git anterior foi encontrado para preservar. O repositório novo foi criado após autorização expressa do proprietário: [viracopos-cargo-intelligence](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence).

## Evidências de dados
- Brasil: uma observação set/2026, exportação 34,4 e importação 26,7 US$ bilhões; conferidas no [painel oficial MDIC](https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas). São valores arredondados. Coleta original desconhecida; conferência atual registrada separadamente.
- ANAC: nenhuma observação, somente cabeçalho. Não há série operacional a auditar ou prever.
- Comex URF: nenhuma observação, somente cabeçalho; recorte ainda sem validação.
- Macro original: nenhuma observação. Primeiro teste real local: câmbio retornou 57 meses; Selic retornou resposta inválida e IPCA expirou. Nova tentativa: as três séries retornaram sucesso, 57 competências jan/2022–set/2026; câmbio atualizou 13 meses sobrepostos sem perder os anteriores. Recibos reais em `data/fontes.json`.

## Problemas e correções
| Problema | Efeito | Correção |
|---|---|---|
| Sem página principal | Raiz não entregava a variante aprovada | Template azul gera `index.html`; URL azul antiga encaminha para a principal |
| Filtro por quantidade de registros | 12 observações podiam cobrir vários anos | Janela de calendário e competência final; KPIs, gráficos e setores sincronizados |
| Comex inicializado em zero para os dois fluxos | Ausência parecia atividade observada nula | Fluxo ausente é `null`; zero observado permanece zero |
| Meses ausentes ligados por linha | Falsa continuidade | Lacunas mensais explícitas e quebra de segmentos |
| Eixo macro arredondado para inteiros | Vários rótulos idênticos no câmbio | Duas casas decimais |
| Tooltip SVG apenas com ponteiro | Valores difíceis de consultar com teclado | Tabelas expansíveis e área do gráfico com foco/rolagem |
| Menu antes das ferramentas no celular | Ordem de leitura e posicionamento inconsistentes | Menu após ferramentas; estado acessível, Escape e fechamento ao navegar |
| Seção ativa dependia só do último callback do observer | Podia ficar desatualizada em seções altas | Posição de todas as seções, atualizada com requestAnimationFrame; aria-current |
| Dois deslocamentos de âncora se somavam | Título ficava distante do cabeçalho e seção anterior permanecia ativa | Um único deslocamento responsivo; atalho ao topo com rolagem explícita |
| Cache manteve CSS antigo após deploy | Navegador podia usar correções de versões diferentes | URLs de CSS/JS com versão SHA-256, conferidas pelo validador |
| Sem contratos/proveniência | CSV malformado ou duplicado poderia publicar | Validação de datas, chaves, números, metadados e igualdade CSV/JSON/HTML |
| Automação somente descrita | Estado operacional incorreto | Scripts e Actions implementados, com fallback por série e deploy após checks |

## Verificações locais
11 testes Python: arquivo original, contratos, chaves, negativos/NaN/infinito, mês aberto, agregações, deflação, falha total/parcial, revisão histórica, compilação offline e consistência de HTML/dados. Quatro regressões JavaScript: calendário, competência final, fluxo ausente/zero e soma/unidades Comex. `node --check` para sintaxe. Preparação de `_site` e HTTP local 200.

Navegador Chrome: desktop, celular 390×844 e tablet 768×1024; sem transbordamento horizontal da página nos tamanhos verificados. Menu móvel e Escape, seleção histórica, 24 pontos mensais, indisponibilidade do Brasil fora da competência, tabela de valores e gráfico real de câmbio conferidos. Identidade azul preservada. A renderização cheia de ANAC/Comex ainda não pode ser verificada com dados reais, pois essas séries não existem no pacote; cálculos de agregação possuem testes isolados identificados como fixtures, nunca publicados como observações.

## Publicação e automação
Configuração Pages inspecionada no repositório novo: desativada, sem branch de origem e sem site anterior. Fonte alterada para GitHub Actions; sem domínio personalizado. `pages.yml` publica somente `_site`, excluindo o protótipo arquivado e ferramentas de desenvolvimento. `atualizar.yml` usa cron mensal configurável, valida antes de fazer commit e chama workflow reutilizável com SHA explícito, evitando depender de gatilho por push do bot.

Evidências remotas verificadas:
- [Publicação do snapshot validado](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40523025672): validação e deploy concluídos com sucesso.
- [Primeiro ciclo completo de atualização](https://github.com/brunogiacomelli1979-cyber/viracopos-cargo-intelligence/actions/runs/40523186877): `workflow_dispatch`, sucesso em 46 segundos; coleta SGS 432, 1 e 433 com 13 meses cada; histórico de 57 competências preservado; 11 testes Python e quatro JavaScript; commit automático `fcd101b`; jobs update, publish/validate e publish/deploy concluídos com sucesso. Logs e artefato de coleta disponíveis nessa execução.
- [Site público](https://brunogiacomelli1979-cyber.github.io/viracopos-cargo-intelligence/) aberto e inspecionado no Chrome.

O primeiro ensaio Actions falhou no teste de arquivo original devido a caminhos Windows no manifesto. Separadores normalizados para `/` e `.gitattributes` protege os bytes arquivados; a execução seguinte confirmou hashes no Linux e os demais checks. Nenhum deploy ocorreu na tentativa inválida.

Fluxo mensal validado por disparo manual; primeiro cron previsto para 13/11/2026 às 07:17 em Brasília, ainda não observado. ANAC, Comex e Brasil ainda não têm coleta automática. O runner reportou avisos de Actions com runtime legado executadas pelo GitHub em Node 24 e migração de ubuntu-latest; não impediram os jobs, mas a atualização das majors deve entrar na manutenção.

## Pendências e próximo passo
Integração ANAC/SBKP e validação Comex, histórico Brasil, coleta bruta/retries/backfill SGS e indicadores derivados. Plano e critérios em `docs/backlog.md`. Próxima tarefa recomendada: integrar e reconciliar a carga internacional de SBKP com fonte ANAC.
