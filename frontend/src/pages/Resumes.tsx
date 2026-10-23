import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorNote, PageHeader, Spinner } from "../components/ui";
import { useToast } from "../hooks/useToast";
import { api } from "../services/api";
import type { Page } from "../types";
import { validateResumeFile } from "../utils/validate";

export function ResumesPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<any | null>(null);
  const list = useQuery({ queryKey: ["resumes"], queryFn: () => api.get<Page<any>>("/resumes") });
  const detail = useQuery({ queryKey: ["resume", selected], queryFn: () => api.get<any>(`/resumes/${selected}`), enabled: !!selected });
  const upload = useMutation({
    mutationFn: (f: File) => api.upload<any>("/resumes", f),
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["resumes"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); setSelected(r.id); toast("success", "Resume uploaded and analysed."); },
  });
  const del = useMutation({
    mutationFn: (id: string) => api.del(`/resumes/${id}`),
    onSuccess: () => { qc.invalidateQueries(); setToDelete(null); setSelected(null); toast("success", "Resume deleted."); },
  });
  const aiSug = useMutation({
    mutationFn: (id: string) => api.post<any>(`/resumes/${id}/ai-suggestions`),
    onSuccess: (r) => qc.setQueryData(["resume", r.id], r),
    onError: (e) => toast("error", (e as Error).message),
  });

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]; e.target.value = "";
    if (!f) return;
    const err = validateResumeFile(f);
    setLocalError(err);
    if (!err) upload.mutate(f);
  }
  const a = detail.data?.analysis;
  return (
    <>
      <PageHeader title="My Resumes" subtitle="Upload a text-based PDF or a DOCX (up to 5 MB). Files are private to your account." actions={
        <><input ref={fileRef} type="file" accept=".pdf,.docx" className="sr-only" aria-label="Choose a resume file" onChange={onPick} />
          <Button busy={upload.isPending} onClick={() => fileRef.current?.click()}><Upload className="h-4 w-4" aria-hidden />Upload resume</Button></>} />
      {localError && <p role="alert" className="mb-3 text-sm font-medium text-clay">{localError}</p>}
      <ErrorNote error={upload.error} />
      {list.isLoading ? <Spinner /> : list.data?.items.length === 0 ? (
        <EmptyState title="No resumes yet" body="Upload your resume to check its structure and see which skills it shows." />
      ) : (
        <div className="grid gap-5 lg:grid-cols-[18rem_1fr]">
          <ul className="space-y-2">{list.data?.items.map((r) => (
            <li key={r.id}><button onClick={() => setSelected(r.id)} className={`w-full rounded-card border p-3 text-left text-sm ${selected === r.id ? "border-teal bg-teal-tint" : "border-line bg-white"}`}>
              <span className="block truncate font-semibold">{r.original_filename}</span><span className="text-xs text-ink-faint">{r.file_type.toUpperCase()} · {new Date(r.created_at).toLocaleDateString()}</span></button></li>))}</ul>
          <div>
            {!selected && <p className="text-sm text-ink-soft">Select a resume to see its analysis.</p>}
            {detail.isLoading && selected && <Spinner />}
            {a && (
              <div className="space-y-5">
                <div className="flex flex-wrap gap-2">
                  <Button variant="secondary" onClick={() => api.download(`/resumes/${selected}/download`, detail.data.original_filename)}><Download className="h-4 w-4" aria-hidden />Original file</Button>
                  <Button variant="secondary" onClick={() => api.download(`/resumes/${selected}/report`, "resume-analysis.md")}><Download className="h-4 w-4" aria-hidden />Analysis report</Button>
                  <Button variant="danger" onClick={() => setToDelete(detail.data)}><Trash2 className="h-4 w-4" aria-hidden />Delete</Button>
                </div>
                <Card><h2>What we found</h2>
                  <p className="mt-2 text-sm text-ink-soft">Sections: {a.sections_found.join(", ") || "none detected"} · {a.stats.word_count} words · {a.stats.bullet_count} bullet points</p>
                  <div className="mt-3 flex flex-wrap gap-2">{Object.keys(a.skills_detected).map((s) => <Badge key={s} tone="teal">{s}</Badge>)}</div>
                </Card>
                <Card><h2>Checks</h2>
                  {a.warnings.length ? <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{a.warnings.map((w: string) => <li key={w}>{w}</li>)}</ul> : <p className="mt-2 text-sm text-teal-dark">No structural problems detected.</p>}
                </Card>
                <Card><h2>Suggestions <Badge>rule-based</Badge></h2>
                  {a.suggestions.length ? <ul className="mt-2 space-y-2 text-sm">{a.suggestions.map((s: any, i: number) => <li key={i}>{s.kind === "weak_opening" && <q className="text-ink-soft">{s.text}</q>} {s.advice}</li>)}</ul> : <p className="mt-2 text-sm text-ink-soft">No wording issues spotted.</p>}
                </Card>
                <Card><div className="flex items-center justify-between gap-3"><h2>AI suggestions <Badge tone="signal">AI-generated</Badge></h2>
                  <Button variant="secondary" busy={aiSug.isPending} onClick={() => aiSug.mutate(selected!)}>Generate</Button></div>
                  <p className="mt-1 text-xs text-ink-faint">Uses a local model only if it is running. Suggestions are advice about wording; they never add facts to your resume.</p>
                  {detail.data.ai_suggestions?.length ? <ul className="mt-3 space-y-2 text-sm">{detail.data.ai_suggestions.map((s: any, i: number) => <li key={i}><q className="text-ink-soft">{s.original}</q> {s.advice}</li>)}</ul> : null}
                </Card>
              </div>)}
          </div>
        </div>)}
      <ConfirmDialog open={!!toDelete} title="Delete this resume?" body="This deletes the file, its analysis, and any job analyses made with it. This cannot be undone." confirmLabel="Delete resume" busy={del.isPending} onCancel={() => setToDelete(null)} onConfirm={() => del.mutate(toDelete.id)} />
    </>
  );
}
