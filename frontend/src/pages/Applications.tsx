import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { ApplicationForm } from "../components/ApplicationForm";
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorNote, Input, PageHeader, Select, Spinner } from "../components/ui";
import { useToast } from "../hooks/useToast";
import { api } from "../services/api";
import { APPLICATION_STATUSES, type Application, type Page } from "../types";

const tone: Record<string, "teal" | "signal" | "clay" | "neutral"> = { OFFER: "teal", APPLIED: "signal", ASSESSMENT: "signal", INTERVIEWING: "signal", REJECTED: "clay", WITHDRAWN: "neutral", SAVED: "neutral" };

export function ApplicationsPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [filters, setFilters] = useState({ q: "", status: "", sort: "created", order: "desc", page: 1 });
  const [editing, setEditing] = useState<Application | "new" | null>(null);
  const [toDelete, setToDelete] = useState<Application | null>(null);
  const qs = new URLSearchParams({ sort: filters.sort, order: filters.order, page: String(filters.page), page_size: "10", ...(filters.q ? { q: filters.q } : {}), ...(filters.status ? { status: filters.status } : {}) });
  const list = useQuery({ queryKey: ["applications", filters], queryFn: () => api.get<Page<Application>>(`/applications?${qs}`), placeholderData: keepPreviousData });
  const summary = useQuery({ queryKey: ["app-summary"], queryFn: () => api.get<any>("/applications/summary") });
  const refresh = () => { qc.invalidateQueries({ queryKey: ["applications"] }); qc.invalidateQueries({ queryKey: ["app-summary"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); };
  const save = useMutation({
    mutationFn: (v: Record<string, unknown>) => editing && editing !== "new" ? api.patch(`/applications/${editing.id}`, v) : api.post("/applications", v),
    onSuccess: () => { refresh(); setEditing(null); toast("success", "Application saved."); },
  });
  const del = useMutation({ mutationFn: (id: string) => api.del(`/applications/${id}`), onSuccess: () => { refresh(); setToDelete(null); toast("success", "Application deleted."); } });
  const totalPages = list.data ? Math.max(1, Math.ceil(list.data.total / list.data.page_size)) : 1;
  const set = (patch: Partial<typeof filters>) => setFilters({ ...filters, page: 1, ...patch });

  return (
    <>
      <PageHeader title="Job Applications" subtitle="Keep track of where you applied and what is next." actions={
        <div className="flex gap-2"><Button variant="secondary" onClick={() => api.download("/applications/export.csv", "applications.csv")}><Download className="h-4 w-4" aria-hidden />Export CSV</Button>
          <Button onClick={() => setEditing("new")}><Plus className="h-4 w-4" aria-hidden />Add application</Button></div>} />
      {summary.data && summary.data.total > 0 && (
        <div className="mb-5 flex flex-wrap gap-2" aria-label="Status summary">{APPLICATION_STATUSES.map((s) => <button key={s} onClick={() => set({ status: filters.status === s ? "" : s })} className={`rounded-full border px-3 py-1 text-xs font-semibold ${filters.status === s ? "border-ink bg-ink text-white" : "border-line bg-white"}`}>{s[0] + s.slice(1).toLowerCase()} · {summary.data.by_status[s]}</button>)}</div>)}
      {summary.data?.upcoming_deadlines.length > 0 && <Card className="mb-5"><h2>Upcoming deadlines</h2><ul className="mt-2 text-sm">{summary.data.upcoming_deadlines.map((a: Application) => <li key={a.id}><strong>{a.deadline}</strong> · {a.job_title} at {a.company}</li>)}</ul></Card>}
      {editing && <Card className="mb-5"><h2 className="mb-3">{editing === "new" ? "Add application" : "Edit application"}</h2><ErrorNote error={save.error} /><ApplicationForm initial={editing === "new" ? null : editing} busy={save.isPending} onSubmit={(v) => save.mutate(v)} onCancel={() => setEditing(null)} /></Card>}
      <div className="mb-3 flex flex-wrap gap-2">
        <Input aria-label="Search applications" placeholder="Search company, title or notes" className="max-w-xs" value={filters.q} onChange={(e) => set({ q: e.target.value })} />
        <Select aria-label="Sort by" className="!w-40" value={filters.sort} onChange={(e) => set({ sort: e.target.value })}><option value="created">Newest added</option><option value="deadline">Deadline</option><option value="company">Company</option><option value="applied">Date applied</option><option value="status">Status</option></Select>
        <Select aria-label="Order" className="!w-32" value={filters.order} onChange={(e) => set({ order: e.target.value })}><option value="desc">Descending</option><option value="asc">Ascending</option></Select>
      </div>
      {list.isLoading ? <Spinner /> : list.data?.items.length === 0 ? <EmptyState title={filters.q || filters.status ? "No matches" : "No applications yet"} body={filters.q || filters.status ? "Try a different search or filter." : "Add a job you are interested in or have applied to."} /> : (
        <div className="overflow-x-auto rounded-card border border-line bg-white"><table className="w-full text-left text-sm">
          <thead className="bg-paper text-xs uppercase text-ink-faint"><tr><th className="p-3">Company</th><th className="p-3">Role</th><th className="p-3">Status</th><th className="p-3">Deadline</th><th className="p-3"><span className="sr-only">Actions</span></th></tr></thead>
          <tbody>{list.data?.items.map((a) => (
            <tr key={a.id} className="border-t border-line"><td className="p-3 font-semibold">{a.company}</td>
              <td className="p-3">{a.job_url ? <a className="underline" href={a.job_url} target="_blank" rel="noopener noreferrer">{a.job_title}</a> : a.job_title}</td>
              <td className="p-3"><Badge tone={tone[a.status]}>{a.status[0] + a.status.slice(1).toLowerCase()}</Badge></td><td className="p-3 text-ink-soft">{a.deadline ?? "–"}</td>
              <td className="p-3 text-right"><button aria-label={`Edit ${a.job_title} at ${a.company}`} className="p-1" onClick={() => setEditing(a)}><Pencil className="h-4 w-4" /></button><button aria-label={`Delete ${a.job_title} at ${a.company}`} className="p-1 text-clay" onClick={() => setToDelete(a)}><Trash2 className="h-4 w-4" /></button></td></tr>))}</tbody>
        </table></div>)}
      {list.data && list.data.total > list.data.page_size && <div className="mt-3 flex items-center justify-between text-sm"><span>Page {filters.page} of {totalPages}</span><div className="flex gap-2"><Button variant="secondary" disabled={filters.page <= 1} onClick={() => setFilters({ ...filters, page: filters.page - 1 })}>Previous</Button><Button variant="secondary" disabled={filters.page >= totalPages} onClick={() => setFilters({ ...filters, page: filters.page + 1 })}>Next</Button></div></div>}
      <ConfirmDialog open={!!toDelete} title="Delete this application?" body={`${toDelete?.job_title} at ${toDelete?.company} will be removed.`} confirmLabel="Delete" busy={del.isPending} onCancel={() => setToDelete(null)} onConfirm={() => toDelete && del.mutate(toDelete.id)} />
    </>
  );
}
