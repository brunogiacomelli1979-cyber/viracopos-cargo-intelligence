# Documentação oficial ANAC — etapa 1 (somente coleta documental)

A primeira etapa tem como objetivo arquivar documentos oficiais e respectivos metadados **sem tratar séries de carga**. O acervo é isolado do dashboard e dos PRs de coleta ANAC.

## Núcleos documentais
1. ANAC — catálogo e definição de Dados Estatísticos do Transporte Aéreo (Etapa Básica): https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/voos-e-operacoes-aereas/dados-estatisticos-do-transporte-aereo/48-dados-estatisticos-do-transporte-aereo
2. ANAC — Resolução 191/2011: https://pergamum.anac.gov.br/arquivos/RA2011-0191.pdf
3. ANAC — Portaria 3506/SAS/2019, normativa de envio estatístico: https://www.anac.gov.br/assuntos/legislacao/legislacao-1/portarias/2019/portaria-no-3506-sas-11-11-2019
4. ANAC — Portaria 3507/SAS/2019 e alterações: https://www.anac.gov.br/assuntos/legislacao/legislacao-1/portarias/2019/portaria-no-3507-sas-11-11-2019
5. ANAC — Resolução 464/2018, movimentação aeroportuária: https://www.anac.gov.br/assuntos/legislacao/legislacao-1/resolucoes/2018/resolucao-no-464-22-02-2018
6. ANAC — Portaria 1017/SRA/SIA/2018 e alterações: https://www.anac.gov.br/assuntos/legislacao/legislacao-1/portarias/2018/portaria-no-1017-sra-sia-26-03-2018
7. ANAC — Dados de Movimentação Aeroportuária (RMA/RIMA, quando aplicável): https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/operador-aeroportuario/dados-de-movimentacao-aeroportuaria/60-dados-de-movimentacao-aeroportuaria
8. Viracopos — publicações e estatísticas da concessionária: https://www.viracopos.com/pt_br/institucional/estatisticas-e-publicacoes.htm

## Inventário e limites

- **Original arquivado:** `originais/` com documento real obtido por HTTPS validado, assinatura PDF ou HTML conferida.
- **Manifesto:** `manifesto.json` com origem, URL final, SHA-256, tamanho, data e falhas de obtenção.
- **Não localizado/baixado:** preservar status `pendente`; não fingir que o arquivo está em acervo.
- Referências de 2011 devem ser lidas juntamente com a legislação posterior. Um arquivo compilado não dispensa conferir vigência e alterações.
- Se páginas legais mudarem de domínio/caminho, alterar a URL somente após verificar a referência oficial.
- Dados físicos e tratamento de ausências serão objeto da etapa 2; nenhuma imputação, soma ou validação estatística faz parte desta etapa.

## Execução

```bash
python scripts/baixar_documentacao_anac.py
```

O workflow arquiva somente documentos verificáveis na branch de documentação; nenhum arquivo altera `data/`, a homepage ou os indicadores.
