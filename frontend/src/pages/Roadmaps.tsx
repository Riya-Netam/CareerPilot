import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { Badge, Card, EmptyState, ErrorNote, PageHeader, Progress, Select, Spinner } from "../components/ui";
import { api } from "../services/api";
import type { Roadmap, RoadmapItem } from "../types";

const tone = { high: "clay", medium: "signal", low: "neutral" } as const;

export function RoadmapsPage() {
  const q = useQuery({ queryKey: ["roadmaps"], queryFn: () => api.get<{ items: Roadmap[] }>("/roadmaps") });
  return (
    <>
      <PageHeader title="Learning Roadmaps" subtitle="Personal learning plans created from your job analyses." />
      {q.isLoading ? <Spinner /> : !q.data?.items.length ? <EmptyState title="No roadmaps yet" body="Open a job analysis and choose “Learning roadmap”." action={<Link to="/analyzer" className="underline">Go to analyses</Link>} /> : (
        <ul className="grid gap-4 sm:grid-cols-2">{q.data.items.map((r) => (
          <li key={r.id}><Link to={`/roadmaps/${r.id}`} className="block rounded-card border border-line bg-white p-5 hover:border-teal">
            <p className="font-semibold">{r.title}</p><p className="mt-1 text-sm text-ink-soft">{r.progress.completed} of {r.progress.total} skills completed</p>
            <div className="mt-3"><Progress percent={r.progress.percent} label={`${r.title} progress`} /></div></Link></li>))}</ul>)}
    </>
  );
}

function ItemCard({ roadmapId, item, onSaved }: { roadmapId: string; item: RoadmapItem; onSaved: (r: Roadmap) => void }) {
  const m = useMutation({ mutationFn: (body: any) => api.patch<Roadmap>(`/roadmaps/${roadmapId}/items/${item.id}`, body), onSuccess: onSaved });
  const c = item.content;
  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2"><h2>{item.skill}</h2><Badge tone={tone[item.priority]}>{item.priority} priority</Badge></div>
        <Select aria-label={`Status for ${item.skill}`} className="!w-40" value={item.status} onChange={(e) => m.mutate({ status: e.target.value })}>
          <option value="not_started">Not started</option><option value="in_progress">In progress</option><option value="completed">Completed</option></Select>
      </div>
      <p className="mt-2 text-sm text-ink-soft"><strong>Why it matters here:</strong> {item.why}</p>
      <p className="mt-2 text-sm">{c.explanation}</p>
      {c.prerequisites.length > 0 && <p className="mt-2 text-sm text-ink-soft"><strong>Helpful first:</strong> {c.prerequisites.join(", ")}</p>}
      <fieldset className="mt-3"><legend className="text-sm font-semibold">Practice tasks</legend>
        <ul className="mt-1 space-y-1">{item.tasks.map((t, i) => (
          <li key={i}><label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={t.done} onChange={(e) => m.mutate({ tasks: item.tasks.map((x, k) => k === i ? { ...x, done: e.target.checked } : x) })} /><span className={t.done ? "text-ink-faint line-through" : ""}>{t.text}</span></label></li>))}</ul></fieldset>
      <p className="mt-3 text-sm text-ink-soft"><strong>Estimated effort:</strong> about {c.estimated_hours_min}–{c.estimated_hours_max} hours. <em>{c.effort_note}</em></p>
      <ul className="mt-2 space-y-1 text-sm">{c.resources.map((r, i) => <li key={i}>{r.url ? <a className="inline-flex items-center gap-1 font-medium underline" href={r.url} target="_blank" rel="noopener noreferrer">{r.title}<ExternalLink className="h-3 w-3" aria-hidden /></a> : <span>{r.title}</span>}<span className="block text-xs text-ink-faint">{r.note}</span></li>)}</ul>
      <ErrorNote error={m.error} />
    </Card>
  );
}

export function RoadmapDetailPage() {
  const { id } = useParams();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["roadmap", id], queryFn: () => api.get<Roadmap>(`/roadmaps/${id}`) });
  if (q.isLoading) return <Spinner />;
  if (q.error) return <ErrorNote error={q.error} />;
  const r = q.data!;
  const saved = (nr: Roadmap) => { qc.setQueryData(["roadmap", id], nr); qc.invalidateQueries({ queryKey: ["roadmaps"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); };
  return (
    <>
      <PageHeader title={r.title} subtitle="Hours are rough estimates for a beginner. Resource links go to official sites; check they are still current." />
      <Card className="mb-5"><p className="mb-2 text-sm">{r.progress.completed} of {r.progress.total} skills completed ({r.progress.percent}%)</p><Progress percent={r.progress.percent} label="Roadmap progress" /></Card>
      {r.items?.length === 0 && <EmptyState title="Nothing to learn here" body="Every skill in this posting was found in your resume." />}
      <div className="space-y-4">{r.items?.map((it) => <ItemCard key={it.id} roadmapId={r.id} item={it} onSaved={saved} />)}</div>
    </>
  );
}
