import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("exports the Threat & Thesis research letter as static HTML", async () => {
  const html = await readFile(new URL("../out/index.html", import.meta.url), "utf8");
  assert.match(html, /<html[^>]*lang="ko"/i);
  assert.match(html, /<title>Threat &amp; Thesis<\/title>/i);
  assert.match(html, /<h1[^>]*>보안 위협/);
  assert.match(html, /카테고리 순위/);
  assert.match(html, /발행일 선택/);
  assert.match(html, /오늘 새로 공개된 자료만/);
  assert.match(html, /Google Project Zero/);
  assert.match(html, /IACR Cryptology ePrint/);
  assert.match(html, /<h3[^>]*>영향<\/h3>/);
  assert.match(html, /선정 이유/);
  assert.match(html, /신규/);
  assert.doesNotMatch(html, /유지|상승|하락|재진입/);
  assert.match(html, /CISA/);
  assert.match(html, /보안 위협/);
  assert.match(html, /AI 보안/);
  assert.match(html, /보안 논문/);
  assert.match(html, /AI 논문/);
  assert.match(html, /최신 기술/);
  assert.match(html, /<h2[^>]*>출처<\/h2>/);
  assert.doesNotMatch(html, /확인하는 출처/);
  assert.doesNotMatch(html, /정부·표준기관, 논문 원문과 공식 제품 권고를 우선합니다/);
  assert.doesNotMatch(html, /데일리 보안·AI 순위/);
  assert.doesNotMatch(html, /보안 경보/);
  assert.doesNotMatch(html, /왜 중요한가/);
  assert.doesNotMatch(html, /href="#intelligence"/);
  assert.doesNotMatch(html, /우선순위 99/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/i);
});

test("keeps content, UI, and build configuration wired together", async () => {
  const [page, layout, packageJson, content, daily, config] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
    readFile(new URL("../content/articles.json", import.meta.url), "utf8"),
    readFile(new URL("../content/daily/index.json", import.meta.url), "utf8"),
    readFile(new URL("../next.config.ts", import.meta.url), "utf8"),
  ]);

  assert.match(page, /content\/articles\.json/);
  assert.match(page, /content\/daily\/index\.json/);
  assert.match(page, /const CATEGORIES/);
  assert.doesNotMatch(page, /value: "all"/);
  assert.match(page, /sourceUrl/);
  assert.match(page, /requiresLibraryAccess/);
  assert.match(page, /SKKU 원문 확인/);
  assert.match(page, /lib\.skku\.edu\/nsc\/proxy-link/);
  assert.match(layout, /title:\s*"Threat & Thesis"/);
  assert.match(content, /"evidenceLevel"/);
  assert.match(daily, /"previousRank"/);
  assert.match(daily, /"reason"/);
  const dailyPayload = JSON.parse(daily);
  assert.equal(dailyPayload.editions[0].selectionMode, "new-only");
  for (const category of [
    "security",
    "ai-security",
    "security-paper",
    "ai-paper",
    "technology",
  ]) {
    const ranks = dailyPayload.editions[0].rankings[category].map(({ rank }) => rank);
    assert.ok(ranks.length <= 10);
    assert.deepEqual(
      ranks,
      Array.from({ length: ranks.length }, (_, index) => index + 1),
    );
  }
  assert.match(config, /output:\s*"export"/);
  assert.match(packageJson, /"build:pages": "next build"/);
  assert.match(packageJson, /"dev": "next dev"/);
  assert.doesNotMatch(packageJson, /vinext|wrangler|drizzle|cloudflare/i);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
});
