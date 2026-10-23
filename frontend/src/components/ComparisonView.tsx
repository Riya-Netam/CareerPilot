import { CheckCircle2, CircleAlert, CircleHelp } from "lucide-react";
import type { Comparison, ComparisonItem } from "../types";
import { Badge, Card } from "./ui";
import { ScoreDial } from "./ScoreDial";

const levelTone = { required: "clay", preferred: "teal", uncertain: "signal" } as const;
const statusText = { demonstrated: "Shown in projects or experience", listed: "Listed in skills only", not_found: "Not found in your resume" } as const;

function Row({ i }: { i: ComparisonItem }) {
  const ev = Array.isArray(i.evidence) ? i.evidence : [];
  const Icon = i.status === "not_found" ? CircleAlert : CheckCircle2;
  return (
    <li className="border-t border-line py-3 first:border-t-0">
      <div className="flex flex-wrap items-center gap-2">
        <Icon className={`h-4 w-4 ${i.status === "not_found" ? "text-clay" : "text-teal"}`} aria-hidden />
        <span className="font-semibold">{i.skill}</span>
        <Badge tone={levelTone[i.level]}>{i.level}</Badge>
        <span className="text-sm text-ink-soft">{statusText[i.status]}</span>
      </div>
      <p className="mt-1 pl-6 text-xs text-ink-faint">Why "{i.level}": {i.reason}</p>
      {ev.map((e, k) => <p key={k} className="mt-1 pl-6 text-sm text-ink-soft"><span className="text-ink-faint">{e.section}:</span> “{e.snippet}”</p>)}
    </li>
  );
}

export function ComparisonView({ c }: { c: Comparison }) {
  const cov = (k: "required" | "preferred") => c.coverage[k].total ? `${c.coverage[k].percent}% (${c.coverage[k].demonstrated + c.coverage[k].listed} of ${c.coverage[k].total} found)` : "none in this posting";
  const ex = c.score_explanation;
  return (
    <div className="space-y-5">
      <Card className="flex flex-wrap items-center gap-8">
        <ScoreDial score={c.score} />
        <div className="min-w-[16rem] flex-1 space-y-2 text-sm">
          <p><strong>Required skills:</strong> {cov("required")}</p>
          <p><strong>Preferred skills:</strong> {cov("preferred")}</p>
          <p className="text-ink-soft">How this is calculated: <code>{ex.formula}</code>. Weights: required {ex.weights.required}, unclear {ex.weights.uncertain}, preferred {ex.weights.preferred}. Credit: shown in projects or experience {ex.credits.demonstrated}, listed in skills only {ex.credits.listed}, not found 0.</p>
          <p className="rounded-md bg-signal-tint px-3 py-2 text-signal-dark">{ex.disclaimer}</p>
        </div>
      </Card>

      {c.priorities.length > 0 && (
        <Card>
          <h2>What to work on first</h2>
          <ol className="mt-3 space-y-2">
            {c.priorities.slice(0, 8).map((p) => (
              <li key={p.skill} className="flex flex-wrap items-center gap-2 text-sm">
                <Badge tone={p.priority === "high" ? "clay" : p.priority === "medium" ? "signal" : "neutral"}>{p.priority}</Badge>
                <strong>{p.skill}</strong><span className="text-ink-soft">{p.why}</span>
              </li>
            ))}
          </ol>
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <Card><h2>Matched in your resume ({c.matched.length})</h2>
          {c.matched.length ? <ul className="mt-2">{c.matched.map((i) => <Row key={i.skill} i={i} />)}</ul> : <p className="mt-2 text-sm text-ink-soft">None of the posting's skills were found in this resume.</p>}
        </Card>
        <Card><h2>Not found in your resume ({c.not_found.length})</h2>
          <p className="mt-1 text-xs text-ink-faint">Not found means the wording is not in your resume text. You may still have the skill; add honest evidence if you do.</p>
          {c.not_found.length ? <ul className="mt-2">{c.not_found.map((i) => <Row key={i.skill} i={i} />)}</ul> : <p className="mt-2 text-sm text-ink-soft">Everything in the posting was found.</p>}
        </Card>
      </div>

      {c.manual_confirmation.length > 0 && (
        <Card>
          <h2 className="flex items-center gap-2"><CircleHelp className="h-5 w-5 text-signal-dark" aria-hidden />Please confirm yourself</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-soft">{c.manual_confirmation.map((m, k) => <li key={k}>{m.skill ? <strong>{m.skill}: </strong> : null}{m.note}</li>)}</ul>
        </Card>
      )}
    </div>
  );
}
