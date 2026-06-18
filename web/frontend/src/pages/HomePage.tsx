import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchStats, fetchVacancies, setVacancyDismissed, VacancyListItem } from "../api/client";
import { Badge, Card, CardContent, CardHeader, CardTitle, Input, Select } from "../components/ui";
import { deadlineBadgeClass, formatDate } from "../lib/utils";
import { ExternalLink } from "lucide-react";

export function HomePage() {
  const [items, setItems] = useState<VacancyListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [location, setLocation] = useState("");
  const [openOnly, setOpenOnly] = useState(true);
  const [excludeDismissed, setExcludeDismissed] = useState(true);
  const [sort, setSort] = useState("deadline");
  const [stats, setStats] = useState({ total: 0, open_count: 0, closed_count: 0 });
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    const p = new URLSearchParams();
    if (q) p.set("q", q);
    if (location) p.set("location", location);
    if (openOnly) p.set("open_only", "true");
    if (!excludeDismissed) p.set("exclude_dismissed", "false");
    p.set("sort", sort);
    p.set("limit", "50");
    fetchVacancies(p)
      .then((r) => {
        setItems(r.items);
        setTotal(r.total);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchStats().then(setStats).catch(() => {});
  }, []);

  useEffect(() => {
    load();
  }, [q, location, openOnly, excludeDismissed, sort]);

  const onDismissToggle = async (slug: string, dismissed: boolean) => {
    await setVacancyDismissed(slug, dismissed);
    if (excludeDismissed && dismissed) {
      setItems((prev) => prev.filter((v) => v.slug !== slug));
      setTotal((t) => Math.max(0, t - 1));
    } else {
      setItems((prev) =>
        prev.map((v) => (v.slug === slug ? { ...v, dismissed } : v))
      );
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <Card><CardContent className="pt-6"><div className="text-2xl font-bold">{stats.total}</div><div className="text-sm text-muted-foreground">Totaal</div></CardContent></Card>
        <Card><CardContent className="pt-6"><div className="text-2xl font-bold text-emerald-600">{stats.open_count}</div><div className="text-sm text-muted-foreground">Open</div></CardContent></Card>
        <Card><CardContent className="pt-6"><div className="text-2xl font-bold">{stats.closed_count}</div><div className="text-sm text-muted-foreground">Gesloten</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Input placeholder="Zoek titel, org, locatie…" value={q} onChange={(e) => setQ(e.target.value)} className="max-w-xs" />
          <Input placeholder="Locatie (bv. Den Haag)" value={location} onChange={(e) => setLocation(e.target.value)} className="max-w-xs" />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={openOnly} onChange={(e) => setOpenOnly(e.target.checked)} />
            Alleen open
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={excludeDismissed} onChange={(e) => setExcludeDismissed(e.target.checked)} />
            Verberg irrelevant
          </label>
          <Select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="deadline">Deadline ↑</option>
            <option value="deadline_desc">Deadline ↓</option>
            <option value="title">Titel</option>
          </Select>
        </CardContent>
      </Card>

      <p className="text-sm text-muted-foreground">{total} vacatures</p>

      {loading ? (
        <p className="text-muted-foreground">Laden…</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((v) => (
            <Card key={v.slug} className="hover:shadow-md transition-shadow">
              <CardContent className="pt-6 space-y-3">
                <div className="flex justify-between gap-2">
                  <Link to={`/vacatures/${v.slug}`} className="font-semibold hover:text-primary line-clamp-2">
                    {v.title}
                  </Link>
                  <Badge className={deadlineBadgeClass(v.solliciteer_deadline)}>{formatDate(v.solliciteer_deadline)}</Badge>
                </div>
                <p className="text-sm text-muted-foreground">{v.organisation}</p>
                <p className="text-sm">{v.location} · {v.scale}</p>
                <div className="flex flex-wrap gap-1">
                  {v.vakgebieden.slice(0, 3).map((t) => (
                    <Badge key={t} className="bg-muted text-muted-foreground">{t}</Badge>
                  ))}
                </div>
                <div className="flex justify-between items-center">
                  <a href={v.url} target="_blank" rel="noreferrer" className="text-sm text-primary inline-flex items-center gap-1 hover:underline">
                    IkWerk <ExternalLink className="h-3 w-3" />
                  </a>
                  <label className="flex items-center gap-1 text-xs text-muted-foreground cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!!v.dismissed}
                      onChange={(e) => onDismissToggle(v.slug, e.target.checked)}
                    />
                    Niet relevant
                  </label>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
