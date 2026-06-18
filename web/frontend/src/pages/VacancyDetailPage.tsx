import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  fetchCvStatus,
  fetchExplainLatest,
  fetchLlmJob,
  fetchLlmStatus,
  fetchMotivatieLatest,
  fetchVacancy,
  setVacancyDismissed,
  startExplain,
  startMotivatie,
  VacancyDetail,
} from "../api/client";
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from "../components/ui";
import { deadlineBadgeClass, formatDate } from "../lib/utils";
import { ArrowLeft, ExternalLink, Sparkles } from "lucide-react";

function jobStatusLabel(status: string, queuePosition?: number) {
  if (status === "queued" && queuePosition) return `Wachtrij positie ${queuePosition}`;
  if (status === "queued") return "In wachtrij";
  if (status === "running") return "Bezig…";
  if (status === "done") return "Klaar";
  if (status === "failed") return "Mislukt";
  return status;
}

export function VacancyDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [v, setV] = useState<VacancyDetail | null>(null);
  const [tab, setTab] = useState<"sections" | "vakgebied" | "contact" | "motivatie">("sections");
  const [llmOk, setLlmOk] = useState<boolean | null>(null);
  const [motivatie, setMotivatie] = useState("");
  const [motivatieModel, setMotivatieModel] = useState("");
  const [motivatieJobId, setMotivatieJobId] = useState<string | null>(null);
  const [motivatieStatus, setMotivatieStatus] = useState("");
  const [motivatieQueue, setMotivatieQueue] = useState<number | undefined>();
  const [motivatieError, setMotivatieError] = useState("");
  const [explain, setExplain] = useState("");
  const [explainModel, setExplainModel] = useState("");
  const [explainJobId, setExplainJobId] = useState<string | null>(null);
  const [explainStatus, setExplainStatus] = useState("");
  const [explainQueue, setExplainQueue] = useState<number | undefined>();
  const [explainError, setExplainError] = useState("");
  const [cvReady, setCvReady] = useState<boolean | null>(null);
  const [cvFilename, setCvFilename] = useState<string | null>(null);

  useEffect(() => {
    if (slug) fetchVacancy(slug).then(setV).catch(() => setV(null));
    fetchLlmStatus().then((s) => setLlmOk(s.available)).catch(() => setLlmOk(false));
    fetchCvStatus()
      .then((s) => {
        setCvReady(s.has_cv);
        setCvFilename(s.filename || null);
      })
      .catch(() => setCvReady(false));
  }, [slug]);

  useEffect(() => {
    if (!slug) return;
    fetchMotivatieLatest(slug).then((r) => {
      if (r) {
        setMotivatie(r.text);
        setMotivatieModel(r.model);
      }
    }).catch(() => {});
    fetchExplainLatest(slug).then((r) => {
      if (r) {
        setExplain(r.text);
        setExplainModel(r.model);
      }
    }).catch(() => {});
  }, [slug]);

  useEffect(() => {
    if (!motivatieJobId || motivatieStatus === "done" || motivatieStatus === "failed") return;
    const t = setInterval(() => {
      fetchLlmJob(motivatieJobId).then((j) => {
        setMotivatieStatus(j.status);
        setMotivatieQueue(j.queue_position);
        if (j.status === "done" && j.text) {
          setMotivatie(j.text);
          setMotivatieModel(j.model || "");
        }
        if (j.status === "failed") setMotivatieError(j.log_tail || "Generatie mislukt");
      });
    }, 2000);
    return () => clearInterval(t);
  }, [motivatieJobId, motivatieStatus]);

  useEffect(() => {
    if (!explainJobId || explainStatus === "done" || explainStatus === "failed") return;
    const t = setInterval(() => {
      fetchLlmJob(explainJobId).then((j) => {
        setExplainStatus(j.status);
        setExplainQueue(j.queue_position);
        if (j.status === "done" && j.text) {
          setExplain(j.text);
          setExplainModel(j.model || "");
        }
        if (j.status === "failed") setExplainError(j.log_tail || "Uitleg mislukt");
      });
    }, 2000);
    return () => clearInterval(t);
  }, [explainJobId, explainStatus]);

  const onGenerateMotivatie = async () => {
    if (!slug) return;
    setMotivatieError("");
    setMotivatieJobId(null);
    try {
      const job = await startMotivatie(slug);
      setMotivatieJobId(job.id);
      setMotivatieStatus(job.status);
      setMotivatieQueue(job.queue_position);
    } catch (e) {
      setMotivatieError(String(e));
    }
  };

  const onGenerateExplain = async () => {
    if (!slug) return;
    setExplainError("");
    setExplainJobId(null);
    try {
      const job = await startExplain(slug);
      setExplainJobId(job.id);
      setExplainStatus(job.status);
      setExplainQueue(job.queue_position);
    } catch (e) {
      setExplainError(String(e));
    }
  };

  const motivatieBusy = motivatieStatus === "queued" || motivatieStatus === "running";
  const explainBusy = explainStatus === "queued" || explainStatus === "running";

  if (!v) return <p className="text-muted-foreground">Laden of niet gevonden…</p>;

  return (
    <div className="space-y-6">
      <Link to="/" className="text-sm text-muted-foreground inline-flex items-center gap-1 hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Terug
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{v.title}</h1>
          <p className="text-muted-foreground mt-1">{v.organisation}</p>
          <p className="mt-2">{v.location} · {v.scale} · {v.hours}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge className={deadlineBadgeClass(v.solliciteer_deadline)}>
            Deadline: {formatDate(v.solliciteer_deadline)}
          </Badge>
          <a
            href={v.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-primary text-primary-foreground h-9 px-4 text-sm font-medium hover:opacity-90"
          >
            Bekijk op IkWerk <ExternalLink className="h-4 w-4" />
          </a>
          <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer">
            <input
              type="checkbox"
              checked={!!v.dismissed}
              onChange={async (e) => {
                if (!slug) return;
                const dismissed = e.target.checked;
                const updated = await setVacancyDismissed(slug, dismissed);
                setV(updated);
              }}
            />
            Niet relevant
          </label>
        </div>
      </div>

      <div className="flex gap-2 border-b border-border">
        {(["sections", "vakgebied", "contact", "motivatie"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm border-b-2 -mb-px ${tab === t ? "border-primary text-primary" : "border-transparent text-muted-foreground"}`}
          >
            {t === "sections" ? "Omschrijving" : t === "vakgebied" ? "Vakgebied" : t === "contact" ? "Contact" : "Motivatie (LLM)"}
          </button>
        ))}
      </div>

      {tab === "sections" && (
        <div className="space-y-4">
          {v.sections.map((s) => (
            <Card key={s.section_type}>
              <CardHeader><CardTitle className="text-base">{s.section_type}</CardTitle></CardHeader>
              <CardContent><p className="text-sm whitespace-pre-wrap leading-relaxed">{s.text}</p></CardContent>
            </Card>
          ))}
          {!v.sections.length && <p className="text-muted-foreground">Geen secties beschikbaar.</p>}
        </div>
      )}

      {tab === "vakgebied" && (
        <div className="flex flex-wrap gap-2">
          {v.vakgebieden.map((t) => <Badge key={t} className="bg-muted">{t}</Badge>)}
        </div>
      )}

      {tab === "contact" && (
        <div className="space-y-3">
          {v.contacts.map((c, i) => (
            <Card key={i}>
              <CardContent className="pt-4 text-sm">
                <p className="font-medium">{c.name}</p>
                <p className="text-muted-foreground">{c.contact_type.replace(/_/g, " ")}</p>
                {c.email && <p>{c.email}</p>}
                {c.phone && <p>{c.phone}</p>}
              </CardContent>
            </Card>
          ))}
          {!v.contacts.length && <p className="text-muted-foreground">Geen contactpersonen geparsed.</p>}
        </div>
      )}

      {tab === "motivatie" && (
        <div className="space-y-6">
          {llmOk === false && (
            <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-3">
              Ollama niet bereikbaar. Start Ollama op de host (<code>ollama serve</code>).
            </p>
          )}
          {cvReady === false && (
            <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-3">
              Upload eerst je CV op de{" "}
              <Link to="/match" className="underline font-medium">Match-pagina</Link>.
            </p>
          )}
          {cvReady && cvFilename && (
            <p className="text-sm text-muted-foreground">Actief CV: {cvFilename}</p>
          )}

          <Card>
            <CardHeader><CardTitle className="text-base">Motivatiebrief</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Button onClick={onGenerateMotivatie} disabled={motivatieBusy || llmOk === false || cvReady === false}>
                <Sparkles className="h-4 w-4 mr-2" />
                {motivatieBusy ? jobStatusLabel(motivatieStatus, motivatieQueue) : "Genereer motivatiebrief"}
              </Button>
              {motivatieError && <p className="text-sm text-destructive">{motivatieError}</p>}
              {motivatie && (
                <div>
                  {motivatieModel && <p className="text-xs text-muted-foreground mb-2">Model: {motivatieModel}</p>}
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{motivatie}</p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Match-uitleg</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Button variant="outline" onClick={onGenerateExplain} disabled={explainBusy || llmOk === false || cvReady === false}>
                {explainBusy ? jobStatusLabel(explainStatus, explainQueue) : "Genereer match-uitleg"}
              </Button>
              {explainError && <p className="text-sm text-destructive">{explainError}</p>}
              {explain && (
                <div>
                  {explainModel && <p className="text-xs text-muted-foreground mb-2">Model: {explainModel}</p>}
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{explain}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
