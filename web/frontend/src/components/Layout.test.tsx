import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./Layout";

function renderLayout(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<div>Home content</div>} />
          <Route path="/match" element={<div>Match content</div>} />
          <Route path="/beheer" element={<div>Beheer content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("Layout", () => {
  it("renders title and nav links", () => {
    renderLayout("/");
    expect(screen.getByText("Vacature Explorer")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Vacatures" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /CV-match/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Beheer/i })).toBeInTheDocument();
  });

  it("highlights active nav link on current route", () => {
    renderLayout("/match");
    const matchLink = screen.getByRole("link", { name: /CV-match/i, current: "page" });
    expect(matchLink.className).toContain("bg-primary");
  });
});
