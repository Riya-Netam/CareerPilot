import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, ErrorNote, Field, Input, PageHeader, Select, Spinner } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { api } from "../services/api";
import type { Page } from "../types";

const TABS = ["Overview", "Users", "Audit log", "AI & health", "Errors", "Skills"] as const;

export function AdminPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Overview");
  return (
    <>
      <PageHeader title="Admin" subtitle="Aggregate platform data only. User resumes, letters and notes are never shown here." />
      <div role="tablist" aria-label="Admin sections" className="mb-5 flex flex-wrap gap-2">{TABS.map((t) => <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)} className={`rounded-md px-3 py-1.5 text-sm font-semibold ${tab === t ? "bg-ink text-white" : "border border-line bg-white"}`}>{t}</button>)}</div>
      {tab === "Overview" && <Overview />}{tab === "Users" && <Users />}{tab === "Audit log" && <Audit />}{tab === "AI & health" && <Health />}{tab === "Errors" && <Errors />}{tab === "Skills" && <Skills />}
    </>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) { return <div><dt className="text-xs text-ink-faint">{label}</dt><dd className="text-2xl font-bold">{value}</dd></div>; }

function Overview() {
  const q = useQuery({ queryKey: ["admin", "overview"], queryFn: () => api.get<any>("/admin/overview") });
  if (q.isLoading) return <Spinner />; if (q.error) return <ErrorNote error={q.error} />;
  const d = q.data;
  return <div className="grid gap-5 sm:grid-cols-2">
    <Card><h2>Users</h2><dl className="mt-3 grid grid-cols-2 gap-3"><Stat label="Total" value={d.users.total} /><Stat label="Active" value={d.users.active} /><Stat label="Verified" value={d.users.verified} /><Stat label="New (7 days)" value={d.users.new_last_7_days} /></dl></Card>
    <Card><h2>Usage</h2><dl className="mt-3 grid grid-cols-2 gap-3"><Stat label="Resumes" value={d.usage.resumes} /><Stat label="Job analyses" value={d.usage.job_analyses} /><Stat label="Cover letters" value={d.usage.cover_letters} /><Stat label="Applications" value={d.usage.applications} /></dl></Card>
    <Card><h2>AI requests</h2><dl className="mt-3 grid grid-cols-2 gap-3"><Stat label="Total" value={d.ai.requests_total} /><Stat label="Failed" value={d.ai.failures_total} /><Stat label="Last 24h" value={d.ai.requests_last_24h} /><Stat label="Failed (24h)" value={d.ai.failures_last_24h} /></dl></Card>
    <Card><h2>Errors (24h)</h2><p className="mt-3 text-2xl font-bold">{d.errors_last_24h}</p></Card></div>;
}

function Users() {
  const { user: me } = useAuth();
  const qc = useQueryClient(); const toast = useToast();
  const [f, setF] = useState({ q: "", role: "", page: 1 });
  const q = useQuery({ queryKey: ["admin", "users", f], queryFn: () => api.get<Page<any>>(`/admin/users?${new URLSearchParams({ page: String(f.page), ...(f.q ? { q: f.q } : {}), ...(f.role ? { role: f.role } : {}) })}`) });
  const act = useMutation({ mutationFn: ({ id, on }: { id: string; on: boolean }) => api.post(`/admin/users/${id}/${on ? "reactivate" : "disable"}`), onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin"] }); toast("success", "Account updated."); }, onError: (e) => toast("error", (e as Error).message) });
  return <>
    <div className="mb-3 flex flex-wrap gap-2"><Input aria-label="Search users" placeholder="Search name or email" className="max-w-xs" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value, page: 1 })} />
      <Select aria-label="Role" className="!w-40" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value, page: 1 })}><option value="">All roles</option><option>USER</option><option>ADMIN</option><option>SUPER_ADMIN</option></Select></div>
    {q.isLoading ? <Spinner /> : <div className="overflow-x-auto rounded-card border border-line bg-white"><table className="w-full text-left text-sm"><thead className="bg-paper text-xs uppercase text-ink-faint"><tr><th className="p-3">User</th><th className="p-3">Role</th><th className="p-3">Status</th><th className="p-3">Joined</th><th className="p-3"><span className="sr-only">Actions</span></th></tr></thead>
      <tbody>{q.data?.items.map((u) => <tr key={u.id} className="border-t border-line"><td className="p-3"><span className="font-semibold">{u.full_name}</span><br /><span className="text-ink-soft">{u.email}</span></td><td className="p-3">{u.role}</td><td className="p-3">{u.is_active ? <Badge tone="teal">Active</Badge> : <Badge tone="clay">Disabled</Badge>}{!u.email_verified && <> <Badge>Unverified</Badge></>}</td><td className="p-3 text-ink-soft">{new Date(u.created_at).toLocaleDateString()}</td>
        <td className="p-3 text-right">{u.id !== me?.id && <Button variant="secondary" onClick={() => act.mutate({ id: u.id, on: !u.is_active })}>{u.is_active ? "Disable" : "Reactivate"}</Button>}</td></tr>)}</tbody></table></div>}
    {q.data && <div className="mt-3 flex items-center justify-between text-sm"><span>{q.data.total} users</span><div className="flex gap-2"><Button variant="secondary" disabled={f.page <= 1} onClick={() => setF({ ...f, page: f.page - 1 })}>Previous</Button><Button variant="secondary" disabled={f.page * q.data.page_size >= q.data.total} onClick={() => setF({ ...f, page: f.page + 1 })}>Next</Button></div></div>}
  </>;
}

