import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { HomePage } from "./HomePage";
import { fetchVacancies, setVacancyDismissed } from "../api/client";

const fixture = {
  slug: "test-vac",
  url: "https://example.com/vac",
  title: "Test Vacature",
  organisation: "Test Org",
  location: "Den Haag",
  scale: "Schaal 11",
  vakgebieden: ["IT"],
};

vi.mock("../api/client", () => ({
  fetchStats: vi.fn().mockResolvedValue({ total: 1, open_count: 1, closed_count: 0 }),
  fetchVacancies: vi.fn(),
  setVacancyDismissed: vi.fn().mockResolvedValue({ slug: "test-vac" }),
}));

function renderHomePage() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>
  );
}

describe("HomePage", () => {
  beforeEach(() => {
    vi.mocked(fetchVacancies).mockResolvedValue({
      items: [fixture],
      total: 1,
      page: 1,
      limit: 50,
    });
  });

  it("shows loading while fetching", () => {
    vi.mocked(fetchVacancies).mockReturnValue(new Promise(() => {}));
    renderHomePage();
    expect(screen.getByText("Laden…")).toBeInTheDocument();
  });

  it("renders vacancy title and organisation after load", async () => {
    renderHomePage();
    await waitFor(() => {
      expect(screen.getByText("Test Vacature")).toBeInTheDocument();
    });
    expect(screen.getByText("Test Org")).toBeInTheDocument();
  });

  it("dismiss checkbox calls API and removes card", async () => {
    const user = userEvent.setup();
    renderHomePage();
    await waitFor(() => {
      expect(screen.getByText("Test Vacature")).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("Niet relevant"));

    expect(setVacancyDismissed).toHaveBeenCalledWith("test-vac", true);
    await waitFor(() => {
      expect(screen.queryByText("Test Vacature")).not.toBeInTheDocument();
    });
  });
});
