#!/usr/bin/env bash
# 폐쇄망 서버에서 실행: export-images.sh 가 만든 tar.gz 를 docker 에 올립니다.
set -euo pipefail
[ $# -eq 1 ] || { echo "사용법: $0 dist-images/ax-lib-<버전>.tar.gz"; exit 1; }
gunzip -c "$1" | docker load
