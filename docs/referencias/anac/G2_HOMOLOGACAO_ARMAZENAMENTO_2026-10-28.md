# G2 — homologação de armazenamento independente e ensaio de restauração

**Estado em 28/10/2026:** CONTROLES TÉCNICOS TESTADOS, G2 OPERACIONAL **NÃO HOMOLOGADO**. Execução local simulada com arquivos sintéticos em runner efêmero ≠ armazenamento permanente ou cópia independente. Não houve download adicional de fontes ANAC.

## Objetivo e limites

Provar que um original CSV nacional ANAC guardado fora do Git pode sobreviver à perda do cofre de trabalho, incluindo seus recibos/revisões, com backup verificável por SHA-256, restauração em diretório separado e reprocessamento de SBKP. O hash confere integridade acidental, mas não comprova autenticidade nem resiste a quem possa alterar objetos e manifestos conjuntamente. Exigir proteção de credenciais, controle de acesso, imutabilidade/versionamento independente e cópia fora do domínio de falha do computador de origem.

**O que não está feito:** provedor externo contratado/provisionado, volume de backup independente identificado, replicação offsite, política de retenção em serviço real, teste de restauração real do usuário, originais nacionais recuperados para as quatro competências ANAC já arquivadas (o Git conserva apenas recortes SBKP e hashes dos originais). Não declarar G2 concluído.

## Rotina automática de ensaio — sem rede

Código: scripts/ensaio_recuperacao_g2_anac.py e tests/test_ensaio_recuperacao_g2_anac.py.

A rotina exige três diretórios *já existentes*, fora do Git e não aninhados:
- Cofre primário com objects/ e receipts/ auditados; incoming/ pode estar vazio, mas nenhuma transferência parcial é aceita.
- Raiz de backups, que receberá snapshots/ID_HASH.
- Raiz de recuperação, para cópia **temporária**, que é removida após os controles.

Fluxo: auditoria da origem → conferência do bruto selecionado por competência e SHA exato → backup por inventário SHA-256 → verificação independente do snapshot → restauração em diretório temporário novo → igualdade bit a bit do inventário e dos arquivos restaurados → reprocessamento offline da competência selecionada → verificação de inalterabilidade do cofre e do backup. Não executa workflows, não escreve em data/anac/rima, não publica e não invoca ANAC.

O comando possui modo simulado (permite mesmo dispositivo para testes, nunca certifica G2) e pre_homologacao (recusa source e backup no mesmo st_dev do sistema operacional). **Mesmo st_dev diferente não garante discos fisicamente distintos**, porque duas partições de um único disco, dispositivos virtuais ou mounts de rede mal definidos ainda podem compartilhar falha. O processo **sempre** retorna g2_operacional_aprovado=false; somente avaliação com evidências operacionais externas pode alterar esse status, mediante autorização formal.

### Exemplos de execução, somente após preparar o ambiente

Os caminhos abaixo são ilustrativos; não representam volumes configurados para o projeto.

~~~bash
# Confirmar que há discos/volumes efetivamente montados e separados
findmnt -T /mnt/d/vcp-anac-brutos
findmnt -T /mnt/e/vcp-anac-backups
df -T /mnt/d/vcp-anac-brutos /mnt/e/vcp-anac-backups

# Pasta de recuperação e pasta para relatório devem existir no volume apropriado
python scripts/ensaio_recuperacao_g2_anac.py \
  --cofre /mnt/d/vcp-anac-brutos \
  --backups /mnt/e/vcp-anac-backups \
  --recuperacao-parent /mnt/d/vcp-anac-recuperacoes \
  --competencia 2020-04 \
  --sha256 SHA256_REAL_DO_CSV_ORIGINAL_JA_PRESERVADO \
  --modo pre_homologacao \
  --evidencia /mnt/e/vcp-anac-backups/ensaio-g2-2026-10-28.json
~~~

**No Windows com WSL:** letras de unidade distintas não provam discos independentes. Use as informações de disco/partição (Gerenciamento de Disco / Get-Disk e Get-Partition) para verificar se a mídia da cópia é independente da mídia de origem. Se o backup estiver em serviço cloud, a sincronização precisa de ferramentas/protocolos específicos, não é automaticamente criada pelo script. Nenhuma chave ou token deve ser commitado.

## Critérios de aceite operacional (todos necessários)

| Controle | Evidência requerida | Estado |
|---|---|---|
| G2-A | Cofre primário fora do Git, armazenamento permanente definido e acesso controlado | Pendente infraestrutura |
| G2-B | Segundo destino em domínio de falha independente, cópia real versionada/imutável | Pendente infraestrutura |
| G2-C | Snapshot original e recibos no backup, hashes e inventário auditados | Testado localmente; pendente real |
| G2-D | Recuperação real em diretório novo, sem sobrescrever, com prova SHA-256 integral | Testado localmente; pendente real |
| G2-E | Reprocessamento pós-restauração usando original real e SHA exato | Testado sinteticamente; pendente real |
| G2-F | Retenção, segurança de acesso, rotação, recuperação a desastres e responsável nomeado | Pendente decisão |
| G2-G | Evidência de tempo real de recuperação, limites do ambiente e aprovação humana | Pendente real |

**Não homologar G2 apenas por testes CI verdes.** Em especial, o experimento do runner GitHub usa diretórios temporários no mesmo ambiente e arquivos sintéticos, cuja persistência cessa após a execução. Os valores medidos de tempo são apenas diagnósticos daquele ambiente; não são RTO/RPO de produção.

## Evidências de código e diagnóstico

- Backup/restauração controlados: scripts/backup_acervo_anac.py.
- Ensaios, check de dispositivos, fail-closed para arquivos pendentes e replay: scripts/ensaio_recuperacao_g2_anac.py.
- Testes: tests/test_ensaio_recuperacao_g2_anac.py (restauração, idempotência, revisão de um mês, falhas por hash, ausência de diretórios, mesmo dispositivo e transferência parcial). O CI completo na branch demonstra compatibilidade com o site e parser histórico.

**Próxima decisão operacional necessária:** escolher os volumes/serviço de backup, providenciar autenticação e permissões, e executar o ensaio com um CSV nacional oficial efetivamente preservado. Enquanto esse controle não for demonstrado, permanecem bloqueados novos lotes históricos G5/G6. O teste do recorte ANAC-04 independe disso, mas não libera coleta.
