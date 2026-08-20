"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import intelligenceData from "@/content/articles.json";
import dailyData from "@/content/daily/index.json";

type IntelligenceKind =
  | "security"
  | "ai-security"
  | "security-paper"
  | "ai-paper"
  | "technology";

type IntelligenceItem = {
  id: string;
  kind: IntelligenceKind;
  title: string;
  originalTitle?: string;
  source: string;
  sourceUrl: string;
  publishedAt: string;
  dateLabel?: "게시일" | "수정일" | "확인일" | "기준일";
  summary: string;
  whyItMatters: string;
  details: string[];
  limitations?: string[];
  action?: string;
  tags: string[];
  priority: number;
  severity?: "critical" | "high" | "medium" | "info";
  identifier?: string;
  evidenceLevel: "official" | "peer-reviewed" | "preprint" | "industry";
};

type IntelligenceFile = {
  generatedAt: string;
  items: IntelligenceItem[];
};

type RankingStatus = "new" | "up" | "down" | "same" | "returning";

type DailyRanking = {
  rank: number;
  itemId: string;
  previousRank: number | null;
  status: RankingStatus;
  reason: string;
};

type DailyEdition = {
  date: string;
  generatedAt: string;
  rankings: DailyRanking[];
};

type DailyIndex = {
  generatedAt: string;
  editions: DailyEdition[];
};

type RankedItem = {
  item: IntelligenceItem;
  ranking: DailyRanking;
};

const data = intelligenceData as IntelligenceFile;
const daily = dailyData as DailyIndex;

const FILTERS: Array<{ value: "all" | IntelligenceKind; label: string }> = [
  { value: "all", label: "전체" },
  { value: "security", label: "보안 경보" },
  { value: "ai-security", label: "AI 보안" },
  { value: "security-paper", label: "보안 논문" },
  { value: "ai-paper", label: "AI 논문" },
  { value: "technology", label: "최신 기술" },
];

const KIND_LABELS: Record<IntelligenceKind, string> = {
  security: "보안 경보",
  "ai-security": "AI 보안",
  "security-paper": "보안 논문",
  "ai-paper": "AI 논문",
  technology: "최신 기술",
};

const EVIDENCE_LABELS: Record<IntelligenceItem["evidenceLevel"], string> = {
  official: "공식 자료",
  "peer-reviewed": "동료평가",
  preprint: "프리프린트",
  industry: "산업 자료",
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: "Asia/Seoul",
  }).format(new Date(`${value}T00:00:00+09:00`));
}

function formatUpdatedAt(value: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Seoul",
  }).format(new Date(value));
}

function movementLabel(ranking: DailyRanking) {
  if (ranking.status === "new") return "신규";
  if (ranking.status === "returning") return "재진입";
  if (ranking.status === "same") return "유지";
  if (ranking.previousRank === null) return "";

  const difference = Math.abs(ranking.previousRank - ranking.rank);
  return ranking.status === "up" ? `▲ ${difference}` : `▼ ${difference}`;
}

function classNames(...values: Array<string | false | undefined>) {
  return values.filter(Boolean).join(" ");
}

