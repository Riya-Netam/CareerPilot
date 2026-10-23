import { ReactNode } from "react";

export function AuthLayout({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-paper p-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center gap-2">
          <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden><rect width="32" height="32" rx="7" fill="#10243A" /><path d="M16 6l6 18-6-4-6 4z" fill="#E39B1B" /></svg>
          <span className="text-xl font-bold tracking-tight">CareerPilot AI</span>
        </div>
        <div className="rounded-card border border-line bg-white p-6">
          <h1>{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-ink-soft">{subtitle}</p>}
          <div className="mt-5">{children}</div>
        </div>
      </div>
    </div>
  );
}
