# Auditoria da Biblioteca Científica v1.0 — 28/10/2026

## Decisão
**Aprovada para prosseguir à definição de indicadores (Etapa 3)**, como **biblioteca inicial curada**, não como revisão sistemática ou leitura crítica integral dos artigos.

## Conferência realizada
- Presença do arquivo `docs/referencias/biblioteca-cientifica.md` e 12 entradas identificadas por REF-001 a REF-012, incluindo 4 artigos científicos.
- Checagem externa dos metadados, títulos, autores, periódicos e identificadores DOI dos artigos e conferência descritiva das fontes institucionais citadas.
- Verificação de que os estudos internacionais são apresentados como **fundamentação para hipóteses**, sem importar coeficientes para Viracopos.
- Conferência de distinção entre RMA da concessionária, Comex/MDIC, ANAC (transportadoras e operadores), CTK/ACTK da IATA e indicadores macroeconômicos.
- Correção de um link metodológico de validação temporal para um endereço da edição em `otexts.com`.
- Confronto com os contratos locais de dados em `docs/indicadores.md`, `docs/fontes.md` e `data/fontes.json`. Os contratos existentes não foram alterados.

## Lacunas que permanecem explícitas
1. **Textos integrais:** quatro artigos verificados a partir de resumos/metadados; não foi realizada leitura integral independente ou extração exaustiva de coeficientes, dados e testes de robustez.
2. **Cobertura bibliográfica:** seleção intencional; sem protocolo PRISMA, busca sistemática, exaustividade ou avaliação formal de risco de viés.
3. **Datas de disponibilidade:** links institucionais e publicações não demonstram quando cada observação fica disponível para uso em tempo real. Esse calendário será especificado por variável no Catálogo de Indicadores.
4. **Acesso a séries:** existência de fonte não significa que todos os dados, frequências, revisões e direitos de redistribuição estejam confirmados.
5. **Escopo operacional:** nenhuma nova série ANAC foi integrada; falta conciliação dos universos e ampliação do RMA antes de previsões robustas.
6. **Reprodutibilidade dos modelos publicados:** não reproduzida. Reprodutibilidade do estudo de Viracopos exigirá código, versões das séries, separação temporal e métricas de erro.

## Critérios de aceite da Etapa 2
| Critério | Resultado |
|---|---|
| Arquivo publicado, versionado e acessível | Atendido |
| Estudos, referências institucionais e fontes estatísticas catalogados | Atendido (12 entradas) |
| DOI/identificadores e links de origem | Conferidos; link de metodologia ajustado |
| Aplicação e limitações por referência | Atendido |
| Hipóteses preliminares falsificáveis | Atendido (H01–H05) |
| Separação de universos e ausência de alegações causais | Atendido |
| Revisão sistemática e leitura integral | **Não faz parte do aceite v1.0** |
| Dados ou previsões publicados a partir da biblioteca | Não realizados |

## Próxima etapa
Gerar `docs/referencias/catalogo-indicadores-v1.md` com alvos, regressores, fórmulas, periodicidade, disponibilidade, estado no pipeline, horizontes exploratórios e controles para validação temporal. Não implementar modelos nem alterar as fontes atuais nesta passagem.

**Nota de controle:** a aprovação acima é metodológica e documental; não é certificação da vigência normativa ANAC nem confirmação da qualidade estatística de séries futuras.
