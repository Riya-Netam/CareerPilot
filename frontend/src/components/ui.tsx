import clsx from "clsx";
import { Loader2 } from "lucide-react";
import { ButtonHTMLAttributes, forwardRef, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes, useEffect, useRef } from "react";

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "ghost"; busy?: boolean };
export function Button({ variant = "primary", busy, className, children, disabled, ...p }: BtnProps) {
  const styles = {
    primary: "bg-ink text-white hover:bg-ink-soft",
    secondary: "border border-line bg-white text-ink hover:bg-paper",
    danger: "bg-clay text-white hover:opacity-90",
    ghost: "text-ink-soft hover:bg-white",
  }[variant];
  return (
    <button {...p} disabled={disabled || busy} className={clsx("inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50", styles, className)}>
      {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}{children}
    </button>
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={clsx("rounded-card border border-line bg-white p-5", className)}>{children}</section>;
}

export function Field({ label, error, hint, children, id }: { label: string; error?: string; hint?: string; children: ReactNode; id: string }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium">{label}</label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-ink-faint">{hint}</p>}
      {error && <p role="alert" className="mt-1 text-xs font-medium text-clay">{error}</p>}
    </div>
  );
}
const inputCls = "w-full rounded-md border border-line bg-white px-3 py-2 text-sm placeholder:text-ink-faint";
export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>((p, r) => <input ref={r} {...p} className={clsx(inputCls, p.className)} />);
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>((p, r) => <textarea ref={r} {...p} className={clsx(inputCls, p.className)} />);
export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>((p, r) => <select ref={r} {...p} className={clsx(inputCls, p.className)} />);

const tones = { teal: "bg-teal-tint text-teal-dark", signal: "bg-signal-tint text-signal-dark", clay: "bg-clay-tint text-clay", neutral: "bg-paper text-ink-soft border border-line" };
export function Badge({ tone = "neutral", children }: { tone?: keyof typeof tones; children: ReactNode }) {
  return <span className={clsx("inline-block rounded px-2 py-0.5 text-xs font-semibold", tones[tone])}>{children}</span>;
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return <div className="flex items-center gap-2 py-10 text-ink-faint" role="status"><Loader2 className="h-5 w-5 animate-spin" aria-hidden />{label}…</div>;
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="rounded-card border border-dashed border-line bg-white px-6 py-10 text-center">
      <p className="font-semibold">{title}</p>
      <p className="mx-auto mt-1 max-w-md text-sm text-ink-soft">{body}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  return <p role="alert" className="rounded-md border border-clay bg-clay-tint px-3 py-2 text-sm text-clay">{(error as Error).message || "Something went wrong."}</p>;
}

export function ConfirmDialog({ open, title, body, confirmLabel, onConfirm, onCancel, busy }: { open: boolean; title: string; body: string; confirmLabel: string; onConfirm: () => void; onCancel: () => void; busy?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { if (open) ref.current?.querySelector<HTMLButtonElement>("button")?.focus(); }, [open]);
  useEffect(() => { const h = (e: KeyboardEvent) => e.key === "Escape" && onCancel(); if (open) window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h); }, [open, onCancel]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-ink/40 p-4">
      <div ref={ref} role="alertdialog" aria-modal="true" aria-labelledby="dlg-title" className="w-full max-w-md rounded-card bg-white p-6">
        <h2 id="dlg-title">{title}</h2>
        <p className="mt-2 text-sm text-ink-soft">{body}</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel}>Cancel</Button>
          <Button variant="danger" busy={busy} onClick={onConfirm}>{confirmLabel}</Button>
        </div>
      </div>
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div><h1>{title}</h1>{subtitle && <p className="mt-1 max-w-2xl text-sm text-ink-soft">{subtitle}</p>}</div>
      {actions}
    </div>
  );
}

export function Progress({ percent, label }: { percent: number; label: string }) {
  return (
    <div role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label={label} className="h-2 w-full overflow-hidden rounded bg-paper">
      <div className="h-full bg-teal" style={{ width: `${percent}%` }} />
    </div>
  );
}
