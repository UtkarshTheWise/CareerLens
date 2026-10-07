"use client";
import { Highlight, Prism, type PrismTheme } from "prism-react-renderer";
import type { Schema } from "@/components/career/shared";
const theme: PrismTheme = {
  plain: { color: "var(--text)", backgroundColor: "var(--surface-2)" },
  styles: [
    {
      types: ["comment", "prolog", "doctype"],
      style: { color: "var(--muted-readable)" },
    },
    {
      types: ["keyword", "boolean", "operator"],
      style: { color: "var(--primary-text)" },
    },
    {
      types: ["string", "char", "attr-value"],
      style: { color: "var(--success-readable)" },
    },
    {
      types: ["number", "function", "class-name"],
      style: { color: "var(--code-warm)" },
    },
  ],
};
export function CodeSnippet({
  snippet,
}: {
  snippet: NonNullable<Schema["QuizQuestion"]["code_snippet"]>;
}) {
  const requested = snippet.language?.toLowerCase() || "plain";
  const aliases: Record<string, string> = {
    py: "python",
    js: "javascript",
    ts: "typescript",
    shell: "bash",
    sh: "bash",
  };
  const language = aliases[requested] || requested;
  return (
    <figure className="min-w-0 rounded-control border border-border bg-surface-2">
      <figcaption className="break-anywhere border-b border-border px-4 py-3 text-xs text-muted-readable">
        {snippet.path} · lines {snippet.start_line}–{snippet.end_line}
      </figcaption>
      <Highlight
        code={snippet.code}
        language={Prism.languages[language] ? language : "plain"}
        theme={theme}
      >
        {({ tokens, getTokenProps }) => (
          <pre
            tabIndex={0}
            aria-label={`Code from ${snippet.path}, lines ${snippet.start_line} to ${snippet.end_line}`}
            className="max-h-96 overflow-auto p-4 font-mono text-xs leading-6 focus-visible:outline-2 focus-visible:outline-primary"
          >
            <code>
              {tokens.map((line, index) => (
                <span key={index} className="flex min-w-max">
                  <span
                    aria-hidden="true"
                    className="mr-4 inline-block w-8 shrink-0 select-none text-right text-muted-readable"
                  >
                    {snippet.start_line + index}
                  </span>
                  <span>
                    {line.map((token, key) => (
                      <span key={key} {...getTokenProps({ token })} />
                    ))}
                    {"\n"}
                  </span>
                </span>
              ))}
            </code>
          </pre>
        )}
      </Highlight>
    </figure>
  );
}
