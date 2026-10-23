import { Briefcase, FileText, LayoutDashboard, LogOut, Map, Menu, PenLine, Settings, ShieldCheck, Target, User as UserIcon } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/resumes", label: "My Resumes", icon: FileText },
  { to: "/analyzer", label: "Job Skill Analyzer", icon: Target },
  { to: "/roadmaps", label: "Learning Roadmaps", icon: Map },
  { to: "/cover-letters", label: "Cover Letters", icon: PenLine },
  { to: "/applications", label: "Job Applications", icon: Briefcase },
  { to: "/profile", label: "Profile", icon: UserIcon },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function AppLayout() {
  const { user, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const link = ({ isActive }: { isActive: boolean }) => `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium ${isActive ? "bg-white/15 text-white" : "text-white/70 hover:bg-white/10 hover:text-white"}`;
  return (
    <div className="min-h-screen lg:flex">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2">Skip to content</a>
      <header className="flex items-center justify-between bg-ink px-4 py-3 text-white lg:hidden">
        <span className="font-bold">CareerPilot AI</span>
        <button aria-label="Toggle navigation" aria-expanded={open} onClick={() => setOpen(!open)}><Menu /></button>
      </header>
      <aside className={`${open ? "block" : "hidden"} w-full shrink-0 bg-ink p-4 text-white lg:sticky lg:top-0 lg:block lg:h-screen lg:w-64`}>
        <div className="mb-6 hidden items-center gap-2 px-2 lg:flex">
          <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden><rect width="32" height="32" rx="7" fill="#1B7A8C" /><path d="M16 6l6 18-6-4-6 4z" fill="#E39B1B" /></svg>
          <span className="text-lg font-bold tracking-tight">CareerPilot AI</span>
        </div>
        <nav aria-label="Main" className="space-y-1">
          {nav.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} className={link} onClick={() => setOpen(false)}><Icon className="h-4 w-4" aria-hidden />{label}</NavLink>)}
          {user && user.role !== "USER" && <NavLink to="/admin" className={link} onClick={() => setOpen(false)}><ShieldCheck className="h-4 w-4" aria-hidden />Admin</NavLink>}
        </nav>
        <div className="mt-6 border-t border-white/15 pt-4 text-sm">
          <p className="truncate px-2 text-white/80">{user?.full_name}</p>
          <button className="mt-2 flex w-full items-center gap-3 rounded-md px-3 py-2 text-white/70 hover:bg-white/10 hover:text-white" onClick={async () => { await signOut(); navigate("/login"); }}><LogOut className="h-4 w-4" aria-hidden />Sign out</button>
        </div>
      </aside>
      <main id="main" className="min-w-0 flex-1 p-4 sm:p-8"><div className="mx-auto max-w-6xl"><Outlet /></div></main>
    </div>
  );
}
