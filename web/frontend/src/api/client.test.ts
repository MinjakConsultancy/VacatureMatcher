import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchCvMatchLatest,
  fetchMotivatieLatest,
  fetchStats,
  getAdminToken,
  setAdminToken,
  setVacancyDismissed,
  startVervers,
} from "./client";

describe("admin token", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("stores and retrieves admin token", () => {
    expect(getAdminToken()).toBe("");
    setAdminToken("secret");
    expect(getAdminToken()).toBe("secret");
  });

  it("sends X-Admin-Token header when set", async () => {
    setAdminToken("secret");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ total: 1, open_count: 1, closed_count: 0 }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchStats();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/stats",
      expect.objectContaining({
        headers: expect.objectContaining({ "X-Admin-Token": "secret" }),
      })
    );
  });
});

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
        body: JSON.stringify({ sinds: "gisteren" }),
      })
    );
  });
});
