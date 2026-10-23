import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, ConfirmDialog, ErrorNote, Field, Input, PageHeader } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { api } from "../services/api";
import { passwordRule } from "../schemas/auth";

export function ProfilePage() {
  const { user, refresh } = useAuth();
  const toast = useToast();
  const [name, setName] = useState(user?.full_name ?? "");
  const m = useMutation({ mutationFn: () => api.patch("/users/me", { full_name: name }), onSuccess: async () => { await refresh(); toast("success", "Profile updated."); } });
  return (
    <>
      <PageHeader title="Profile" />
      <Card className="max-w-lg space-y-4">
        <Field id="email" label="Email"><Input id="email" value={user?.email ?? ""} readOnly /></Field>
        <Field id="name" label="Full name"><Input id="name" value={name} onChange={(e) => setName(e.target.value)} maxLength={120} /></Field>
        <p className="text-xs text-ink-faint">Account type: {user?.role === "USER" ? "Standard" : user?.role}</p>
        <ErrorNote error={m.error} />
        <Button busy={m.isPending} disabled={!name.trim() || name === user?.full_name} onClick={() => m.mutate()}>Save changes</Button>
      </Card>
    </>
  );
}

export function SettingsPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const toast = useToast();
  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  const [pwErr, setPwErr] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);
  const [delPw, setDelPw] = useState("");
  const change = useMutation({ mutationFn: () => api.post("/auth/change-password", pw), onSuccess: () => { setPw({ current_password: "", new_password: "" }); toast("success", "Password changed. Other devices were signed out."); } });
  const remove = useMutation({ mutationFn: () => api.del("/users/me", { password: delPw }), onSuccess: () => { qc.clear(); navigate("/login"); } });
  return (
    <>
      <PageHeader title="Settings" />
      <div className="max-w-lg space-y-5">
        <Card className="space-y-4"><h2>Change password</h2>
          <Field id="cur" label="Current password"><Input id="cur" type="password" autoComplete="current-password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></Field>
          <Field id="new" label="New password" hint="At least 10 characters, with letters and numbers." error={pwErr ?? undefined}><Input id="new" type="password" autoComplete="new-password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></Field>
          <ErrorNote error={change.error} />
          <Button busy={change.isPending} onClick={() => { const r = passwordRule.safeParse(pw.new_password); setPwErr(r.success ? null : r.error.issues[0].message); if (r.success) change.mutate(); }}>Update password</Button>
        </Card>
        <Card className="space-y-3 border-clay"><h2>Delete account</h2>
          <p className="text-sm text-ink-soft">Permanently deletes your account, resumes, analyses, roadmaps, cover letters and applications.</p>
          <Button variant="danger" onClick={() => setConfirm(true)}>Delete my account</Button>
        </Card>
      </div>
      <ConfirmDialog open={confirm} title="Delete your account?" body="This cannot be undone. Enter your password below, then confirm." confirmLabel="Delete everything" busy={remove.isPending} onCancel={() => setConfirm(false)} onConfirm={() => remove.mutate()} />
      {confirm && <div className="fixed inset-x-0 bottom-24 z-50 mx-auto w-full max-w-md px-4"><Input aria-label="Confirm password" type="password" placeholder="Your password" value={delPw} onChange={(e) => setDelPw(e.target.value)} /><ErrorNote error={remove.error} /></div>}
    </>
  );
}
