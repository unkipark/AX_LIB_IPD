#!/usr/bin/env bash
# 외부망에서 실행: 이미지를 빌드해 tar 하나로 묶습니다. 폐쇄망 서버로 반입 후 import-images.sh 로 올립니다.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
VERSION="${APP_VERSION:-$(git rev-parse --short HEAD 2>/dev/null || echo latest)}"
docker build -t "ax-lib:$VERSION" -t ax-lib:latest .
docker pull postgres:16-alpine
mkdir -p dist-images
docker save "ax-lib:$VERSION" ax-lib:latest postgres:16-alpine | gzip > "dist-images/ax-lib-$VERSION.tar.gz"
echo "dist-images/ax-lib-$VERSION.tar.gz 생성 완료"
