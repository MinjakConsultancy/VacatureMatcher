import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchCvMatchLatest,
  fetchMotivatieLatest,
  fetchStats,
  setVacancyDismissed,
  startVervers,
} from "./client";

describe("api error handling", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("throws with response body on non-OK", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        text: async () => "Server error",
      })
    );

    await expect(fetchStats()).rejects.toThrow("Server error");
  });
});

describe("nullable endpoints", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetchCvMatchLatest returns null on 404", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 404 })
    );

    await expect(fetchCvMatchLatest()).resolves.toBeNull();
  });

  it("fetchMotivatieLatest returns null on 404", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 404 })
    );

    await expect(fetchMotivatieLatest("test-slug")).resolves.toBeNull();
  });
});

describe("mutations", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("setVacancyDismissed PATCHes correct URL and body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ slug: "foo" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await setVacancyDismissed("foo", true);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/vacancies/foo/dismiss",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ dismissed: true }),
      })
    );
  });

  it("startVervers POSTs sinds parameter", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "job-1", status: "queued" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await startVervers("gisteren");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/jobs/ververs",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ sinds: "gisteren", rebuild_index: true }),
      })
    );
  });
});
