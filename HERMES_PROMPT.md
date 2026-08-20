# Hermes 3시간 갱신 프롬프트

아래 프롬프트는 이 저장소에서 3시간마다 실행하는 정기 큐레이션 작업용이다. 이 프롬프트로 작업을 등록하는 것은 검증된 공개 콘텐츠 변경에 한해 커밋과 `origin/main` 푸시까지 허용한다는 뜻이다.

## 작업 프롬프트

```text
Threat & Thesis의 3시간 정기 갱신을 수행해줘. 먼저 AGENTS.md, EDITORIAL.md, skills/threat-and-thesis/SKILL.md, skills/threat-and-thesis/references/source-policy.md를 읽고 그대로 따라라.

1. 작업 시작 전 git status를 확인한다. 기존의 예상하지 못한 로컬 변경이 있으면 덮어쓰지 말고 중단 사유를 보고한다. 작업 트리가 깨끗하면 `git pull --ff-only origin main`으로 배포 저장소의 최신 상태를 받은 뒤 진행하고, fast-forward가 불가능하면 임의 병합하지 말고 중단한다.
2. python3 scripts/collect.py --since-hours 3을 실행한다. 출처 하나가 실패해도 나머지는 계속 검토하고 실패 출처를 보고한다.
3. data/inbox.json 후보를 content/articles.json 및 data/processed.json과 중복 검사한다. arXiv의 kind는 분류 제안일 뿐이므로 raw.needsEditorialReview와 논문의 핵심 연구 대상을 확인한다. Crossref의 publication-record는 DOI 등록 기록이지 동료평가 증명이 아니므로 출판사·학회 페이지에서 게재 상태를 확인한다. 검색 결과나 제3자 요약만 믿지 말고 모든 게시 후보의 1차 출처를 직접 확인한다.
4. 공개 가치가 확인된 자료만 content/articles.json에 한국어로 반영한다. AI 모델·에이전트·머신러닝 연구는 ai-paper, 일반 시스템·네트워크·암호·소프트웨어 보안 연구는 security-paper로 구분한다. 프리프린트와 공식 자료를 정확히 표시하고 확인되지 않은 수치나 사실을 만들지 않는다. 논문은 출판사·DOI 페이지, 공개 저장소, arXiv, 가능한 경우 OpenAlex·Unpaywall의 공개 원문 위치를 확인한다. 합법적인 공개 원문이 있으면 requiresLibraryAccess를 쓰지 않고, 공개 원문 없이 결제나 구독이 필요한 논문에만 requiresLibraryAccess: true를 추가한다. sourceUrl은 DOI 또는 출판사 페이지를 유지하며, 구독 원문을 읽지 못했다면 공개 초록이 뒷받침하는 내용만 쓰고 limitations에 원문 미확인을 명시한다.
5. 검토를 끝낸 후보는 채택 여부와 간단한 이유를 data/processed.json에 기록해 다음 실행에서 같은 후보를 반복 검토하지 않는다.
6. 오늘 날짜의 content/daily/YYYY-MM-DD.json을 갱신한다. 전체 통합 순위를 만들지 말고 security, ai-security, security-paper, ai-paper, technology마다 최대 10건을 별도로 순위화한다. 각 카테고리의 번호는 1위부터 시작하며, 같은 카테고리의 직전 날짜와 비교한 previousRank와 status(new/up/down/same/returning), 근거가 분명한 한 문장의 reason을 작성한다. 지난 날짜 스냅샷은 사실 오류 정정 외에는 수정하지 않는다.
7. npm run content:validate, npm run lint, npm test, SITE_BASE_PATH=/threat-and-thesis npm run build:pages를 모두 실행한다.
8. 검증이 모두 통과했고 공개 추적 파일에 실제 변경이 있을 때만 변경 파일을 커밋하고 origin main에 푸시한다. 커밋 메시지는 chore(content): refresh YYYY-MM-DD HH:mm KST 형식을 사용한다. GitHub Pages 워크플로 상태를 확인하고 추가·수정·제외 항목, 순위 변동, 출처 오류, 검증 및 배포 결과를 보고한다.
9. 공개할 새 내용이나 정정이 없으면 공개 파일의 generatedAt을 바꾸지 말고, 빈 커밋이나 푸시 없이 결과만 보고한다. 정기 갱신 중에는 UI, 스키마, 운영 정책을 임의로 변경하지 않는다.
```

## 등록 명령

저장소 루트에서 다음 명령을 한 번 실행한다.

```bash
hermes cron create "0 */3 * * *" \
  'Threat & Thesis의 3시간 정기 갱신을 수행해줘. 먼저 HERMES_PROMPT.md의 작업 프롬프트와 AGENTS.md, EDITORIAL.md를 읽고 모든 절차를 그대로 수행해. 검증된 공개 변경이 있을 때에만 커밋하고 origin/main에 푸시한 뒤 GitHub Pages 배포 결과까지 보고해. 변경이 없으면 빈 커밋을 만들지 마.' \
  --name "threat-and-thesis-3h" \
  --workdir "/Users/jaydev/codex_dev/논문_dev"
```

등록 후 `hermes cron list`로 작업을 확인한다. GitHub 인증이 만료되면 수집과 검증까지만 끝내고 푸시 실패를 보고해야 한다.
