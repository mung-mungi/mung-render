#!/bin/bash
# 시황 영상 최종 렌더를 클라우드(8조각)로 보내고 받아 오는 도구 — 공개 저장소라 끝나면 그날 재료·결과를 바로 지움
# 사용: bash cloud_render.sh 그날재료폴더 결과.mp4   (그날재료폴더 안에 script.json 등)
set -e
R=$(cd "$(dirname "$0")" && pwd); SRC=$1; OUT=$2; cd $R
git pull -q --rebase origin main
OLD=$(git ls-remote origin results | cut -f1)
rm -rf job && cp -r "$SRC" job && git add -A job
git -c user.name=mung-mungi -c user.email=mung-mungi@users.noreply.github.com commit -qm "그날 재료 올림(렌더 후 삭제)"
git -c push.negotiate=true push -q origin main; T0=$(date +%s); echo "⏳ 클라우드 렌더 출발"
while true; do NEW=$(git ls-remote origin results | cut -f1); [ -n "$NEW" ] && [ "$NEW" != "$OLD" ] && break
  sleep 15; echo "⏳ 정상 진행 중 — $(( $(date +%s)-T0 ))초째"; [ $(( $(date +%s)-T0 )) -gt 1500 ] && { echo "25분 초과 — 중단"; exit 1; }; done
TMP=$(mktemp -d); git clone -q --depth 1 -b results "$(git remote get-url origin)" $TMP/r && cp $TMP/r/render.mp4 "$OUT" && cat $TMP/r/times.txt
# 정리: 그날 재료 지우고 결과 가지 삭제
git rm -rq job && git -c user.name=mung-mungi -c user.email=mung-mungi@users.noreply.github.com commit -qm "그날 재료 삭제(렌더 끝)" && git -c push.negotiate=true push -q origin main
git push -q origin --delete results; echo "✅ 받기 완료 $(( $(date +%s)-T0 ))초 · 클라우드 재료·결과 삭제함 → $OUT"
