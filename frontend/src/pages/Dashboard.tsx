import { useQuery } from "@tanstack/react-query";
import { Link, useLocation } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Card, EmptyState, ErrorNote, PageHeader, Progress, Spinner } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/api";

export function DashboardPage() {
  const { user } = useAuth();
  const notice = (useLocation().state as { notice?: string } | null)?.notice;
  const q = useQuery({ queryKey: ["dashboard"], queryFn: () => api.get<any>("/dashboard") });
  if (q.isLoading) return <Spinner />;
  if (q.error) return <ErrorNote error={q.error} />;
  const d = q.data;
  const fresh = d.counts.resumes === 0;
  const chart = Object.entries(d.application_status).map(([status, count]) => ({ status: status[0] + status.slice(1).toLowerCase(), count }));
  return (
    <>
      <PageHeader title={`Welcome, ${user?.full_name.split(" ")[0]}`} subtitle="Everything here is calculated from your own saved data." />
      {notice && <p role="alert" className="mb-4 rounded-md bg-signal-tint px-3 py-2 text-sm text-signal-dark">{notice}</p>}
      {fresh && <EmptyState title="Start with your resume" body="Upload a PDF or DOCX resume, then paste a job description to see which skills match and which to learn next." action={<Link to="/resumes" className="rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white">Upload a resume</Link>} />}
      {!fresh && (
        <div className="grid gap-5 lg:grid-cols-3">
          <Card className="lg:col-span-3">
            <dl className="grid grid-cols-2 gap-4 sm:grid-cols-5">
              {[["Resumes", d.counts.resumes], ["Job analyses", d.counts.job_analyses], ["Roadmaps", d.counts.roadmaps], ["Cover letters", d.counts.cover_letters], ["Applications", d.counts.applications]].map(([k, v]) => (
                <div key={k as string}><dt className="text-xs text-ink-faint">{k}</dt><dd className="text-2xl font-bold">{v}</dd></div>))}
            </dl>
          </Card>
          <Card><h2>Recent job comparisons</h2>
            {d.recent_analyses.length ? <ul className="mt-3 space-y-2 text-sm">{d.recent_analyses.map((a: any) => <li key={a.id} className="flex justify-between gap-2"><Link className="underline" to={`/analyzer/${a.id}`}>{a.job_title}{a.company ? ` · ${a.company}` : ""}</Link><span className="font-semibold">{a.score ?? "–"}</span></li>)}</ul> : <p className="mt-2 text-sm text-ink-soft">No comparisons yet. <Link className="underline" to="/analyzer/new">Analyse a job</Link>.</p>}
          </Card>
          <Card><h2>Top matched skills</h2>
            <div className="mt-3 flex flex-wrap gap-2">{d.top_matched_skills.length ? d.top_matched_skills.map((s: any) => <Badge key={s.skill} tone="teal">{s.skill}</Badge>) : <p className="text-sm text-ink-soft">Appears after your first analysis.</p>}</div>
            <h2 className="mt-5">Important gaps</h2>
            <div className="mt-3 flex flex-wrap gap-2">{d.important_gaps.length ? d.important_gaps.map((s: any) => <Badge key={s.skill} tone="clay">{s.skill}</Badge>) : <p className="text-sm text-ink-soft">No required skills missing so far.</p>}</div>
          </Card>
          <Card><h2>Roadmap progress</h2>
            {d.roadmap_progress.total ? <><p className="mt-3 text-sm">{d.roadmap_progress.completed} of {d.roadmap_progress.total} skills completed</p><div className="mt-2"><Progress percent={d.roadmap_progress.percent} label="Roadmap progress" /></div></> : <p className="mt-2 text-sm text-ink-soft">Create a roadmap from any analysis.</p>}
          </Card>
          <Card className="lg:col-span-2"><h2>Applications by status</h2>
            {d.counts.applications ? <div className="mt-3 h-52"><ResponsiveContainer width="100%" height="100%"><BarChart data={chart}><CartesianGrid vertical={false} stroke="#D5DEE5" /><XAxis dataKey="status" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} width={28} tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="count" fill="#1B7A8C" radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer></div> : <p className="mt-2 text-sm text-ink-soft">Track a job to see your pipeline here.</p>}
          </Card>
          <Card><h2>Upcoming deadlines</h2>
            {d.upcoming_deadlines.length ? <ul className="mt-3 space-y-2 text-sm">{d.upcoming_deadlines.map((a: any) => <li key={a.id}><strong>{a.deadline}</strong> · {a.job_title} at {a.company}</li>)}</ul> : <p className="mt-2 text-sm text-ink-soft">No deadlines in the next 30 days.</p>}
          </Card>
          <Card className="lg:col-span-3"><h2>Recent activity</h2>
            <ul className="mt-3 space-y-1 text-sm">{d.recent_activity.map((e: any, i: number) => <li key={i} className="flex justify-between gap-3"><span>{e.label}</span><time className="text-ink-faint" dateTime={e.at}>{new Date(e.at).toLocaleDateString()}</time></li>)}</ul>
          </Card>
        </div>
      )}
    </>
  );
}
