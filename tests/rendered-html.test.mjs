import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("exports the Threat & Thesis research letter as static HTML", async () => {
  const html = await readFile(new URL("../out/index.html", import.meta.url), "utf8");
  assert.match(html, /<html[^>]*lang="ko"/i);
  assert.match(html, /<title>Threat &amp; Thesis<\/title>/i);
  assert.match(html, /데일리 보안·AI 순위/);
  assert.match(html, /오늘의 우선순위/);
  assert.match(html, /발행일 선택/);
  assert.match(html, /선정 이유/);
  assert.match(html, /유지/);
  assert.match(html, /OWASP/);
  assert.match(html, /보안 경보/);
  assert.match(html, /AI 보안/);
  assert.match(html, /최신 기술/);
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
  assert.match(page, /const FILTERS/);
  assert.match(page, /sourceUrl/);
  assert.match(layout, /title:\s*"Threat & Thesis"/);
  assert.match(content, /"evidenceLevel"/);
  assert.match(daily, /"previousRank"/);
  assert.match(daily, /"reason"/);
  assert.match(config, /output:\s*"export"/);
  assert.match(packageJson, /"build:pages": "next build"/);
  assert.match(packageJson, /"dev": "next dev"/);
  assert.doesNotMatch(packageJson, /vinext|wrangler|drizzle|cloudflare/i);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
});
