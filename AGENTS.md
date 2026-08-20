# Threat & Thesis 운영 규칙

이 저장소는 정보보안·AI 논문과 기술 동향을 선별해 날짜별 순위로 보존하고 GitHub Pages로 배포한다. 자동 수집 결과는 후보일 뿐이며, 검증 전에는 공개 콘텐츠가 아니다.

작업을 시작할 때 반드시 `EDITORIAL.md`를 읽는다. 문체, 논문 분류, 순위, 화면 디자인, 수정 가능 파일, 배포 조건은 그 문서를 기준으로 한다. 출처 세부 정책은 `skills/threat-and-thesis/references/source-policy.md`를 함께 따른다.

## 3시간 갱신 절차

예약 작업 프롬프트에 명시된 텔레그램 대상(`telegram:<chat_id>`)에 시작, 수집 완료, 최종 결과를 각각 한 번씩 짧게 알린다. 기본 대상인 `telegram`만 사용하지 않는다. 중단이나 실패는 실패 단계와 필요한 조치만 즉시 알린다. 메시지는 `hermes send --to telegram:<chat_id> "메시지"`로 보내며 장문의 로그, 토큰, 인증정보를 포함하지 않는다. 명시적 대상이 없는 수동 실행에서는 진행 알림을 생략한다.

1. 저장소 루트에서 `python3 scripts/collect.py --since-hours 3`를 실행한다. 수집기는 출처별 마지막 성공 시각을 기억하므로 매번 전체 기간을 다시 수집하지 않는다.
2. `data/inbox.json`의 `sources` 오류와 `candidates`를 확인한다. `data/source-state.json`은 수집 커서, `data/processed.json`은 이미 판단한 후보 기록이다. 이 런타임 파일들은 공개 콘텐츠가 아니다.
   - arXiv 후보의 `kind`는 카테고리와 초록에 따른 제안값이다. `raw.needsEditorialReview`가 참이거나 AI·보안 신호가 함께 있으면 논문의 핵심 연구 대상을 읽고 최종 분류한다.
   - Crossref 후보의 `evidenceLevel: publication-record`는 DOI 등록 기록이라는 뜻이지 동료평가 확인이 아니다. 출판사 또는 학회 페이지에서 게재 상태를 확인한 뒤에만 공개 항목에 `peer-reviewed`를 사용한다.
3. 기존 `content/articles.json`과 URL, 식별자, 정규화한 제목을 비교해 중복을 제외한다.
4. 후보의 `sourceUrl`과 연결된 1차 출처를 직접 확인한다. 검색 결과 설명이나 제3자 요약만으로 게시하지 않는다.
5. 가치가 높은 항목만 `content/articles.json`에 추가하거나, 같은 사건의 공식 정보가 바뀐 경우 기존 항목을 수정한다. 실제 변경이 있을 때만 `generatedAt`을 갱신한다.
6. 오늘 날짜의 `content/daily/YYYY-MM-DD.json`을 만든다. 같은 날짜에는 이 파일을 갱신할 수 있지만 지난 날짜 스냅샷은 사실 오류를 바로잡는 경우 외에는 수정하지 않는다.
7. `security`, `ai-security`, `security-paper`, `ai-paper`, `technology`를 섞은 전체 순위를 만들지 않는다. 각 카테고리 안에서 최대 10건을 별도로 순위화한다. 긴급성·실제 악용·출처 신뢰도·신선도·실무 영향·연구 기여를 함께 고려하고, 각 항목에 출처로 설명 가능한 `reason`을 한 문장으로 쓴다.
8. 같은 카테고리의 직전 발행일 순위와 비교해 `previousRank`와 `status`를 기록한다. 처음 등장하면 `new`, 연속 발행에서 상승·하락·유지는 `up`·`down`·`same`, 하루 이상 빠졌다가 돌아오면 `returning`이다.
9. 공개하지 않은 후보도 `data/processed.json`에 ID와 판단 시각, 간단한 제외 이유를 남겨 다음 실행에서 반복 검토하지 않는다. 새 공식 정보가 생긴 항목은 다시 검토할 수 있다.
10. `npm run content:validate`, `npm run lint`, `npm test`, `SITE_BASE_PATH=/threat-and-thesis npm run build:pages`를 실행한다.
11. 검증이 모두 통과한 경우에만 변경 내용을 보고한다. 커밋·푸시는 사용자가 해당 작업에 명시적으로 요청했을 때만 수행한다. 새로 공개할 내용이나 정정이 없으면 파일을 억지로 바꾸거나 빈 커밋을 만들지 않는다.

