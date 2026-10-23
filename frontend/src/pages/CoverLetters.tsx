import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Download, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorNote, Input, PageHeader, Spinner, Textarea } from "../components/ui";
import { useToast } from "../hooks/useToast";
import { api } from "../services/api";

const sourceLabel: Record<string, [string, "teal" | "signal" | "neutral"]> = { ai: ["AI-drafted", "signal"], fallback_template: ["Template (no AI used)", "neutral"], user_edited: ["Edited by you", "teal"] };

export function CoverLettersPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const list = useQuery({ queryKey: ["letters"], queryFn: () => api.get<any[]>("/cover-letters") });
  const analyses = useQuery({ queryKey: ["analyses"], queryFn: () => api.get<any>("/job-analyses") });
  const [selId, setSelId] = useState<string | null>(null);
  const [draft, setDraft] = useState({ title: "", content: "" });
  const [analysisId, setAnalysisId] = useState("");
  const [notes, setNotes] = useState("");
  const [del, setDel] = useState(false);
  const sel = list.data?.find((l) => l.id === selId);
  useEffect(() => { if (sel) setDraft({ title: sel.title, content: sel.content }); }, [selId, sel?.updated_at]);

  const gen = useMutation({
    mutationFn: () => api.post<any>("/cover-letters/generate", { analysis_id: analysisId, notes: notes || null }),
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["letters"] }); setSelId(r.letter.id); toast("success", r.label); },
  });
  const save = useMutation({ mutationFn: () => api.patch(`/cover-letters/${selId}`, draft), onSuccess: () => { qc.invalidateQueries({ queryKey: ["letters"] }); toast("success", "Saved."); } });
  const remove = useMutation({ mutationFn: () => api.del(`/cover-letters/${selId}`), onSuccess: () => { qc.invalidateQueries({ queryKey: ["letters"] }); setSelId(null); setDel(false); } });

  if (list.isLoading) return <Spinner />;
  return (
    <>
      <PageHeader title="Cover Letter Generator" subtitle="Drafts use only facts from your resume and anything you type below. Always read and edit before sending." />
      <div className="grid gap-5 lg:grid-cols-[20rem_1fr]">
        <div className="space-y-4">
          <Card className="space-y-3"><h2>New draft</h2>
            {!analyses.data?.items.length ? <p className="text-sm text-ink-soft">Analyse a job first. <Link className="underline" to="/analyzer/new">Start an analysis</Link></p> : <>
              <label className="block text-sm font-medium" htmlFor="an">Job analysis</label>
              <select id="an" className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm" value={analysisId} onChange={(e) => setAnalysisId(e.target.value)}><option value="">Choose…</option>{analyses.data.items.map((a: any) => <option key={a.id} value={a.id}>{a.job_title}{a.company ? ` · ${a.company}` : ""}</option>)}</select>
              <label className="block text-sm font-medium" htmlFor="notes">Extra facts to include (optional)</label>
              <Textarea id="notes" rows={3} maxLength={1500} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Only true things, e.g. availability" />
              <ErrorNote error={gen.error} />
              <Button disabled={!analysisId} busy={gen.isPending} onClick={() => gen.mutate()}>Generate draft</Button></>}
          </Card>
          {list.data?.length ? <ul className="space-y-2">{list.data.map((l) => <li key={l.id}><button onClick={() => setSelId(l.id)} className={`w-full rounded-card border p-3 text-left text-sm ${selId === l.id ? "border-teal bg-teal-tint" : "border-line bg-white"}`}><span className="block truncate font-semibold">{l.title}</span><span className="text-xs text-ink-faint">{new Date(l.updated_at).toLocaleDateString()}</span></button></li>)}</ul> : <EmptyState title="No drafts yet" body="Generated letters are saved here." />}
        </div>
        <div>
          {!sel ? <p className="text-sm text-ink-soft">Select or generate a letter to edit it.</p> : (
            <Card className="space-y-3">
              <div className="flex flex-wrap items-center gap-2"><Badge tone={sourceLabel[sel.source]?.[1] ?? "neutral"}>{sourceLabel[sel.source]?.[0] ?? sel.source}</Badge>{sel.ai_model && <span className="text-xs text-ink-faint">{sel.ai_model}</span>}</div>
              <Input aria-label="Title" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
              <Textarea aria-label="Letter text" rows={18} value={draft.content} onChange={(e) => setDraft({ ...draft, content: e.target.value })} />
              <ErrorNote error={save.error} />
              <div className="flex flex-wrap gap-2">
                <Button busy={save.isPending} onClick={() => save.mutate()}>Save</Button>
                <Button variant="secondary" onClick={async () => { await navigator.clipboard.writeText(draft.content); toast("success", "Copied."); }}><Copy className="h-4 w-4" aria-hidden />Copy</Button>
                <Button variant="secondary" onClick={() => api.download(`/cover-letters/${selId}/download`, "cover-letter.txt")}><Download className="h-4 w-4" aria-hidden />Download</Button>
                <Button variant="danger" onClick={() => setDel(true)}><Trash2 className="h-4 w-4" aria-hidden />Delete</Button>
              </div>
            </Card>)}
        </div>
      </div>
      <ConfirmDialog open={del} title="Delete this letter?" body="This cannot be undone." confirmLabel="Delete" busy={remove.isPending} onCancel={() => setDel(false)} onConfirm={() => remove.mutate()} />
    </>
  );
}
