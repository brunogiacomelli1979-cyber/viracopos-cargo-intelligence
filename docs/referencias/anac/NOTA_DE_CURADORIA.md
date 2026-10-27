# Nota de curadoria — fechamento da etapa documental

**Escopo:** documentação de fontes, normativa e rastreabilidade. Nenhum tratamento de dados foi realizado nesta etapa.

## Separação entre duas populações estatísticas

1. **Etapa Básica**: trechos de voos informados por empresas aéreas. Os campos de carga paga, grátis e correio pertencem a essa família. Referências: metadados ANAC, Resolução 191/2011 e Portarias 3506/2019, 3507/2019 e 3902/2019.
2. **Movimentação Aeroportuária**: informações reportadas pelos operadores aeroportuários. Referências: metadados da movimentação, Resolução 464/2018 e Portaria 1017/2018. Não converter automaticamente uma série na outra.
3. **Concessionária Viracopos**: boletins operacionais RMA e relatórios próprios. A página de origem não foi arquivada por falha de verificação TLS; não foi desativada a validação HTTPS.
4. **Comex/MDIC**: declaração aduaneira/FOB/peso líquido não se confunde com tonelagem transportada por etapa nem com movimentação operacional do terminal.

## Controle normativo

A existência de Resolução 191/2011 ou outros documentos históricos no acervo **não prova sua vigência atual**. As páginas históricas podem citar portarias anteriores a 2019. Antes do tratamento, comparar versões consolidadas, revogações e alterações, registrar período de vigência pertinente ao ano do dado.

## Integridade, cobertura e pendências

Apenas `manifesto.json` atesta quais originais foram efetivamente baixados. `scripts/validar_acervo_anac.py` compara arquivo, tamanho, SHA-256 e assinatura antes de considerar um documento íntegro. O catálogo é recapturado no workflow e não deve ser lido como completo se houver `essenciais_pendentes`.

A referência da concessionária é **opcional neste acervo da ANAC** e permanece pendente devido ao certificado HTTPS. Não substituir o original por página de terceiros e não atribuir aos metadados ANAC significados que pertençam exclusivamente à concessionária.

## Portão para a etapa 2

- Confirmar a integridade dos originais e que todos os essenciais estão presentes.
- Conferir as diferenças conceituais entre duas fontes ANAC.
- Decidir como representar valores ausentes somente após consultar o dicionário e eventuais orientações oficiais.
- Não imputar valores nem habilitar previsões sem decisão metodológica documentada.
