import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorNote, Field, Input, PageHeader, Select, Spinner, Textarea } from "../components/ui";
import { ComparisonView } from "../components/ComparisonView";
import { useToast } from "../hooks/useToast";
import { api } from "../services/api";
import type { Analysis, Level, Page } from "../types";

export function AnalyzerListPage() {
  const q = useQuery({ queryKey: ["analyses"], queryFn: () => api.get<Page<any>>("/job-analyses") });
  return (
    <>
      <PageHeader title="Job Skill Analyzer" subtitle="Paste a job description, review the skills we extract, then compare them with your resume." actions={<Link to="/analyzer/new" className="inline-flex items-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white"><Plus className="h-4 w-4" aria-hidden />New analysis</Link>} />
      {q.isLoading ? <Spinner /> : q.data?.items.length === 0 ? <EmptyState title="No analyses yet" body="Your saved job comparisons will appear here." action={<Link to="/analyzer/new" className="underline">Start your first analysis</Link>} /> : (
        <div className="overflow-x-auto rounded-card border border-line bg-white"><table className="w-full text-left text-sm">
          <thead className="bg-paper text-xs uppercase text-ink-faint"><tr><th className="p-3">Job</th><th className="p-3">Resume</th><th className="p-3">Alignment</th><th className="p-3">Date</th></tr></thead>
          <tbody>{q.data?.items.map((a) => <tr key={a.id} className="border-t border-line"><td className="p-3"><Link className="font-semibold underline" to={`/analyzer/${a.id}`}>{a.job_title}</Link>{a.company && <span className="text-ink-soft"> · {a.company}</span>}</td><td className="p-3 text-ink-soft">{a.resume_filename}</td><td className="p-3 font-semibold">{a.score ?? "–"}</td><td className="p-3 text-ink-soft">{new Date(a.created_at).toLocaleDateString()}</td></tr>)}</tbody>
        </table></div>)}
    </>
  );
}

type Req = { skill: string; level: Level };

export function NewAnalysisPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const toast = useToast();
  const resumes = useQuery({ queryKey: ["resumes"], queryFn: () => api.get<Page<any>>("/resumes") });
  const [f, setF] = useState({ title: "", company: "", location: "", experience_level: "", description: "", resume_id: "" });
  const [reqs, setReqs] = useState<Req[] | null>(null);
  const [quals, setQuals] = useState<{ type: string; text: string }[]>([]);
  const [newSkill, setNewSkill] = useState("");
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<any>) => setF({ ...f, [k]: e.target.value });

  const extract = useMutation({
    mutationFn: () => api.post<any>("/job-analyses/extract", { description: f.description }),
    onSuccess: (r) => { setReqs(r.requirements.map((x: any) => ({ skill: x.skill, level: x.level }))); setQuals(r.qualifications); },
  });
  const compare = useMutation({
    mutationFn: () => api.post<Analysis>("/job-analyses", { ...f, company: f.company || null, location: f.location || null, experience_level: f.experience_level || null, requirements: reqs }),
    onSuccess: (a) => { qc.invalidateQueries(); toast("success", "Analysis saved."); navigate(`/analyzer/${a.id}`); },
  });
  const canExtract = f.title.trim() && f.description.trim().length >= 50;

  if (resumes.isLoading) return <Spinner />;
  if (!resumes.data?.items.length) return <EmptyState title="Upload a resume first" body="The analyzer compares a job description with one of your resumes." action={<Link className="underline" to="/resumes">Go to My Resumes</Link>} />;

  return (
    <>
      <PageHeader title="New job analysis" subtitle="Step 1: describe the job. Step 2: check what we extracted. Step 3: compare with your resume." />
      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="space-y-4">
          <h2>1. The job</h2>
          <Field id="title" label="Job title"><Input id="title" value={f.title} onChange={set("title")} maxLength={200} /></Field>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field id="company" label="Company (optional)"><Input id="company" value={f.company} onChange={set("company")} /></Field>
            <Field id="location" label="Location (optional)"><Input id="location" value={f.location} onChange={set("location")} /></Field>
            <Field id="level" label="Level (optional)"><Select id="level" value={f.experience_level} onChange={set("experience_level")}><option value="">Not sure</option><option>Internship</option><option>Entry level</option><option>Mid level</option><option>Senior</option></Select></Field>
          </div>
          <Field id="jd" label="Job description" hint="Paste the full posting. Headings like Requirements and Nice to have help the analysis."><Textarea id="jd" rows={12} value={f.description} onChange={set("description")} maxLength={20000} /></Field>
          <ErrorNote error={extract.error} />
          <Button disabled={!canExtract} busy={extract.isPending} onClick={() => extract.mutate()}>Extract skills</Button>
        </Card>

        <Card className="space-y-4">
          <h2>2. Review what was extracted</h2>
          {!reqs ? <p className="text-sm text-ink-soft">Extracted skills appear here. You can change whether each is required or preferred, remove wrong ones, or add missing ones before comparing.</p> : (
            <>
              <p className="text-xs text-ink-faint">“Unclear” means the posting does not say whether the skill is required. Please set it yourself if you know.</p>
              <ul className="divide-y divide-line">{reqs.map((r, i) => (
                <li key={r.skill} className="flex items-center gap-2 py-2">
                  <span className="min-w-0 flex-1 truncate text-sm font-medium">{r.skill}</span>
                  <Select aria-label={`Level for ${r.skill}`} className="!w-32" value={r.level} onChange={(e) => setReqs(reqs.map((x, k) => k === i ? { ...x, level: e.target.value as Level } : x))}><option value="required">Required</option><option value="preferred">Preferred</option><option value="uncertain">Unclear</option></Select>
                  <button aria-label={`Remove ${r.skill}`} className="p-1 text-ink-faint hover:text-clay" onClick={() => setReqs(reqs.filter((_, k) => k !== i))}><Trash2 className="h-4 w-4" /></button>
                </li>))}</ul>
              {reqs.length === 0 && <p className="text-sm text-ink-soft">No skills were recognised. Add the ones you see in the posting.</p>}
              <div className="flex gap-2"><Input aria-label="Add a skill" placeholder="Add a skill, e.g. Docker" value={newSkill} onChange={(e) => setNewSkill(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && newSkill.trim()) { setReqs([...reqs, { skill: newSkill.trim(), level: "required" }]); setNewSkill(""); } }} />
                <Button variant="secondary" onClick={() => { if (newSkill.trim()) { setReqs([...reqs, { skill: newSkill.trim(), level: "required" }]); setNewSkill(""); } }}>Add</Button></div>
              {quals.length > 0 && <div><h3 className="text-sm font-semibold">Qualifications to confirm yourself</h3><ul className="mt-1 list-disc pl-5 text-sm text-ink-soft">{quals.map((q, i) => <li key={i}>{q.text}</li>)}</ul></div>}
              <h2 className="pt-2">3. Compare</h2>
              <Field id="resume" label="Resume to compare"><Select id="resume" value={f.resume_id} onChange={set("resume_id")}><option value="">Choose a resume…</option>{resumes.data.items.map((r) => <option key={r.id} value={r.id}>{r.original_filename}</option>)}</Select></Field>
              <ErrorNote error={compare.error} />
              <Button disabled={!f.resume_id} busy={compare.isPending} onClick={() => compare.mutate()}>Compare with my resume</Button>
            </>)}
        </Card>
      </div>
    </>
  );
}

