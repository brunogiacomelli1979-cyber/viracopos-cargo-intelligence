# Evolução 2 · dados e interface

Solicitação do proprietário em 27/10/2026: corrigir bases vazias e adotar aparência profissional, clean e moderna com a skill Sites. A autorização amplia a revisão visual anterior. O destino existente permanece GitHub Pages, preservando repositório e histórico; não foi criado outro site com audiência diferente.

## Interface implementada
- Título compacto, filtros e quatro indicadores na abertura, sem hero fotográfico.
- Fundo claro, superfícies brancas, azul-marinho e amarelo discreto.
- Navegação por áreas que preserva competência/janela sem percorrer uma página longa.
- Lateral desktop com escopo aeroportuário, intervalos de cobertura e download da base.
- Gráficos SVG com leitura ao apontar, setas por teclado, linhas distintas e tabelas de valores.
- Visões dedicadas de carga, Comex nacional/URF, economia, composição setorial e fontes.
- Competência inicial compartilhada entre as bases; se não houver interseção completa, priorizar as séries do aeroporto. Não selecionar automaticamente um mês que só possua contexto nacional.

## Dados nacionais
Coletor `scripts/coletar_brasil.py`: tabela Totais > Mensal da publicação consolidada MDIC, conversão de US$ milhões para bilhões. Reconciliação de exportação + importação com corrente e de exportação − importação com saldo; tolerância de US$ 0,2 milhão pelo arredondamento da tabela. Primeira coleta contém 13 competências, set/2025 a set/2026; substitui o único mês arredondado do protótipo. A mesclagem mantém competências anteriores.

O cliente HTTPS conserva verificação de certificado e nome do host; quando a cadeia OpenSSL falha, pode consultar o mesmo endereço com o curl nativo e suas verificações padrão. Não é utilizado modo inseguro. Respostas e recibos mantêm fonte, instante e SHA-256.

## Verificação
Os contratos, agregações, seleção de competência e consistência CSV/JSON/HTML são testados. Dados de pesquisa e microdados não entram no artefato público: a preparação do site inclui somente os seis arquivos de dados explicitamente previstos.

Revisão visual v2 pendente no ambiente: a abertura de `http://127.0.0.1:8081` foi negada primeiro pela revisão automática de permissões e, após autorização expressa do usuário, por uma configuração de permissão salva. Não houve tentativa por outro navegador, proxy, captura indireta ou remoção de proteções. Essa limitação não deve ser descrita como teste visual aprovado.

## Cobertura integrada

Carga RMA:20 meses jan/2025–ago/2026, com internacional/doméstica/courier separados; controles dos PDFs conferidos também por renderização da página de origem. Comex:21 meses jan/2025–set/2026, 3.792 registros por mês×fluxo×SH2, URF 0817700 e via 04. Brasil:21 meses dos mesmos microdados, sem filtro URF/via, reconciliados contra13 meses da publicação consolidada. Macro:57 meses jan/2022–set/2026.

Coletores reproduzíveis: `coletar_carga_vcp.py`, `coletar_comex.py`, `coletar_brasil.py` (fallback), utilitário `fontes_http.py`. Dependência pypdf 6.10.0 para PDF. Os CSVs, fontes.json e snapshot contêm dados reais; staging fica fora do Git e do artefato público. Há 25 testes Python e 7 regressões JavaScript, incluindo alteração de colunas RMA, courier separado, filtros URF/via, revisão de setores removidos, recibos antigos, falha total das fontes sem perda de dados e os quatro indicadores principais preenchidos na competência inicial.

As execuções verificadas de coleta, testes e publicação são consultáveis na aba Actions do repositório. A limitação de revisão visual do novo site descrita acima permanece; não se confunde com a conferência visual dos PDFs de origem, que foi realizada.
