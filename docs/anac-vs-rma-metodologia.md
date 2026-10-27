# Contrato ANAC × concessionária — SBKP

## Pergunta
Recuperar as 60 competências janeiro/2020–dezembro/2024 de transporte físico
reportado à ANAC, separando internacional/doméstico, embarque/desembarque e
carga paga/grátis/correio. Não inferir séries operacionais RMA desses registros.

## Fonte e linhagem
Microdados **Etapa Básica** ANAC, arquivos mensais `basicaAAAA-MM.zip`, 
portal governamental (confirmar endereço e disponibilidade em cada recibo).
Fonte primária de definição:
https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/voos-e-operacoes-aereas/dados-estatisticos-do-transporte-aereo/48-dados-estatisticos-do-transporte-aereo
O aeroporto é identificado por ICAO **SBKP**, não apenas nome textual.

## Métodos
- Registrar toda etapa cuja origem ou destino seja SBKP.
- Embarque = origem SBKP; desembarque = destino SBKP.
- Natureza = doméstica ou internacional conforme classificação publicada pela ANAC.
- Toneladas de carga sem correio = (kg_carga_paga + kg_carga_gratis)/1.000.
- Correio (kg_correio)/1.000 é separado. Não somar automaticamente ao RMA.
- Colunas de peso vazias bloqueiam a consolidação do mês até investigar se
  ausência significa não informado ou zero documentado.
- Não duplicar linhas por escalas; a unidade é a etapa básica, não conhecimento
  de carga, alfândega, cliente, armazenagem ou volume desembaraçado.
- Baixar apenas ZIP oficial, guardar URL, horário de consulta, bytes e SHA-256
  do ZIP e do CSV. Checar período e esquema de cada mês.
- Os CSVs originais não entram no site; apenas agregados validados no staging.

## Comparabilidade
RMA da concessionária: escopo de movimentação operacional do terminal, categorias
INT, DOM e courier, com possível diferença de população e regra de contagem.
ANAC Básica: transporte realizado em etapas de voo, por origem/destino.
MDIC/Comex: registros aduaneiros de URF 0817700/via 04, FOB e kg líquidos.
É esperado haver diferenças de cobertura, datas e inclusões; não calibrar
coeficientes de equivalência por simples ajuste de totais.

## Limites de validação
O coletor e testes sintéticos **não provam** que os 60 arquivos foram coletados.
Usar piloto em 2024-01 primeiro para confirmar layout, encoding, faltantes,
convenção de decimais e completude, depois expandir.
Nenhuma coluna ANAC deverá substituir automaticamente `data/viracopos.csv`;
criar série e gráficos com atribuição e rótulos separados, após auditoria.
