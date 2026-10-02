import type { ReactNode } from "react";

/**
 * Minimal block renderer for deliverable bodies. It produces React elements, so
 * nothing ever reaches dangerouslySetInnerHTML (coding-conventions §6): any
 * markup an agent emits renders as literal text.
 */
export function renderMarkdown(source: string): ReactNode[] {
  return source
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block, index) => {
      const [firstLine, ...rest] = block.split("\n");
      const heading = /^#{1,3}\s+(.*)$/.exec(firstLine ?? "");
      if (heading) {
        return (
          <div key={index} className="flex flex-col gap-1">
            <h4 className="text-h3 text-text">{heading[1]}</h4>
            {rest.length > 0 ? <p className="text-body text-text">{rest.join(" ")}</p> : null}
          </div>
        );
      }
      if (/^[-*]\s+/.test(block)) {
        return (
          <ul key={index} className="flex list-disc flex-col gap-0.5 pl-3 text-body text-text">
            {block.split("\n").map((line, line_index) => (
              <li key={line_index}>{line.replace(/^[-*]\s+/, "")}</li>
            ))}
          </ul>
        );
      }
      return (
        <p key={index} className="text-body text-text">
          {block}
        </p>
      );
    });
}
