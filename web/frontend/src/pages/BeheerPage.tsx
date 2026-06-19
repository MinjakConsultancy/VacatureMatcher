import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  fetchJobs,
  fetchJob,
  startVervers,
  Job,
} from "../api/client";
import { Button, Card, CardContent, CardHeader, CardTitle, Select } from "../components/ui";

const LLM_JOB_TYPES = new Set(["llm_motivatie", "llm_explain"]);

const JOB_TYPE_LABELS: Record<string, string> = {
  ververs: "Data verversen",
  match: "RAG-index",
  cv_match: "CV-match",
  llm_motivatie: "Motivatiebrief",
  llm_explain: "Match-uitleg",
};

function jobTypeLabel(jobType: string): string {
  return JOB_TYPE_LABELS[jobType] ?? jobType;
}

function vacancySlugFromJob(job: Job): string | null {
  if (!LLM_JOB_TYPES.has(job.job_type)) return null;
  const fromParams = job.params?.slug;
  if (typeof fromParams === "string" && fromParams) return fromParams;
  const fromResult = job.result?.slug;
  if (typeof fromResult === "string" && fromResult) return fromResult;
  return null;
}

export function BeheerPage() {
  const [sinds, setSinds] = useState("5d");
  const [rebuildIndex, setRebuildIndex] = useState(true);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [error, setError] = useState("");

  const refresh = () => fetchJobs().then(setJobs).catch((e) => setError(String(e)));

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (!activeJob || activeJob.status === "done" || activeJob.status === "failed") return;
    const t = setInterval(() => {
      fetchJob(activeJob.id).then((j) => {
        setActiveJob(j);
        if (j.status === "done" || j.status === "failed") refresh();
      });
    }, 2000);
    return () => clearInterval(t);
  }, [activeJob]);

  const runVervers = async () => {
    try {
      const j = await startVervers(sinds, rebuildIndex);
      setActiveJob(j);
      refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Beheer</h1>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <Card className="max-w-xl">
        <CardHeader><CardTitle>Data verversen</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <Select value={sinds} onChange={(e) => setSinds(e.target.value)}>
            <option value="gisteren">Gisteren</option>
            <option value="3d">3 dagen</option>
            <option value="5d">5 dagen</option>
            <option value="7d">7 dagen</option>
            <option value="1maand">1 maand</option>
            <option value="all">Alles (geen datumfilter)</option>
          </Select>
          <p className="text-xs text-muted-foreground">
            Bron: IkWerk (met inlog) of Werkenbijdeoverheid (zonder inlog, automatisch).
            Bij sinds=all kan een WbO-run lang duren (duizenden vacatures).
          </p>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={rebuildIndex}
              onChange={(e) => setRebuildIndex(e.target.checked)}
            />
            RAG-index herbouwen na ververs
          </label>
          <p className="text-xs text-muted-foreground">
            Nodig voor actuele CV-match scores na nieuwe vacatures. Vink uit als je alleen data wilt ophalen.
          </p>
          <Button onClick={runVervers}>Start ververs</Button>
        </CardContent>
      </Card>

      {activeJob && (
        <Card>
          <CardHeader>
            <CardTitle>
              Actieve job: {jobTypeLabel(activeJob.job_type)} — {activeJob.status}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-muted p-3 rounded-md max-h-64 overflow-auto whitespace-pre-wrap">
              {activeJob.log_tail || "Wachten op output…"}
            </pre>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle>Job-historie</CardTitle></CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted-foreground border-b">
                <th className="pb-2">Type</th>
                <th className="pb-2">Vacature</th>
                <th>Status</th>
                <th>Gestart</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => {
                const slug = vacancySlugFromJob(j);
                return (
                <tr key={j.id} className="border-b border-border/50">
                  <td className="py-2">{jobTypeLabel(j.job_type)}</td>
                  <td className="py-2">
                    {slug ? (
                      <Link to={`/vacatures/${slug}`} className="text-primary hover:underline">
                        {slug}
                      </Link>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                  <td>{j.status}</td>
                  <td>{new Date(j.created_at).toLocaleString("nl-NL")}</td>
                </tr>
              );
              })}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