장애로 3시간 주기를 놓친 경우 수집기는 출처별 마지막 성공 시각부터 최대 7일을 복구 수집한다. 장기 백필이 필요한 경우에만 `python3 scripts/collect.py --days N`을 명시적으로 사용한다.

## 작성 기준

- 사실, 날짜, CVE, CVSS, 논문 결과, 제품 버전을 추측하거나 만들어내지 않는다.
- 원문 제목은 `originalTitle`, 한국어 편집 제목은 `title`에 둔다.
- `summary`는 무엇이 발표됐는지, `whyItMatters`는 독자에게 왜 중요한지 분리한다.
- `details`는 출처가 직접 뒷받침하는 내용만 쓴다.
- `limitations`에는 프리프린트 여부, 적용 범위, 확인되지 않은 부분을 명시한다.
- `action`은 방어·평가·업데이트 같은 안전한 다음 행동만 제안한다.
- 프리프린트는 `evidenceLevel: preprint`, 정부·표준기관·공식 벤더 권고는 `official`로 표시한다.
- 논문은 주된 연구 질문을 기준으로 분류한다. AI 모델·에이전트·머신러닝이 연구 대상이면 `ai-paper`, 일반 시스템·네트워크·암호·소프트웨어 보안 연구이면 `security-paper`를 사용한다. 두 영역이 겹치면 논문의 핵심 기여가 향하는 쪽 하나만 선택하고 보고에 근거를 남긴다.
- 논문은 출판사·DOI 페이지, 공개 저장소, arXiv, OpenAlex·Unpaywall의 공개 원문 위치를 먼저 확인한다. 합법적인 공개 원문이 하나라도 있으면 `requiresLibraryAccess`를 쓰지 않는다. 공개 원문 없이 구독 또는 결제가 필요한 경우에만 `requiresLibraryAccess: true`를 추가한다. 이때 `sourceUrl`은 프록시 주소가 아니라 DOI 또는 출판사 원문 페이지를 유지하고, 공개 초록 밖의 내용을 확인한 것처럼 작성하지 않는다.
- 살아 있는 지식베이스나 수집 기준일은 `dateLabel: 확인일` 또는 `기준일`로 구분한다.
- 공개 익스플로잇을 재현하거나 공격 자동화 코드를 작성하지 않는다. 필요한 경우 영향과 방어책만 요약한다.
- 오래된 기사와 지난 날짜 스냅샷을 임의로 삭제하지 않는다. 정리나 삭제는 사용자의 지시를 받는다.

## 내부 우선도

`articles.json`의 `priority`는 후보 선별과 순위 판단을 돕는 내부 값이며 화면에 점수로 노출하지 않는다. 최종 공개 순위는 숫자 하나만으로 자동 결정하지 않고 당일 맥락과 검증 결과를 반영한다.

- 95–100: 실제 악용 확인, 긴급 패치, 광범위한 공급망 영향
- 85–94: Critical 취약점, 주요 표준·프레임워크 변화, 실무 영향이 큰 연구
- 70–84: 추적 가치가 높은 연구·기술 발표
- 0–69: 후보 또는 배경 자료. 선별 이유가 약하면 공개하지 않는다.

자세한 편집 기준은 `EDITORIAL.md`, 출처 정책은 `skills/threat-and-thesis/references/source-policy.md`를 따른다.
