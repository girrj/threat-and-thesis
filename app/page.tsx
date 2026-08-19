"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import intelligenceData from "@/content/articles.json";

type IntelligenceKind = "security" | "ai-security" | "paper" | "technology";

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

const data = intelligenceData as IntelligenceFile;

const FILTERS: Array<{ value: "all" | IntelligenceKind; label: string }> = [
  { value: "all", label: "전체" },
  { value: "security", label: "보안 경보" },
  { value: "ai-security", label: "AI 보안" },
  { value: "paper", label: "논문" },
  { value: "technology", label: "최신 기술" },
];

const KIND_LABELS: Record<IntelligenceKind, string> = {
  security: "보안 경보",
  "ai-security": "AI 보안",
  paper: "논문",
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

function classNames(...values: Array<string | false | undefined>) {
  return values.filter(Boolean).join(" ");
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | IntelligenceKind>("all");
  const [selectedId, setSelectedId] = useState(data.items[0]?.id ?? "");
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

  const filteredItems = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("ko-KR");
    return [...data.items]
      .filter((item) => filter === "all" || item.kind === filter)
      .filter((item) => {
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
      })
      .sort((a, b) => b.priority - a.priority || b.publishedAt.localeCompare(a.publishedAt));
  }, [filter, query]);

  const selectedItem =
    filteredItems.find((item) => item.id === selectedId) ?? filteredItems[0] ?? null;

  const counts = useMemo(
    () => ({
      security: data.items.filter((item) => item.kind === "security").length,
      research: data.items.filter((item) => item.kind === "paper").length,
      aiSecurity: data.items.filter((item) => item.kind === "ai-security").length,
    }),
    [],
  );

  return (
    <main className="site-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Threat & Thesis 홈">
          <span className="brand-mark" aria-hidden="true">T/T</span>
          <span>
            <strong>Threat &amp; Thesis</strong>
            <small>Research &amp; Threat Intelligence</small>
          </span>
        </a>
        <nav aria-label="주요 메뉴">
          <a href="#intelligence">인텔리전스</a>
          <a href="#sources">출처</a>
        </nav>
        <div className="freshness">
          <span className="live-dot" aria-hidden="true" />
          최근 갱신 {formatDate(data.generatedAt.slice(0, 10))}
        </div>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow">INFORMATION SECURITY · ARTIFICIAL INTELLIGENCE</p>
          <h1>보안과 AI의 변화를<br />한곳에서 추적합니다.</h1>
          <p className="hero-description">
            공식 보안 권고, AI 보안 프레임워크, 최신 논문과 기술 발표를 출처와 함께 모아
            실무 관점으로 정리합니다.
          </p>
        </div>
        <dl className="metrics" aria-label="현재 수집 현황">
          <div>
            <dt>보안 경보</dt>
            <dd>{counts.security}</dd>
          </div>
          <div>
            <dt>AI 보안</dt>
            <dd>{counts.aiSecurity}</dd>
          </div>
          <div>
            <dt>논문</dt>
            <dd>{counts.research}</dd>
          </div>
        </dl>
      </section>

      <section className="workspace" id="intelligence" aria-labelledby="intelligence-title">
        <div className="workspace-heading">
          <div>
            <p className="section-kicker">INTELLIGENCE FEED</p>
            <h2 id="intelligence-title">최신 수집 자료</h2>
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
          {FILTERS.map((item) => (
            <button
              key={item.value}
              type="button"
              className={classNames("filter-button", filter === item.value && "is-active")}
              aria-pressed={filter === item.value}
              onClick={() => setFilter(item.value)}
            >
              {item.label}
              <span>
                {item.value === "all"
                  ? data.items.length
                  : data.items.filter((entry) => entry.kind === item.value).length}
              </span>
            </button>
          ))}
        </div>

        <div className="intelligence-layout">
          <div className="feed" aria-live="polite">
            <div className="feed-meta">
              <span>{filteredItems.length}개 자료</span>
              <span>우선순위순</span>
            </div>

            {filteredItems.length ? (
              filteredItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={classNames(
                    "feed-card",
                    selectedItem?.id === item.id && "is-selected",
                  )}
                  onClick={() => setSelectedId(item.id)}
                  aria-pressed={selectedItem?.id === item.id}
                >
                  <span className="card-topline">
                    <span className={`kind-badge kind-${item.kind}`}>{KIND_LABELS[item.kind]}</span>
                    {item.severity && (
                      <span className={`severity severity-${item.severity}`}>
                        {item.severity.toUpperCase()}
                      </span>
                    )}
                    <time dateTime={item.publishedAt}>{formatDate(item.publishedAt)}</time>
                  </span>
                  <strong>{item.title}</strong>
                  <span className="card-summary">{item.summary}</span>
                  <span className="card-footer">
                    <span>{item.source}</span>
                    {item.identifier && <code>{item.identifier}</code>}
                    <span className="priority">P{item.priority}</span>
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
            {selectedItem ? (
              <article>
                <div className="detail-header">
                  <div className="detail-badges">
                    <span className={`kind-badge kind-${selectedItem.kind}`}>
                      {KIND_LABELS[selectedItem.kind]}
                    </span>
                    <span className="evidence-badge">
                      {EVIDENCE_LABELS[selectedItem.evidenceLevel]}
                    </span>
                  </div>
                  <span className="detail-priority">Priority {selectedItem.priority}</span>
                </div>

                <h3>{selectedItem.title}</h3>
                {selectedItem.originalTitle && (
                  <p className="original-title">{selectedItem.originalTitle}</p>
                )}

                <dl className="source-meta">
                  <div>
                    <dt>출처</dt>
                    <dd>{selectedItem.source}</dd>
                  </div>
                  <div>
                    <dt>{selectedItem.dateLabel ?? "게시일"}</dt>
                    <dd>{formatDate(selectedItem.publishedAt)}</dd>
                  </div>
                  {selectedItem.identifier && (
                    <div>
                      <dt>식별자</dt>
                      <dd>{selectedItem.identifier}</dd>
                    </div>
                  )}
                </dl>

                <section className="detail-section">
                  <h4>핵심 요약</h4>
                  <p>{selectedItem.summary}</p>
                </section>

                <section className="detail-section highlight-section">
                  <h4>왜 중요한가</h4>
                  <p>{selectedItem.whyItMatters}</p>
                </section>

                <section className="detail-section">
                  <h4>주요 내용</h4>
                  <ul>
                    {selectedItem.details.map((detail) => <li key={detail}>{detail}</li>)}
                  </ul>
                </section>

                {selectedItem.limitations?.length ? (
                  <section className="detail-section caution-section">
                    <h4>한계와 확인사항</h4>
                    <ul>
                      {selectedItem.limitations.map((limitation) => (
                        <li key={limitation}>{limitation}</li>
                      ))}
                    </ul>
                  </section>
                ) : null}

                {selectedItem.action && (
                  <section className="action-box">
                    <span>다음 행동</span>
                    <p>{selectedItem.action}</p>
                  </section>
                )}

                <div className="tag-list" aria-label="태그">
                  {selectedItem.tags.map((tag) => <span key={tag}>#{tag}</span>)}
                </div>

                <a
                  className="source-link"
                  href={selectedItem.sourceUrl}
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

      <section className="sources" id="sources" aria-labelledby="sources-title">
        <div>
          <p className="section-kicker">VERIFIED SOURCES</p>
          <h2 id="sources-title">공식 출처 중심으로 수집합니다.</h2>
        </div>
        <div className="source-grid">
          {["CISA KEV", "NIST NVD", "KISA KrCERT", "arXiv", "Semantic Scholar", "MITRE ATLAS", "OWASP GenAI", "공식 제품 권고"].map(
            (source) => <span key={source}>{source}</span>,
          )}
        </div>
      </section>

      <footer>
        <strong>Threat &amp; Thesis</strong>
        <p>Hermes Agent가 수집하고 GitHub Pages가 제공합니다.</p>
        <a href="#top">맨 위로 ↑</a>
      </footer>
    </main>
  );
}
