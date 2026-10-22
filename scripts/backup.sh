#!/usr/bin/env bash
# DB 덤프와 첨부파일을 backups/<날짜>/ 에 저장합니다. cron 예) 0 2 * * * /opt/ax-lib/scripts/backup.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DEST="backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DEST"
docker compose exec -T db pg_dump -U axlib -Fc axlib > "$DEST/axlib.dump"
tar czf "$DEST/uploads.tar.gz" -C volumes uploads
# 30일 지난 백업 정리
find backups -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +
echo "백업 완료: $DEST"
