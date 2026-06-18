import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui";
import { Info } from "lucide-react";

export function MatchUitlegPage() {
  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-2">
        <Info className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-bold">Hoe werken RAG- en keyword-scores?</h1>
      </div>

      <p className="text-muted-foreground">
        Op de <Link to="/match" className="text-primary underline">CV-match</Link> pagina zie je twee
        scores per vacature. Ze meten verschillende dingen en worden samen gebruikt voor de ranking.
      </p>

      <Card>
        <CardHeader><CardTitle>Overzicht</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b text-left">
                <th className="py-2 pr-3">Aspect</th>
                <th className="py-2 pr-3">RAG-score</th>
                <th className="py-2">Keyword-score</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground">
              <tr className="border-b"><td className="py-2 pr-3 font-medium text-foreground">Doel</td><td className="py-2 pr-3">Overlap tussen CV en volledige vacaturetekst</td><td className="py-2">Checklist op vaardigheden en rollen</td></tr>
              <tr className="border-b"><td className="py-2 pr-3 font-medium text-foreground">Methode</td><td className="py-2 pr-3">TF-IDF + cosine similarity over tekstchunks</td><td className="py-2">Gewogen zoektermen in titel, samenvatting en detail</td></tr>
              <tr className="border-b"><td className="py-2 pr-3 font-medium text-foreground">CV-input</td><td className="py-2 pr-3">Profiel + werkervaring (eerste ~6000 tekens)</td><td className="py-2">Volledige CV (+25% bonus bij dubbele hits)</td></tr>
              <tr className="border-b"><td className="py-2 pr-3 font-medium text-foreground">Sorteervolgorde</td><td className="py-2 pr-3"><strong className="text-foreground">Primair</strong></td><td className="py-2"><strong className="text-foreground">Tiebreaker</strong></td></tr>
              <tr><td className="py-2 pr-3 font-medium text-foreground">Schaal</td><td className="py-2 pr-3">0–1 (typisch tops ~0,06–0,12)</td><td className="py-2">Additief (~5–60); UI normaliseert op /30</td></tr>
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>RAG-score (primair)</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            Vacatures worden opgesplitst in chunks (metadata, &quot;Dit ga je doen&quot;, eisen, enz.).
            Het CV wordt omgezet naar een zoekquery. Per vacature telt de <strong className="text-foreground">hoogste</strong> similarity
            tussen die query en één chunk.
          </p>
          <p>
            Dit vangt brede lexicale overlap op — ook als exacte skill-termen niet in je keyword-lijst staan.
            De snippet bij een resultaat komt uit de best scorende chunk.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Keyword-score (ter referentie)</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            Configureerbare termen (bijv. python, kubernetes, data engineer) met gewichten. Negatieve termen
            (bijv. sap, junior) verlagen de score. Optionele bonussen voor rol-titels of voorkeurslocatie.
          </p>
          <p>
            Twee vacatures met dezelfde RAG-score worden gesorteerd op keyword-score. Rankings kunnen
            dus afwijken: een vacature met veel buzzwords scoort hoger op keywords, terwijl RAG de
            semantisch beste tekstmatch kiest.
          </p>
          <p>
            Pas termen aan via <code className="text-xs bg-muted px-1 rounded">config/keywords.example.yaml</code> en
            env <code className="text-xs bg-muted px-1 rounded">KEYWORDS_CONFIG</code>.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>LLM &quot;Uitleg&quot;</CardTitle></CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          De knop Uitleg op een vacature start een aparte LLM-taak. Die genereert een korte motivatie in
          proza — geen numerieke score en geen invloed op de ranking.
        </CardContent>
      </Card>

      <p className="text-sm">
        <Link to="/match" className="text-primary underline">← Terug naar CV-match</Link>
      </p>
    </div>
  );
}
