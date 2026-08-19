# Threat & Thesis

정보보안 권고, AI 보안 프레임워크, 보안 논문, AI 논문과 기술 발표를 원문 링크와 함께 모아 보는 정적 웹서비스입니다. 화면은 Next.js로 만들고 GitHub Pages에 배포하며, Hermes Agent가 수집 후보를 검증하고 `content/articles.json`을 큐레이션합니다.

## 동작 구조

```text
CISA KEV · NIST NVD · arXiv
             │
             ▼
 scripts/collect.py ──> data/inbox.json  (비공개 후보)
             │
             ▼
     Hermes 검증·선별·한국어 요약
             │
             ▼
 content/articles.json ──> Next.js 정적 빌드 ──> GitHub Pages
```

자동 수집 결과는 사이트에 바로 노출되지 않습니다. Hermes가 1차 출처를 확인하고 공개 JSON으로 옮긴 항목만 배포됩니다.

## 로컬 실행

Node.js 22 이상과 Python 3.10 이상이 필요합니다.

```bash
npm install
npm run dev
```

개발 화면은 기본적으로 `http://localhost:3000`에서 열립니다.

주요 명령:

```bash
npm run content:collect   # 최근 14일 후보를 data/inbox.json에 수집
npm run content:validate  # 공개 콘텐츠의 스키마와 중복 검사
npm test                  # 콘텐츠 검증 + 정적 빌드 + 렌더링 테스트
npm run build:pages       # GitHub Pages용 out/ 정적 파일 생성
```

수집 범위를 바꾸려면 Python 스크립트를 직접 실행합니다.

```bash
python3 scripts/collect.py --days 7 --max-per-source 10
```

## Hermes Agent 사용

이 저장소 루트에서 Hermes를 실행하면 `AGENTS.md`가 자동으로 작업 문맥에 포함되고, 그 지침에 따라 `EDITORIAL.md`도 읽습니다. 문체, AI 논문·보안 논문 분류, 디자인, 수정 범위와 배포 조건을 매번 다시 설명할 필요는 없습니다.

한 번 갱신하려면:

```bash
hermes -z "AGENTS.md 절차에 따라 최신 정보보안·AI 자료를 수집하고, 원문을 검증해 공개할 가치가 있는 항목만 사이트에 반영한 뒤 모든 검증을 실행해줘."
```

매주 월요일 오전 8시에 실행하려면 다음처럼 cron 작업을 만들 수 있습니다. `--workdir`은 반드시 이 저장소의 실제 절대 경로로 바꿉니다.

```bash
hermes cron create "0 8 * * 1" \
  "AGENTS.md 절차에 따라 최근 정보보안·AI 자료를 검증·큐레이션하고 테스트 결과를 보고해줘." \
  --name "threat-and-thesis-weekly" \
  --workdir "/absolute/path/to/threat-and-thesis"
```

프로젝트에는 재사용 가능한 Hermes/Codex 스킬도 `skills/threat-and-thesis/`에 포함되어 있습니다. 저장소를 공개한 뒤 다른 환경에 설치하려면 해당 `SKILL.md`의 raw GitHub URL을 `hermes skills install`에 전달할 수 있습니다.

> Hermes의 커밋·푸시는 외부 상태를 바꾸므로 기본 운영 규칙에서 자동 실행하지 않습니다. 완전 자동 배포가 필요하면 사용자가 Hermes 작업에 커밋·푸시 권한과 명령을 명시적으로 추가해야 합니다.

## GitHub Pages 배포

1. GitHub에서 빈 저장소를 만들고 이 프로젝트를 `main` 브랜치에 푸시합니다.
2. 저장소 **Settings → Pages → Build and deployment → Source**를 **GitHub Actions**로 설정합니다.
3. `.github/workflows/pages.yml`이 콘텐츠를 검증하고 저장소 이름에 맞는 `basePath`로 정적 빌드한 뒤 Pages에 배포합니다.

일반 프로젝트 저장소라면 주소는 `https://GITHUB_ID.github.io/REPOSITORY_NAME/`입니다. 저장소 이름이 `GITHUB_ID.github.io`이면 루트 주소로 배포됩니다.

예시:

```bash
git init -b main
git add .
git commit -m "Build Threat & Thesis"
git remote add origin https://github.com/GITHUB_ID/REPOSITORY_NAME.git
git push -u origin main
```

## 주요 파일

- `app/page.tsx`: 검색·필터·상세 보기 UI
- `content/articles.json`: 사이트에 실제 공개되는 검증된 자료
- `content/article.schema.json`: 공개 콘텐츠 JSON Schema
- `scripts/collect.py`: CISA KEV, NIST NVD, arXiv 후보 수집기
- `scripts/validate.py`: 공개 전 콘텐츠 검증기
- `AGENTS.md`: Hermes의 프로젝트 운영 규칙
- `EDITORIAL.md`: 문체·논문 분류·디자인·배포 편집 지침
- `skills/threat-and-thesis/`: 재사용 가능한 큐레이션 스킬
- `.github/workflows/pages.yml`: GitHub Pages 배포 워크플로

## 출처 원칙

정부·표준기관, 논문 원문, 유지관리되는 보안 지식베이스, 공식 벤더 권고 순으로 우선합니다. 프리프린트는 동료평가 논문과 구분하고, 취약점 점수와 실제 악용 여부를 혼동하지 않으며, 공격 재현법 대신 영향과 방어 조치를 요약합니다.