export default function Home() {
  const firstEdition = daily.editions[0];
  const firstRankedId = firstEdition?.rankings[0]?.itemId ?? data.items[0]?.id ?? "";
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | IntelligenceKind>("all");
  const [editionIndex, setEditionIndex] = useState(0);
  const [selectedId, setSelectedId] = useState(firstRankedId);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function focusSearch(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      }
    }
    window.addEventListener("keydown", focusSearch);
    return () => window.removeEventListener("keydown", focusSearch);
  }, []);

  const articleMap = useMemo(
    () => new Map(data.items.map((item) => [item.id, item])),
    [],
  );
  const selectedEdition = daily.editions[editionIndex] ?? daily.editions[0];
  const rankedItems = useMemo(
    () =>
      (selectedEdition?.rankings ?? [])
        .map((ranking) => {
          const item = articleMap.get(ranking.itemId);
          return item ? { item, ranking } : null;
        })
        .filter((entry): entry is RankedItem => entry !== null),
    [articleMap, selectedEdition],
  );

  const filteredItems = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("ko-KR");
    return rankedItems
      .filter(({ item }) => filter === "all" || item.kind === filter)
      .filter(({ item }) => {
        if (!normalized) return true;
        return [
          item.title,
          item.originalTitle,
          item.source,
          item.identifier,
          item.summary,
          ...item.tags,
        ]
          .filter(Boolean)
          .join(" ")
          .toLocaleLowerCase("ko-KR")
          .includes(normalized);
      });
  }, [filter, query, rankedItems]);

  const selectedEntry =
    filteredItems.find(({ item }) => item.id === selectedId) ?? filteredItems[0] ?? null;

  function changeEdition(nextIndex: number) {
    const nextEdition = daily.editions[nextIndex];
    if (!nextEdition) return;
    setEditionIndex(nextIndex);
    setSelectedId(nextEdition.rankings[0]?.itemId ?? "");
  }

  return (
    <main className="site-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Threat & Thesis 홈">
          <span className="brand-mark" aria-hidden="true">T/T</span>
          <span>
            <strong>Threat &amp; Thesis</strong>
            <small>Security research letter</small>
          </span>
        </a>

        <div className="edition-switcher" aria-label="발행일 탐색">
          <button
            type="button"
            onClick={() => changeEdition(editionIndex + 1)}
            disabled={editionIndex >= daily.editions.length - 1}
            aria-label="이전 발행일"
          >
            ←
          </button>
          <label>
            <span className="sr-only">발행일 선택</span>
            <select
              value={selectedEdition?.date}
              onChange={(event) => {
                const nextIndex = daily.editions.findIndex(
                  (edition) => edition.date === event.target.value,
                );
                changeEdition(nextIndex);
              }}
            >
              {daily.editions.map((edition) => (
                <option key={edition.date} value={edition.date}>
                  {formatDate(edition.date)}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={() => changeEdition(editionIndex - 1)}
            disabled={editionIndex === 0}
            aria-label="다음 발행일"
          >
            →
          </button>
        </div>

        <p className="freshness">
          {selectedEdition ? `${formatUpdatedAt(selectedEdition.generatedAt)} 갱신` : ""}
        </p>
      </header>

      <section className="hero" id="top">
        <div>
          <p className="edition">3시간 단위 업데이트 · 일자별 기록</p>
          <h1>데일리 보안·AI 순위</h1>
          <p className="hero-description">
            새로 확인된 보안 이슈와 AI 연구를 검증하고, 오늘 먼저 읽을 자료를 근거와 함께 정리합니다.
          </p>
        </div>
        <p className="edition-meta">
          {selectedEdition ? formatDate(selectedEdition.date) : "발행 준비 중"}
          <span aria-hidden="true">·</span>
          순위 {rankedItems.length}건
          <span aria-hidden="true">·</span>
          AI 논문 {rankedItems.filter(({ item }) => item.kind === "ai-paper").length}
          <span aria-hidden="true">·</span>
          보안 논문 {rankedItems.filter(({ item }) => item.kind === "security-paper").length}
          <span aria-hidden="true">·</span>
          이전 발행분 보존
        </p>
      </section>

      <section className="workspace" aria-labelledby="ranking-title">
        <div className="workspace-heading">
          <div>
            <h2 id="ranking-title">
              {editionIndex === 0 ? "오늘의 우선순위" : `${formatDate(selectedEdition.date)} 우선순위`}
            </h2>
            <p>순위 변동과 선정 이유를 함께 확인할 수 있습니다.</p>
          </div>
          <label className="search-field">
            <span className="sr-only">자료 검색</span>
            <input
              ref={searchRef}
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="제목, CVE, 기술, 출처 검색"
            />
            <kbd aria-hidden="true">⌘ K</kbd>
          </label>
        </div>

        <div className="filter-row" role="group" aria-label="자료 유형 필터">
          {FILTERS.map((filterItem) => (
            <button
              key={filterItem.value}
              type="button"
              className={classNames("filter-button", filter === filterItem.value && "is-active")}
              aria-pressed={filter === filterItem.value}
              onClick={() => setFilter(filterItem.value)}
            >
              {filterItem.label}{" "}
              <span className="filter-count">
                ({filterItem.value === "all"
                  ? rankedItems.length
                  : rankedItems.filter(({ item }) => item.kind === filterItem.value).length})
              </span>
            </button>
          ))}
        </div>

        <div className="intelligence-layout">
          <div className="feed" aria-live="polite">
            <div className="feed-meta">
              <span>{filteredItems.length}건</span>
              <span>편집 순위</span>
            </div>

            {filteredItems.length ? (
              filteredItems.map(({ item, ranking }) => (
                <button
                  key={item.id}
                  type="button"
                  className={classNames(
                    "feed-card",
                    selectedEntry?.item.id === item.id && "is-selected",
                  )}
                  onClick={() => setSelectedId(item.id)}
                  aria-pressed={selectedEntry?.item.id === item.id}
                >
                  <span className="rank-number" aria-label={`${ranking.rank}위`}>
                    {ranking.rank}
                  </span>
                  <span className="feed-card-body">
                    <span className="card-topline">
                      <span className="kind-label">{KIND_LABELS[item.kind]}</span>
                      <span className={classNames("rank-change", `rank-${ranking.status}`)}>
                        {movementLabel(ranking)}
                      </span>
                      <time dateTime={item.publishedAt}>{formatDate(item.publishedAt)}</time>
                    </span>
                    <strong>{item.title}</strong>
                    <span className="rank-reason">{ranking.reason}</span>
                    <span className="card-footer">
                      <span>{item.source}</span>
                      {item.identifier && <code>{item.identifier}</code>}
                    </span>
                  </span>
                </button>
              ))
            ) : (
              <div className="empty-state">
                <strong>검색 결과가 없습니다.</strong>
                <p>검색어를 줄이거나 다른 자료 유형을 선택해 보세요.</p>
              </div>
            )}
          </div>

          <aside className="detail-panel" aria-live="polite">
            {selectedEntry ? (
              <article>
                <div className="detail-header">
                  <span>
                    {selectedEntry.ranking.rank}위 · {KIND_LABELS[selectedEntry.item.kind]} ·{" "}
                    {EVIDENCE_LABELS[selectedEntry.item.evidenceLevel]}
                  </span>
                  <span>{movementLabel(selectedEntry.ranking)}</span>
                </div>

                <h3>{selectedEntry.item.title}</h3>
                {selectedEntry.item.originalTitle && (
                  <p className="original-title">{selectedEntry.item.originalTitle}</p>
                )}

                <dl className="source-meta">
                  <div>
                    <dt>출처</dt>
                    <dd>{selectedEntry.item.source}</dd>
                  </div>
                  <div>
                    <dt>{selectedEntry.item.dateLabel ?? "게시일"}</dt>
                    <dd>{formatDate(selectedEntry.item.publishedAt)}</dd>
                  </div>
                  {selectedEntry.item.identifier && (
                    <div>
                      <dt>식별자</dt>
                      <dd>{selectedEntry.item.identifier}</dd>
                    </div>
                  )}
                </dl>

                <section className="detail-section ranking-reason-section">
                  <h4>선정 이유</h4>
                  <p>{selectedEntry.ranking.reason}</p>
                </section>

                <section className="detail-section">
                  <h4>핵심 요약</h4>
                  <p>{selectedEntry.item.summary}</p>
                </section>

                <section className="detail-section">
                  <h4>왜 중요한가</h4>
                  <p>{selectedEntry.item.whyItMatters}</p>
                </section>

                <section className="detail-section">
                  <h4>주요 내용</h4>
                  <ul>
                    {selectedEntry.item.details.map((detail) => <li key={detail}>{detail}</li>)}
                  </ul>
                </section>

                {selectedEntry.item.limitations?.length ? (
                  <section className="detail-section caution-section">
                    <h4>한계와 확인사항</h4>
                    <ul>
                      {selectedEntry.item.limitations.map((limitation) => (
                        <li key={limitation}>{limitation}</li>
                      ))}
                    </ul>
                  </section>
                ) : null}

                {selectedEntry.item.action && (
                  <section className="action-box">
                    <h4>실무 메모</h4>
                    <p>{selectedEntry.item.action}</p>
                  </section>
                )}

                <div className="tag-list" aria-label="태그">
                  {selectedEntry.item.tags.map((tag) => <span key={tag}>#{tag}</span>)}
                </div>

                <a
                  className="source-link"
                  href={selectedEntry.item.sourceUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  원문 확인 <span aria-hidden="true">↗</span>
                </a>
              </article>
            ) : (
              <div className="detail-placeholder">표시할 자료를 선택해 주세요.</div>
            )}
          </aside>
        </div>
      </section>

      <section className="sources" aria-labelledby="sources-title">
        <div>
          <h2 id="sources-title">확인하는 출처</h2>
          <p>정부·표준기관, 논문 원문과 공식 제품 권고를 우선합니다.</p>
        </div>
        <div className="source-grid">
          {["CISA KEV", "NIST NVD", "KISA KrCERT", "arXiv", "Semantic Scholar", "MITRE ATLAS", "OWASP GenAI", "공식 제품 권고"].map(
            (source) => <span key={source}>{source}</span>,
          )}
        </div>
      </section>

      <footer>
        <strong>Threat &amp; Thesis</strong>
        <p>원문을 확인한 자료만 공개합니다.</p>
        <a href="#top">맨 위로 ↑</a>
      </footer>
    </main>
  );
}
