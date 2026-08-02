import type { ReactNode } from "react";

import {
  formatGlossaryPopup,
  glossaryTermKeys,
  lookupGlossary,
  type GlossaryEntry,
} from "../i18n/glossary";

type TermHintProps = {
  /** Glossary key or displayed abbreviation (e.g. "WBS", "SPI") */
  term: string;
  children?: ReactNode;
  className?: string;
};

export function TermHint({ term, children, className = "" }: TermHintProps) {
  const entry = lookupGlossary(term);
  if (!entry) {
    return <span className={className}>{children ?? term}</span>;
  }
  return (
    <span className={["term-hint", className].filter(Boolean).join(" ")}>
      <abbr
        className="term-hint__label"
        title={formatGlossaryPopup(entry)}
        aria-label={`${children ?? entry.label ?? term}: ${formatGlossaryPopup(entry)}`}
      >
        {children ?? entry.label ?? term}
      </abbr>
      <span className="term-hint__bubble" role="tooltip">
        {entry.full && <strong className="term-hint__full">{entry.full}</strong>}
        <span className="term-hint__text">{entry.hint}</span>
      </span>
    </span>
  );
}

type GlossaryTextProps = {
  text: string;
  className?: string;
};

/**
 * Annotate known Latin abbreviations inside a string (e.g. "CPM / EVM", "Кейсы CMMN").
 */
export function GlossaryText({ text, className = "" }: GlossaryTextProps) {
  const keys = glossaryTermKeys();
  if (!keys.length) {
    return <span className={className}>{text}</span>;
  }
  const pattern = new RegExp(
    `\\b(${keys.map(escapeRegExp).join("|")})\\b`,
    "gi",
  );
  const nodes: ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  let idx = 0;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) {
      nodes.push(text.slice(last, match.index));
    }
    const raw = match[1];
    const entry = lookupGlossary(raw);
    if (entry) {
      nodes.push(
        <TermHint key={`${match.index}-${idx}`} term={raw}>
          {raw}
        </TermHint>,
      );
    } else {
      nodes.push(raw);
    }
    last = match.index + raw.length;
    idx += 1;
  }
  if (last < text.length) {
    nodes.push(text.slice(last));
  }
  return <span className={className}>{nodes}</span>;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export type { GlossaryEntry };
