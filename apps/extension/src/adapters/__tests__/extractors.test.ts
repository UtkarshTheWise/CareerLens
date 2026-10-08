import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { JSDOM } from "jsdom";
import { extractPosting } from "../index";
import { jsonld } from "../jsonld";
import { dateOnly, pageEligibility } from "../shared";
import { validateSettings, defaults } from "../../settings";
const doc = (html: string, url = "https://example.com/jobs/1") =>
  new JSDOM(html, { url }).window.document;
const fixture = (name: string) =>
  readFileSync(
    new URL("./fixtures/" + name + ".html", import.meta.url),
    "utf8",
  );
test("nested JSON-LD wins over DOM; bad script ignored, HTML removed", () => {
  const posting = extractPosting(
    doc(fixture("jsonld")),
    "https://example.com/jobs/1",
  );
  assert.equal(posting.source, "jsonld");
  assert.equal(posting.title, "Frontend Engineer");
  assert.equal(posting.company, "Fixture Co");
  assert.equal(posting.location, "Pune, MH, IN");
  assert.equal(posting.description, "Build accessible React interfaces.");
  assert.equal(posting.deadline, "2026-12-31");
});
test("top-level arrays and schema type URL accepted", () => {
  const posting = jsonld(
    doc(
      '<script type="application/ld+json">[{"@type":"https://schema.org/JobPosting","title":"Developer","description":"Work on services"}]</script>',
    ),
    "https://example.com/jobs/1",
  );
  assert.equal(posting?.title, "Developer");
});
test("multiple jobs prefer exact current URL", () => {
  const jobs = [
    {
      "@type": "JobPosting",
      title: "Wrong",
      description: "A",
      url: "https://example.com/jobs/2",
    },
    {
      "@type": "JobPosting",
      title: "Current",
      description: "B",
      url: "https://example.com/jobs/1",
    },
  ];
  assert.equal(
    jsonld(
      doc(
        '<script type="application/ld+json">' +
          JSON.stringify(jobs) +
          "</script>",
      ),
      "https://example.com/jobs/1",
    )?.title,
    "Current",
  );
});
for (const [site, url, title, company] of [
  [
    "greenhouse",
    "https://boards.greenhouse.io/fixture/jobs/1",
    "Software Engineer",
    "Synthetic Greenhouse Co",
  ],
  [
    "lever",
    "https://jobs.lever.co/fixture/1",
    "Platform Engineer",
    "Synthetic Lever Co",
  ],
  [
    "linkedin",
    "https://www.linkedin.com/jobs/view/1",
    "Product Engineer",
    "Synthetic LinkedIn Co",
  ],
])
  test(site + " saved job HTML extraction", () => {
    const posting = extractPosting(doc(fixture(site), url), url);
    assert.equal(posting.title, title);
    assert.equal(posting.company, company);
    assert.equal(posting.source, "dom");
    assert.ok(posting.description);
    assert.doesNotMatch(posting.description, /personal data|navigation/);
  });
for (const [site, url, html, title] of [
  [
    "workday",
    "https://fixture.myworkdayjobs.com/job/1",
    '<h1 data-automation-id="jobPostingHeader">Analyst</h1><div data-automation-id="jobPostingDescription">Analyse systems.</div>',
    "Analyst",
  ],
  [
    "naukri",
    "https://www.naukri.com/job-listings/1",
    '<h1 class="jd-header-title">Developer</h1><div class="job-desc-container">Build systems.</div>',
    "Developer",
  ],
  [
    "generic",
    "https://example.com/jobs/1",
    '<h1>Designer</h1><div class="job-description">Design systems.</div>',
    "Designer",
  ],
])
  test(site + " DOM adapter", () => {
    const posting = extractPosting(doc(html, url), url);
    assert.equal(posting.title, title);
    assert.equal(posting.source, "dom");
    assert.equal(posting.company, null);
  });