export function AnalysisDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const toast = useToast();
  const [confirm, setConfirm] = useState(false);
  const q = useQuery({ queryKey: ["analysis", id], queryFn: () => api.get<Analysis>(`/job-analyses/${id}`) });
  const roadmap = useMutation({ mutationFn: () => api.post<any>("/roadmaps", { analysis_id: id }), onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["roadmaps"] }); navigate(`/roadmaps/${r.id}`); }, onError: (e) => toast("error", (e as Error).message) });
  const letter = useMutation({ mutationFn: () => api.post<any>("/cover-letters/generate", { analysis_id: id }), onSuccess: () => { qc.invalidateQueries({ queryKey: ["letters"] }); navigate("/cover-letters"); }, onError: (e) => toast("error", (e as Error).message) });
  const track = useMutation({ mutationFn: (a: Analysis) => api.post("/applications", { company: a.company || "Unknown company", job_title: a.job_title, analysis_id: a.id }), onSuccess: () => { qc.invalidateQueries({ queryKey: ["applications"] }); toast("success", "Added to your job applications."); } });
  const del = useMutation({ mutationFn: () => api.del(`/job-analyses/${id}`), onSuccess: () => { qc.invalidateQueries(); navigate("/analyzer"); } });
  const recompute = useMutation({ mutationFn: (reqs: any[]) => api.patch<Analysis>(`/job-analyses/${id}/requirements`, { requirements: reqs }), onSuccess: (a) => { qc.setQueryData(["analysis", id], a); toast("success", "Score recalculated."); } });

  if (q.isLoading) return <Spinner />;
  if (q.error) return <ErrorNote error={q.error} />;
  const a = q.data!;
  return (
    <>
      <PageHeader title={a.job_title} subtitle={`${a.company ? a.company + " · " : ""}compared with ${a.resume_filename}${a.user_adjusted ? " · requirements adjusted by you" : ""}`} actions={
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => roadmap.mutate()} busy={roadmap.isPending}>Learning roadmap</Button>
          <Button variant="secondary" onClick={() => letter.mutate()} busy={letter.isPending}>Cover letter</Button>
          <Button variant="secondary" onClick={() => track.mutate(a)}>Track application</Button>
          <Button variant="secondary" onClick={() => api.download(`/job-analyses/${id}/report`, "job-analysis.md")}>Report</Button>
          <Button variant="danger" onClick={() => setConfirm(true)}><Trash2 className="h-4 w-4" aria-hidden />Delete</Button>
        </div>} />
      <ComparisonView c={a.comparison} />
      <Card className="mt-5"><h2>Correct a requirement</h2>
        <p className="mt-1 text-xs text-ink-faint">If we misjudged a skill, change it here and the score is recalculated.</p>
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">{a.requirements.map((r, i) => (
          <li key={r.skill} className="flex items-center gap-2 text-sm"><span className="flex-1 truncate">{r.skill}</span>
            <Select aria-label={`Level for ${r.skill}`} className="!w-32" value={r.level} onChange={(e) => recompute.mutate(a.requirements.map((x, k) => k === i ? { ...x, level: e.target.value } : x))}><option value="required">Required</option><option value="preferred">Preferred</option><option value="uncertain">Unclear</option></Select>
            <button aria-label={`Remove ${r.skill}`} className="p-1 text-ink-faint hover:text-clay" onClick={() => recompute.mutate(a.requirements.filter((_, k) => k !== i))}><Trash2 className="h-4 w-4" /></button></li>))}</ul>
      </Card>
      <ConfirmDialog open={confirm} title="Delete this analysis?" body="The comparison and its roadmap will be removed." confirmLabel="Delete" busy={del.isPending} onCancel={() => setConfirm(false)} onConfirm={() => del.mutate()} />
    </>
  );
}
