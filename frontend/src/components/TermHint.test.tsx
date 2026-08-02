import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { GlossaryText, TermHint } from "./TermHint";
import { formatGlossaryPopup, lookupGlossary } from "../i18n/glossary";

describe("glossary", () => {
  it("looks up abbreviations case-insensitively", () => {
    const entry = lookupGlossary("wbs");
    expect(entry?.hint).toMatch(/структур/i);
    expect(formatGlossaryPopup(entry!).toLowerCase()).toContain("work breakdown");
  });

  it("renders TermHint bubble content for known terms", () => {
    render(<TermHint term="SPI">SPI</TermHint>);
    expect(screen.getByText("SPI")).toBeInTheDocument();
    expect(screen.getByText(/индекс выполнения сроков/i)).toBeInTheDocument();
  });

  it("annotates mixed labels via GlossaryText", () => {
    render(<GlossaryText text="CPM / EVM" />);
    expect(screen.getByText("CPM")).toBeInTheDocument();
    expect(screen.getByText("EVM")).toBeInTheDocument();
    expect(screen.getByText(/критического пути/i)).toBeInTheDocument();
    expect(screen.getByText(/освоенным объёмом/i)).toBeInTheDocument();
  });
});
