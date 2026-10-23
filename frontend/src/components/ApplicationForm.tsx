import { useState } from "react";
import { Button, Field, Input, Select, Textarea } from "./ui";
import { APPLICATION_STATUSES, type Application } from "../types";

export type AppValues = { company: string; job_title: string; job_url: string; status: string; applied_on: string; deadline: string; notes: string };

export function toValues(a?: Application | null): AppValues {
  return { company: a?.company ?? "", job_title: a?.job_title ?? "", job_url: a?.job_url ?? "", status: a?.status ?? "SAVED", applied_on: a?.applied_on ?? "", deadline: a?.deadline ?? "", notes: a?.notes ?? "" };
}

export function ApplicationForm({ initial, busy, onSubmit, onCancel }: { initial?: Application | null; busy?: boolean; onSubmit: (v: Record<string, unknown>) => void; onCancel: () => void }) {
  const [v, setV] = useState<AppValues>(toValues(initial));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const set = (k: keyof AppValues) => (e: React.ChangeEvent<any>) => setV({ ...v, [k]: e.target.value });
  function submit(e: React.FormEvent) {
    e.preventDefault();
    const err: Record<string, string> = {};
    if (!v.company.trim()) err.company = "Enter the company name.";
    if (!v.job_title.trim()) err.job_title = "Enter the job title.";
    if (v.job_url && !/^https?:\/\//i.test(v.job_url)) err.job_url = "Use a full link starting with http:// or https://";
    setErrors(err);
    if (Object.keys(err).length) return;
    onSubmit({ company: v.company.trim(), job_title: v.job_title.trim(), job_url: v.job_url || null, status: v.status, applied_on: v.applied_on || null, deadline: v.deadline || null, notes: v.notes || null });
  }
  return (
    <form onSubmit={submit} className="space-y-3" noValidate aria-label={initial ? "Edit application" : "Add application"}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field id="company" label="Company" error={errors.company}><Input id="company" value={v.company} onChange={set("company")} /></Field>
        <Field id="job_title" label="Job title" error={errors.job_title}><Input id="job_title" value={v.job_title} onChange={set("job_title")} /></Field>
        <Field id="status" label="Status"><Select id="status" value={v.status} onChange={set("status")}>{APPLICATION_STATUSES.map((s) => <option key={s} value={s}>{s[0] + s.slice(1).toLowerCase()}</option>)}</Select></Field>
        <Field id="job_url" label="Application link" error={errors.job_url}><Input id="job_url" value={v.job_url} onChange={set("job_url")} placeholder="https://" /></Field>
        <Field id="applied_on" label="Date applied"><Input id="applied_on" type="date" value={v.applied_on} onChange={set("applied_on")} /></Field>
        <Field id="deadline" label="Deadline"><Input id="deadline" type="date" value={v.deadline} onChange={set("deadline")} /></Field>
      </div>
      <Field id="notes" label="Notes"><Textarea id="notes" rows={3} value={v.notes} onChange={set("notes")} maxLength={5000} /></Field>
      <div className="flex gap-2"><Button type="submit" busy={busy}>Save</Button><Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button></div>
    </form>
  );
}
