# Threat & Thesis 운영 규칙

이 저장소는 정보보안·AI 논문과 기술 동향을 선별해 GitHub Pages로 배포한다. 자동 수집 결과는 후보일 뿐이며, 검증 전에는 공개 콘텐츠가 아니다.

## 정기 큐레이션 절차

1. 저장소 루트에서 `python3 scripts/collect.py --days 14`를 실행한다.
2. `data/inbox.json`의 `sources` 오류와 `candidates`를 확인한다.
3. 기존 `content/articles.json`과 URL, 식별자, 제목을 비교해 중복을 제외한다.
4. 후보의 `sourceUrl`과 연결된 1차 출처를 직접 확인한다. 검색 결과 설명이나 제3자 요약만으로 게시하지 않는다.
5. 가치가 높은 항목만 `content/articles.json`에 추가하고 `generatedAt`을 실제 갱신 시각으로 변경한다.
6. `python3 scripts/validate.py`, `npm test`, `SITE_BASE_PATH=/REPOSITORY_NAME npm run build:pages`를 차례로 실행한다.
7. 검증이 모두 통과한 경우에만 변경 내용을 보고한다. 커밋·푸시는 사용자가 명시적으로 요청했을 때만 수행한다.

## 작성 기준

- 사실, 날짜, CVE, CVSS, 논문 결과, 제품 버전을 추측하거나 만들어내지 않는다.
- 원문 제목은 `originalTitle`, 한국어 편집 제목은 `title`에 둔다.
- `summary`는 무엇이 발표됐는지, `whyItMatters`는 독자에게 왜 중요한지 분리한다.
- `details`는 출처가 직접 뒷받침하는 내용만 쓴다.
- `limitations`에는 프리프린트 여부, 적용 범위, 확인되지 않은 부분을 명시한다.
- `action`은 방어·평가·업데이트 같은 안전한 다음 행동만 제안한다.
- 프리프린트는 `evidenceLevel: preprint`, 정부·표준기관·공식 벤더 권고는 `official`로 표시한다.
- 살아 있는 지식베이스나 수집 기준일은 `dateLabel: 확인일` 또는 `기준일`로 구분한다.
- 공개 익스플로잇을 재현하거나 공격 자동화 코드를 작성하지 않는다. 필요한 경우 영향과 방어책만 요약한다.
- 오래된 항목을 임의로 삭제하지 않는다. 정리나 삭제는 사용자의 지시를 받는다.

## 우선순위

- 95–100: 실제 악용 확인, 긴급 패치, 광범위한 공급망 영향
- 85–94: Critical 취약점, 주요 표준·프레임워크 변화, 실무 영향이 큰 연구
- 70–84: 추적 가치가 높은 연구·기술 발표
- 0–69: 후보 또는 배경 자료. 선별 이유가 약하면 공개하지 않는다.

자세한 출처 정책은 `skills/threat-and-thesis/references/source-policy.md`를 따른다.
