# Threat & Thesis

정보보안 권고, AI 보안 프레임워크, 보안 논문, AI 논문과 기술 발표를 검증해 카테고리별 날짜 순위로 보존하는 정적 웹서비스입니다. Next.js로 만들고 GitHub Pages에 배포하며, Hermes Agent가 3시간마다 새 후보만 증분 수집합니다.

## 동작 구조

```text
CISA KEV · NIST NVD · arXiv Atom · Crossref
             │
             ▼
 scripts/collect.py ──> data/inbox.json       비공개 후보
         │             data/source-state.json 출처별 수집 커서
         ▼
     Hermes의 1차 출처 검증·선별·한국어 요약
         │
         ├──> content/articles.json           검증된 자료 본문
         └──> content/daily/YYYY-MM-DD.json   날짜별 순위 스냅샷
                              │
                              ▼
                  Next.js 정적 빌드 ──> GitHub Pages
```

자동 수집 결과는 사이트에 바로 노출되지 않습니다. Hermes가 1차 출처를 확인한 항목만 공개 데이터와 오늘의 카테고리별 순위에 반영합니다. 보안 위협, AI 보안, 보안 논문, AI 논문, 최신 기술은 서로 섞지 않고 각 분야에서 1위부터 다시 시작합니다. 하루가 지난 스냅샷은 보존하므로 화면의 날짜 선택기로 이전 발행분을 다시 볼 수 있습니다.

논문은 공개 원문을 먼저 찾습니다. 공개 PDF나 저자·기관 저장소 원문이 없고 결제 또는 구독이 필요한 논문에만 상세 화면에 `SKKU 원문 확인` 링크를 표시합니다. 링크는 성균관대학교 프록시를 열 뿐 원문을 자동으로 다운로드하지 않습니다.

## 로컬 실행

Node.js 22 이상과 Python 3.10 이상이 필요합니다.

```bash
npm install
npm run dev
```

개발 화면은 기본적으로 `http://localhost:3000`에서 열립니다.

주요 명령:

```bash
npm run content:collect   # 출처별 커서 이후의 최근 3시간 후보를 증분 수집
npm run content:index     # 날짜별 스냅샷을 화면용 index.json으로 결합
npm run content:validate  # 본문·순위·날짜 기록·순위 변동 검사
npm run test:collector    # 증분 커서·복구 범위·중복 제외 단위 테스트
npm test                  # 콘텐츠 검증 + 정적 빌드 + 렌더링 테스트
npm run build:pages       # GitHub Pages용 out/ 정적 파일 생성
```

장기 장애 뒤 명시적인 백필이 필요할 때만 기간을 직접 지정합니다.

```bash
python3 scripts/collect.py --days 7 --max-per-source 10
```

## Hermes Agent 사용

이 저장소 루트에서 Hermes를 실행하면 `AGENTS.md`가 작업 문맥에 포함됩니다. 문체, AI 논문·보안 논문 분류, 날짜별 순위, 수정 범위와 배포 조건은 `EDITORIAL.md`와 프로젝트 스킬에 정리되어 있습니다.

한 번만 갱신하려면:

```bash
hermes -z "HERMES_PROMPT.md의 작업 프롬프트에 따라 Threat & Thesis를 한 번 갱신해줘. 검증된 공개 변경이 있을 때만 커밋하고 origin/main에 푸시해."
```

3시간 정기 작업 등록용 프롬프트와 정확한 명령은 [`HERMES_PROMPT.md`](HERMES_PROMPT.md)에 있습니다. 기본 일정은 매일 0시, 3시, 6시처럼 3시간 간격입니다.

정기 작업은 텔레그램 기본 대화에 시작, 수집 완료, 최종 배포 결과를 짧게 알립니다. 실패하면 실패 단계와 필요한 조치만 즉시 알리고 장문의 실행 로그나 인증정보는 전송하지 않습니다.

정기 갱신은 매 실행마다 최근 14일 전체를 다시 읽지 않습니다. arXiv는 공식 일일 Atom 피드의 `new`·`cross` 발표를 받고, Crossref는 출판사가 등록한 메타데이터의 갱신 시각과 커서를 사용해 3시간 구간 전체를 읽은 뒤 로컬에서 관련 논문을 거릅니다. 이 방식은 새 DOI와 이후 수정된 발행 정보를 함께 포착하면서 단순 재색인 자료는 줄입니다. `data/source-state.json`의 출처별 마지막 성공 시각부터 이어서 받고, 장애로 실행을 놓친 경우에는 최대 7일 범위에서 복구합니다. 공개 변경이 없으면 커밋과 배포도 생략합니다.

## GitHub Pages 배포

이 저장소는 `.github/workflows/pages.yml`로 공개 데이터 검증, 정적 빌드, Pages 배포를 수행합니다. 저장소의 **Settings → Pages → Build and deployment → Source**는 **GitHub Actions**로 설정해야 합니다.

현재 공개 주소:

- <https://girrj.github.io/threat-and-thesis/>

일반 프로젝트 저장소의 주소는 `https://GITHUB_ID.github.io/REPOSITORY_NAME/`이며, 빌드 시 저장소 이름이 `basePath`로 자동 적용됩니다.

## 주요 파일

- `app/page.tsx`: 날짜 선택, 검색, 카테고리별 순위와 상세 보기 UI
- `content/articles.json`: 사이트에 실제 공개되는 검증된 자료
- `content/daily/YYYY-MM-DD.json`: 수정하지 않고 보존하는 날짜별 순위 원본
- `content/daily/index.json`: 정적 화면이 읽는 날짜별 발행본 묶음
- `scripts/collect.py`: 출처별 커서를 사용하는 증분 후보 수집기
- `scripts/build_daily_index.py`: 날짜별 스냅샷 인덱스 생성기
- `scripts/validate.py`: 공개 본문과 순위 변동 검증기
- `AGENTS.md`: Hermes의 3시간 운영 절차
- `EDITORIAL.md`: 문체·논문 분류·순위·디자인·배포 지침
- `HERMES_PROMPT.md`: 복사해 쓸 정기 작업 프롬프트와 등록 명령
- `skills/threat-and-thesis/`: 재사용 가능한 큐레이션 스킬
- `.github/workflows/pages.yml`: GitHub Pages 배포 워크플로

## 출처 원칙

정부·표준기관, 논문 원문, 유지관리되는 보안 지식베이스, 공식 벤더 권고 순으로 우선합니다. 프리프린트는 동료평가 논문과 구분하고, 취약점 점수와 실제 악용 여부를 혼동하지 않으며, 공격 재현법 대신 영향과 방어 조치를 요약합니다.