function Audit() {
  const q = useQuery({ queryKey: ["admin", "audit"], queryFn: () => api.get<Page<any>>("/admin/audit-logs") });
  if (q.isLoading) return <Spinner />;
  return <Card><h2>Recent admin actions</h2><ul className="mt-3 space-y-1 text-sm">{q.data?.items.map((a) => <li key={a.id}><time className="text-ink-faint">{new Date(a.created_at).toLocaleString()}</time> · <strong>{a.action}</strong> by {a.actor ?? "system"}{a.target_id ? ` on ${a.target_type} ${String(a.target_id).slice(0, 8)}` : ""}</li>)}{q.data?.items.length === 0 && <li className="text-ink-soft">No actions recorded yet.</li>}</ul></Card>;
}

function Health() {
  const h = useQuery({ queryKey: ["admin", "health"], queryFn: () => api.get<any>("/admin/health") });
  const ai = useQuery({ queryKey: ["admin", "ai"], queryFn: () => api.get<any>("/admin/ai") });
  if (h.isLoading || ai.isLoading) return <Spinner />;
  const ok = (b: boolean) => <Badge tone={b ? "teal" : "clay"}>{b ? "OK" : "Problem"}</Badge>;
  return <div className="grid gap-5 sm:grid-cols-2">
    <Card><h2>Dependencies</h2><ul className="mt-3 space-y-2 text-sm"><li>Database {ok(h.data.database.ok)}</li><li>File storage {ok(h.data.storage.ok)}</li><li>Local AI model {ok(h.data.ai.ok)} <span className="text-ink-soft">{h.data.ai.detail}</span></li></ul><p className="mt-3 text-xs text-ink-faint">{ai.data.note}</p></Card>
    <Card><h2>Configuration checks</h2><ul className="mt-3 space-y-1 text-sm">{Object.entries(h.data.config_checks).map(([k, v]) => <li key={k} className="flex justify-between gap-2"><span>{k.replace(/_/g, " ")}</span><span className="font-semibold">{String(v)}</span></li>)}</ul></Card>
    <Card className="sm:col-span-2"><h2>Recent AI requests</h2><ul className="mt-3 space-y-1 text-sm">{ai.data.recent.map((r: any, i: number) => <li key={i}>{r.feature} · {r.success ? "ok" : `failed (${r.error})`} · {r.duration_ms} ms</li>)}{ai.data.recent.length === 0 && <li className="text-ink-soft">No AI requests yet.</li>}</ul></Card></div>;
}

function Errors() {
  const q = useQuery({ queryKey: ["admin", "errors"], queryFn: () => api.get<Page<any>>("/admin/errors") });
  if (q.isLoading) return <Spinner />;
  return <Card><h2>Server errors</h2><ul className="mt-3 space-y-1 text-sm">{q.data?.items.map((e) => <li key={e.id}><time className="text-ink-faint">{new Date(e.created_at).toLocaleString()}</time> · {e.method} {e.path} · {e.error_type} · <code>{e.request_id}</code></li>)}{q.data?.items.length === 0 && <li className="text-ink-soft">No errors recorded.</li>}</ul></Card>;
}

function Skills() {
  const qc = useQueryClient(); const toast = useToast();
  const q = useQuery({ queryKey: ["admin", "taxonomy"], queryFn: () => api.get<any>("/admin/taxonomy") });
  const [s, setS] = useState({ name: "", category: "tools", aliases: "" });
  const add = useMutation({ mutationFn: () => api.post("/admin/taxonomy", { name: s.name, category: s.category, aliases: s.aliases.split(",").map((x) => x.trim()).filter(Boolean) }), onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin", "taxonomy"] }); setS({ name: "", category: "tools", aliases: "" }); toast("success", "Skill added."); } });
  if (q.isLoading) return <Spinner />;
  return <div className="grid gap-5 lg:grid-cols-[20rem_1fr]">
    <Card className="space-y-3"><h2>Add a skill</h2>
      <Field id="sk" label="Name"><Input id="sk" value={s.name} onChange={(e) => setS({ ...s, name: e.target.value })} /></Field>
      <Field id="cat" label="Category"><Select id="cat" value={s.category} onChange={(e) => setS({ ...s, category: e.target.value })}>{Object.entries(q.data.categories).map(([k, v]) => <option key={k} value={k}>{v as string}</option>)}</Select></Field>
      <Field id="al" label="Aliases (comma separated)"><Input id="al" value={s.aliases} onChange={(e) => setS({ ...s, aliases: e.target.value })} /></Field>
      <ErrorNote error={add.error} /><Button busy={add.isPending} disabled={!s.name.trim()} onClick={() => add.mutate()}>Add skill</Button></Card>
    <Card><h2>Taxonomy ({q.data.items.length} shown)</h2><ul className="mt-3 max-h-96 divide-y divide-line overflow-auto text-sm">{q.data.items.map((i: any) => <li key={i.id} className="py-1.5"><strong>{i.name}</strong> {i.is_custom && <Badge tone="signal">custom</Badge>} <span className="text-ink-faint">{i.aliases.slice(0, 5).join(", ")}</span></li>)}</ul></Card></div>;
}
