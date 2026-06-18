export type VacancyListItem = {
  slug: string;
  url: string;
  title: string;
  organisation?: string;
  location?: string;
  scale?: string;
  hours?: string;
  solliciteer_deadline?: string;
  status?: string;
  dismissed?: boolean;
  vakgebieden: string[];
};

export type VacancyDetail = VacancyListItem & {
  education?: string;
  kenmerk?: string;
  plaatsingsdatum?: string;
  summary?: string;
  contacts: { contact_type: string; name?: string; email?: string; phone?: string }[];
  sections: { section_type: string; text: string; sort_order: number }[];
};

export type Stats = { total: number; open_count: number; closed_count: number; last_scrape?: string };

export type Job = {
  id: string;
  job_type: string;
  status: string;
  params?: Record<string, unknown>;
  log_tail?: string;
  result?: Record<string, unknown>;
  created_at: string;
  finished_at?: string;
  queue_position?: number;
};

export type MatchResult = {
  slug: string;
  title: string;
  organisation: string;
  location: string;
  url: string;
  rag_score: number;
  keyword_score: number;
  section: string;
  snippet: string;
  solliciteer_deadline?: string;
};

const ADMIN_KEY = "vacature_admin_token";

export function getAdminToken(): string {
  return localStorage.getItem(ADMIN_KEY) || "";
}

export function setAdminToken(t: string) {
  localStorage.setItem(ADMIN_KEY, t);
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { ...(init?.headers as Record<string, string>) };
  const token = getAdminToken();
  if (token) headers["X-Admin-Token"] = token;
  const res = await fetch(path, { ...init, headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const fetchStats = () => api<Stats>("/api/stats");

export const fetchVacancies = (params: URLSearchParams) =>
  api<{ items: VacancyListItem[]; total: number; page: number; limit: number }>(
    `/api/vacancies?${params}`
  );

export const fetchVacancy = (slug: string) => api<VacancyDetail>(`/api/vacancies/${slug}`);

export const startVervers = (sinds: string) =>
  api<Job>("/api/jobs/ververs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sinds }),
  });

export const startMatch = (rebuild_index: boolean) =>
  api<Job>("/api/jobs/match", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rebuild_index }),
  });

export const fetchJob = (id: string) => api<Job>(`/api/jobs/${id}`);

export const fetchJobs = () => api<Job[]>("/api/jobs");

export const uploadCvMatch = async (
  file: File,
  opts: { location?: string; open_only: boolean; top_n: number }
) => {
  const fd = new FormData();
  fd.append("file", file);
  if (opts.location) fd.append("location", opts.location);
  fd.append("open_only", String(opts.open_only));
  fd.append("top_n", String(opts.top_n));
  const headers: Record<string, string> = {};
  const token = getAdminToken();
  if (token) headers["X-Admin-Token"] = token;
  const res = await fetch("/api/match/cv", { method: "POST", body: fd, headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Job>;
};

export const fetchCvMatch = (jobId: string) =>
  api<{ job_id: string; status: string; results: MatchResult[] }>(`/api/match/cv/${jobId}`);

export const fetchCvMatchLatest = async () => {
  const res = await fetch("/api/match/cv/latest");
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ job_id: string; status: string; results: MatchResult[] }>;
};

export const saveCvMatchJobId = (jobId: string) => {
  sessionStorage.setItem(CV_MATCH_JOB_KEY, jobId);
};

export const getSavedCvMatchJobId = () => sessionStorage.getItem(CV_MATCH_JOB_KEY);

export const setVacancyDismissed = (slug: string, dismissed: boolean) =>
  api<VacancyDetail>(`/api/vacancies/${slug}/dismiss`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dismissed }),
  });

export const fetchDismissedSlugs = () =>
  api<{ slugs: string[] }>("/api/vacancies/dismissed").then((r) => new Set(r.slugs));

export const fetchMotivatieStijlStatus = () => api<MotivatieStijlStatus>("/api/motivatie-stijl");

export const uploadMotivatieStijl = async (file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  const headers: Record<string, string> = {};
  const token = getAdminToken();
  if (token) headers["X-Admin-Token"] = token;
  const res = await fetch("/api/motivatie-stijl", { method: "POST", body: fd, headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<MotivatieStijlStatus>;
};

export type LlmStatus = { available: boolean; base_url: string; model?: string; models: string[] };
export type LlmLatest = { slug: string; text: string; model: string; job_id: string; created_at?: string; storage_key?: string };
export type LlmJob = {
  job_id: string;
  job_type: string;
  status: string;
  queue_position?: number;
  slug?: string;
  model?: string;
  text?: string;
  storage_key?: string;
  text_preview?: string;
  log_tail?: string;
  created_at?: string;
  finished_at?: string;
};
export type CvStatus = { has_cv: boolean; filename?: string; uploaded_at?: string };
export type MotivatieStijlStatus = { has_motivatie: boolean; filename?: string; uploaded_at?: string };

const CV_MATCH_JOB_KEY = "cv_match_job_id";

export const fetchLlmStatus = () => api<LlmStatus>("/api/llm/status");

export const fetchCvStatus = () => api<CvStatus>("/api/cv");

export const fetchLlmJob = (jobId: string) => api<LlmJob>(`/api/llm/jobs/${jobId}`);

export const fetchMotivatieLatest = async (slug: string): Promise<LlmLatest | null> => {
  const res = await fetch(`/api/llm/vacancies/${slug}/motivatie/latest`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};

export const fetchExplainLatest = async (slug: string): Promise<LlmLatest | null> => {
  const res = await fetch(`/api/llm/vacancies/${slug}/explain/latest`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};

export const startMotivatie = (slug: string, cv_kern = "") =>
  api<Job>(`/api/llm/vacancies/${slug}/motivatie`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cv_kern }),
  });

export const startExplain = (slug: string, cv_text = "") =>
  api<Job>(`/api/llm/vacancies/${slug}/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cv_text }),
  });
