import assert from "node:assert/strict";
import { test } from "node:test";
import {
  fileError,
  MAX_DOCUMENT_BYTES,
  portfolioUrls,
  validateStep,
  type WizardValues,
} from "../lib/onboarding";
const values: WizardValues = {
  name: "Synthetic Student",
  resume: new File(["resume text"], "resume.pdf"),
  linkedinMode: "none",
  linkedinFile: null,
  linkedinText: "",
  github: "",
  portfolios: "",
  role: "sde-backend",
};
test("document boundary: 5 MB accepted; oversized, empty and legacy formats rejected", () => {
  assert.equal(
    fileError(
      new File([new Uint8Array(MAX_DOCUMENT_BYTES)], "resume.DOCX"),
      "resume",
    ),
    undefined,
  );
  assert.match(
    fileError(
      new File([new Uint8Array(MAX_DOCUMENT_BYTES + 1)], "resume.pdf"),
      "resume",
    )!,
    /exceeds 5 MB/,
  );
  assert.match(fileError(new File([], "resume.pdf"), "resume")!, /empty/);
  assert.match(
    fileError(new File(["text"], "resume.doc"), "resume")!,
    /PDF or DOCX/,
  );
  assert.match(
    fileError(new File(["text"], "linkedin.docx"), "linkedin")!,
    /PDF export/,
  );
});
test("first step requires name and resume and validates only selected LinkedIn source", () => {
  assert.deepEqual(validateStep(values, 0), {});
  assert.deepEqual(
    Object.keys(validateStep({ ...values, name: "  ", resume: null }, 0)),
    ["name", "resume"],
  );
  assert.ok(
    validateStep({ ...values, linkedinMode: "text", linkedinText: " " }, 0)
      .linkedinText,
  );
  assert.ok(validateStep({ ...values, linkedinMode: "pdf" }, 0).linkedinFile);
  assert.deepEqual(
    validateStep(
      {
        ...values,
        linkedinMode: "none",
        linkedinFile: new File([], "bad.exe"),
      },
      0,
    ),
    {},
  );
});
test("GitHub accepts optional username but rejects URLs and malformed boundaries", () => {
  for (const github of ["", "a", "a-b", "a".repeat(39)])
    assert.equal(validateStep({ ...values, github }, 1).github, undefined);
  for (const github of [
    "https://github.com/demo",
    "-demo",
    "demo-",
    "demo--name",
    "a".repeat(40),
  ])
    assert.ok(validateStep({ ...values, github }, 1).github);
});
test("portfolio links preserve full URLs while rejecting executable schemes and credentials", () => {
  const portfolios =
    "  https://example.com/portfolio?q=a#work\r\n\nhttps://www.figma.com/design/demo\n";
  assert.equal(portfolioUrls(portfolios).length, 2);
  assert.equal(
    validateStep({ ...values, portfolios }, 1).portfolios,
    undefined,
  );
  for (const portfolios of [
    "javascript:alert(1)",
    "ftp://example.com",
    "example.com",
    "https://user:password@example.com",
    "https://good.example\ninvalid",
  ])
    assert.ok(validateStep({ ...values, portfolios }, 1).portfolios);
});
test("role must be supplied by the current catalogue", () => {
  assert.deepEqual(validateStep(values, 2, ["sde-backend"]), {});
  assert.ok(validateStep(values, 2, []).role);
  assert.ok(
    validateStep({ ...values, role: "invented-role" }, 2, ["sde-backend"]).role,
  );
});
