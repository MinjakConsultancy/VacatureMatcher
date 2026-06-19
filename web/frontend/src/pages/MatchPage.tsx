import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchCvMatch,
  fetchCvMatchLatest,
  fetchCvStatus,
  fetchDismissedSlugs,
  fetchLlmJob,
  fetchMotivatieStijlStatus,
  getSavedCvMatchJobId,
  MatchResult,
  saveCvMatchJobId,
  setVacancyDismissed,
  startExplain,
  uploadCvMatch,
  uploadMotivatieStijl,
} from "../api/client";
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Progress } from "../components/ui";
import { FileUploadZone } from "../components/FileUploadZone";
import { formatDate } from "../lib/utils";
import { MessageSquare, Info } from "lucide-react";

type ExplainState = {
  jobId: string;
  status: string;
  queuePosition?: number;
  text?: string;
  model?: string;
  error?: string;
};

function jobStatusLabel(status: string, queuePosition?: number) {
  if (status === "queued" && queuePosition) return `Wachtrij ${queuePosition}`;
  if (status === "queued") return "Wachtrij…";
  if (status === "running") return "Bezig…";
  return status;
}

export function MatchPage() {
  const [file, setFile] = useState<File | null>(null);
  const [motivatieFile, setMotivatieFile] = useState<File | null>(null);
  const [location, setLocation] = useState("Den Haag");
  const [openOnly, setOpenOnly] = useState(true);
  const [topN, setTopN] = useState(30);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [results, setResults] = useState<MatchResult[]>([]);
  const [error, setError] = useState("");
  const [cvSaved, setCvSaved] = useState(false);
  const [motivatieSaved, setMotivatieSaved] = useState(false);
  const [motivatieFilename, setMotivatieFilename] = useState<string | null>(null);
  const [explains, setExplains] = useState<Record<string, ExplainState>>({});
  const [openExplain, setOpenExplain] = useState<string | null>(null);
  const [dismissedSlugs, setDismissedSlugs] = useState<Set<string>>(new Set());

  const applyResults = (list: MatchResult[], dismissed: Set<string>) => {
    setResults(list.filter((r) => !dismissed.has(r.slug)));
  };

  useEffect(() => {
    fetchCvStatus()
      .then((s) => setCvSaved(s.has_cv))
      .catch(() => {});
    fetchMotivatieStijlStatus()
      .then((s) => {
        setMotivatieSaved(s.has_motivatie);
        setMotivatieFilename(s.filename || null);
      })
      .catch(() => {});

    const restore = async () => {
      let dismissed = new Set<string>();
      try {
        dismissed = await fetchDismissedSlugs();
        setDismissedSlugs(dismissed);
      } catch {
        /* tabel mogelijk nog niet gemigreerd */
      }

      const savedId = getSavedCvMatchJobId();
      const tryId = async (id: string) => {
        const r = await fetchCvMatch(id);
        setJobId(id);
        setStatus(r.status);
        if (r.status === "done") applyResults(r.results, dismissed);
      };
      try {
        const latest = await fetchCvMatchLatest();
        if (latest) {
          saveCvMatchJobId(latest.job_id);
          setJobId(latest.job_id);
          setStatus(latest.status);
          if (latest.status === "done") applyResults(latest.results, dismissed);
          return;
        }
      } catch {
        /* geen latest */
      }
      if (savedId) {
        try {
          await tryId(savedId);
        } catch {
          /* verlopen job */
        }
      }
    };
    restore();
  }, []);

  useEffect(() => {
    if (!jobId || status === "done" || status === "failed") return;
    const t = setInterval(() => {
      fetchCvMatch(jobId).then((r) => {
        setStatus(r.status);
        if (r.status === "done") applyResults(r.results, dismissedSlugs);
      });
    }, 2000);
    return () => clearInterval(t);
  }, [jobId, status, dismissedSlugs]);

  useEffect(() => {
    const active = Object.entries(explains).filter(
      ([, e]) => e.status === "queued" || e.status === "running"
    );
    if (!active.length) return;
    const t = setInterval(() => {
      active.forEach(([slug, e]) => {
        fetchLlmJob(e.jobId).then((j) => {
          setExplains((prev) => ({
            ...prev,
            [slug]: {
              ...prev[slug],
              status: j.status,
              queuePosition: j.queue_position,
              text: j.text,
              model: j.model,
              error: j.status === "failed" ? j.log_tail || "Mislukt" : undefined,
            },
          }));
        });
      });
    }, 2000);
    return () => clearInterval(t);
  }, [explains]);

  const submit = async () => {
    if (!file) return;
    setError("");
    setResults([]);
    try {
      const job = await uploadCvMatch(file, { location: location || undefined, open_only: openOnly, top_n: topN });
      setJobId(job.id);
      setStatus(job.status);
      setCvSaved(true);
      saveCvMatchJobId(job.id);
    } catch (e) {
      setError(String(e));
    }
  };

  const submitMotivatieStijl = async () => {
    if (!motivatieFile) return;
    setError("");
    try {
      const s = await uploadMotivatieStijl(motivatieFile);
      setMotivatieSaved(s.has_motivatie);
      setMotivatieFilename(s.filename || motivatieFile.name);
    } catch (e) {
      setError(String(e));
    }
  };

  const onDismissToggle = async (slug: string, dismissed: boolean) => {
    await setVacancyDismissed(slug, dismissed);
    setDismissedSlugs((prev) => {
      const next = new Set(prev);
      if (dismissed) next.add(slug);
      else next.delete(slug);
      return next;
    });
    if (dismissed) {
      setResults((prev) => prev.filter((r) => r.slug !== slug));
    }
  };

  const onExplain = async (slug: string) => {
    setOpenExplain(slug);
    try {
      const job = await startExplain(slug);
      setExplains((prev) => ({
        ...prev,
        [slug]: { jobId: job.id, status: job.status, queuePosition: job.queue_position },
      }));
    } catch (e) {
      setExplains((prev) => ({
        ...prev,
        [slug]: { jobId: "", status: "failed", error: String(e) },
      }));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">CV-match</h1>
        <Link to="/match/uitleg" className="text-sm text-primary flex items-center gap-1 hover:underline">
          <Info className="h-4 w-4" />
          Hoe werken de scores?
        </Link>
      </div>

      <Card>
        <CardHeader><CardTitle>Upload CV (.docx of .txt)</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Dit CV wordt opgeslagen op MinIO en gebruikt voor motivatiebrieven op vacaturepagina&apos;s.
            Match gebruikt de huidige RAG-index. Na nieuwe vacatures: Beheer → Data verversen
            (laat &apos;RAG-index herbouwen&apos; aangevinkt).
          </p>
          <FileUploadZone file={file} onFileChange={setFile} />

          <div className="flex flex-wrap gap-3">
            <Input placeholder="Locatie filter" value={location} onChange={(e) => setLocation(e.target.value)} className="max-w-xs" />
            <Input type="number" value={topN} onChange={(e) => setTopN(Number(e.target.value))} className="max-w-[100px]" />
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={openOnly} onChange={(e) => setOpenOnly(e.target.checked)} />
              Alleen open
            </label>
          </div>

          <Button onClick={submit} disabled={!file || (status === "running" || status === "queued")}>
            CV uploaden en matchen
          </Button>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          {cvSaved && (
            <p className="text-sm text-green-700">CV opgeslagen als actief profiel voor motivatiebrieven.</p>
          )}
          {jobId && status !== "done" && status !== "failed" && (
            <p className="text-sm text-muted-foreground">Job {status}…</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Referentie-motivatiebrief (optioneel)</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Upload een bestaande motivatiebrief als stijlvoorbeeld voor gegenereerde brieven.
          </p>
          <FileUploadZone file={motivatieFile} onFileChange={setMotivatieFile} />
          <Button onClick={submitMotivatieStijl} disabled={!motivatieFile}>
            Stijlvoorbeeld opslaan
          </Button>
          {motivatieSaved && (
            <p className="text-sm text-green-700">
              Stijlvoorbeeld actief{motivatieFilename ? `: ${motivatieFilename}` : ""}.
            </p>
          )}
        </CardContent>
      </Card>

      {results.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Resultaten ({results.length})</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {results.map((r, i) => {
              const ex = explains[r.slug];
              const busy = ex?.status === "queued" || ex?.status === "running";
              return (
                <div key={r.slug} className={`p-4 rounded-lg border ${i === 0 ? "border-primary bg-primary/5" : "border-border"}`}>
                  <div className="flex justify-between gap-2 flex-wrap">
                    <Link to={`/vacatures/${r.slug}`} className="font-semibold hover:text-primary">{r.title}</Link>
                    <span className="text-sm text-muted-foreground">#{i + 1}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">{r.organisation} · {r.location}</p>
                  <p className="text-xs text-muted-foreground mt-1">Deadline: {formatDate(r.solliciteer_deadline)}</p>
                  <div className="mt-3 space-y-1">
                    <div className="flex justify-between text-xs"><span>RAG</span><span>{r.rag_score.toFixed(3)}</span></div>
                    <Progress value={r.rag_score} />
                    <div className="flex justify-between text-xs"><span>Keywords</span><span>{r.keyword_score.toFixed(1)}</span></div>
                    <Progress value={Math.min(1, r.keyword_score / 30)} />
                  </div>
                  <p className="text-xs mt-2 text-muted-foreground line-clamp-2">{r.snippet}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      className="h-8 text-xs px-3"
                      onClick={() => onExplain(r.slug)}
                      disabled={busy}
                    >
                      <MessageSquare className="h-3 w-3 mr-1" />
                      {busy ? jobStatusLabel(ex.status, ex.queuePosition) : "Uitleg"}
                    </Button>
                    <label className="flex items-center gap-1 text-xs cursor-pointer">
                      <input
                        type="checkbox"
                        checked={dismissedSlugs.has(r.slug)}
                        onChange={(e) => onDismissToggle(r.slug, e.target.checked)}
                      />
                      Niet relevant
                    </label>
                  </div>
                  {(openExplain === r.slug || ex?.text) && ex && (
                    <div className="mt-3 p-3 bg-muted/50 rounded-md text-sm whitespace-pre-wrap">
                      {ex.error && <p className="text-destructive">{ex.error}</p>}
                      {ex.text && (
                        <>
                          {ex.model && <p className="text-xs text-muted-foreground mb-1">Model: {ex.model}</p>}
                          <p>{ex.text}</p>
                        </>
                      )}
                      {!ex.text && !ex.error && busy && (
                        <p className="text-muted-foreground">{jobStatusLabel(ex.status, ex.queuePosition)}</p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