test("visible fallback excludes hidden/UI/script and does not infer fields", () => {
  const posting = extractPosting(
    doc(
      '<title>Current role</title><nav>Private menu</nav><main><p>Actual job text</p><p style="display:none">secret</p><span aria-hidden="true">secret</span><script>secret</script><button>Apply</button></main>',
    ),
    "https://example.com/jobs/1",
  );
  assert.equal(posting.source, "llm");
  assert.equal(posting.description, "Actual job text");
  assert.equal(posting.company, null);
  assert.equal(posting.location, null);
  assert.equal(posting.required_skills, undefined);
});
test("DOM/fallback descriptions capped at 20k", () => {
  for (const html of [
    '<h1>Role</h1><div class="job-description">' + "x".repeat(25000) + "</div>",
    "<main>" + "x".repeat(25000) + "</main>",
  ])
    assert.equal(
      extractPosting(doc(html), "https://example.com/jobs/1").description
        .length,
      20000,
    );
});
test("JSON-LD description capped at 20k", () =>
  assert.equal(
    jsonld(
      doc(
        '<script type="application/ld+json">' +
          JSON.stringify({
            "@type": "JobPosting",
            title: "Role",
            description: "x".repeat(25000),
          }) +
          "</script>",
      ),
      "https://example.com/jobs/1",
    )?.description.length,
    20000,
  ));
test("LinkedIn profiles rejected before any document read", () => {
  const unreadable = new Proxy(
    {},
    {
      get() {
        throw new Error("DOM WAS READ");
      },
    },
  ) as Document;
  assert.throws(
    () => extractPosting(unreadable, "https://www.linkedin.com/in/fixture"),
    /Profile pages are never read/,
  );
  assert.equal(pageEligibility("https://www.linkedin.com/jobs/view/1"), null);
});
test("restricted protocols and credential-bearing URLs rejected", () => {
  for (const url of [
    "chrome://settings",
    "file:///private",
    "https://user:pass@example.com/jobs/1",
  ])
    assert.ok(pageEligibility(url));
});
test("empty visible page reports error", () =>
  assert.throws(
    () =>
      extractPosting(
        doc("<main hidden>Invisible</main>"),
        "https://example.com/jobs/1",
      ),
    /No visible job text/,
  ));
test("invalid structured job falls back to actual DOM", () => {
  const posting = extractPosting(
    doc(
      '<script type="application/ld+json">{"@type":"JobPosting","title":"Incomplete"}</script><h1>Actual</h1><div class="job-description">Visible description</div>',
    ),
    "https://example.com/jobs/1",
  );
  assert.equal(posting.title, "Actual");
  assert.equal(posting.source, "dom");
});
test("calendar dates validated without rollover", () => {
  assert.equal(dateOnly("2026-02-30"), null);
  assert.equal(dateOnly("2026-02-28T12:00:00Z"), "2026-02-28");
  assert.equal(dateOnly(null), null);
});
test("settings accept normalized URL and profile UUID", () => {
  assert.equal(
    validateSettings({ ...defaults, apiUrl: " http://localhost:8000/ " })
      .apiUrl,
    "http://localhost:8000",
  );
  assert.equal(
    validateSettings({
      ...defaults,
      profileId: "3f2b8c1e-5d47-4a9b-8e21-7c6a0f9d1b34",
    }).profileId,
    "3f2b8c1e-5d47-4a9b-8e21-7c6a0f9d1b34",
  );
});
test("settings reject keys/invalid profile/non-HTTP", () => {
  for (const apiUrl of [
    "file:///private",
    "https://user:pass@example.com",
    "https://example.com?key=secret",
  ])
    assert.throws(() => validateSettings({ ...defaults, apiUrl }));
  assert.throws(() => validateSettings({ ...defaults, profileId: "invalid" }));
});

test("LinkedIn listings/expired redirects rejected; selected SPA jobs allowed", () => {
  assert.ok(
    pageEligibility("https://www.linkedin.com/jobs/software-engineer-jobs"),
  );
  assert.equal(
    pageEligibility(
      "https://www.linkedin.com/jobs/search/?currentJobId=4470982992",
    ),
    null,
  );
});
