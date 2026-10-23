import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApplicationForm } from "../components/ApplicationForm";
import { ComparisonView } from "../components/ComparisonView";
import { AdminRoute, ProtectedRoute } from "../components/RouteGuards";
import { Progress } from "../components/ui";
import { AuthContext, AuthState } from "../hooks/useAuth";
import { LoginPage, RegisterPage } from "../pages/Auth";
import { loginSchema, registerSchema } from "../schemas/auth";
import { validateResumeFile } from "../utils/validate";
import type { Comparison } from "../types";

const auth = (user: AuthState["user"], loading = false): AuthState => ({ user, loading, refresh: async () => {}, signOut: async () => {} });
const person = (role: "USER" | "ADMIN") => ({ id: "1", email: "a@b.c", full_name: "A B", role, email_verified_at: "x", created_at: "x" });

function wrap(ui: React.ReactNode, state: AuthState = auth(null), path = "/") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><AuthContext.Provider value={state}><MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter></AuthContext.Provider></QueryClientProvider>);
}
afterEach(() => vi.restoreAllMocks());

describe("auth forms", () => {
  it("login shows validation errors and does not call the API", async () => {
    const f = vi.spyOn(globalThis, "fetch");
    wrap(<LoginPage />);
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByText("Enter a valid email.")).toBeInTheDocument();
    expect(f).not.toHaveBeenCalled();
  });
  it("register enforces the password rule", async () => {
    wrap(<RegisterPage />);
    await userEvent.type(screen.getByLabelText("Full name"), "Riya");
    await userEvent.type(screen.getByLabelText("Email"), "riya@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "short");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));
    expect(await screen.findByText(/at least 10 characters/i, { selector: "p[role=alert]" })).toBeInTheDocument();
  });
  it("schemas accept good input and reject bad input", () => {
    expect(loginSchema.safeParse({ email: "a@b.co", password: "x" }).success).toBe(true);
    expect(registerSchema.safeParse({ full_name: "R", email: "a@b.co", password: "abcdefghij" }).success).toBe(false);
    expect(registerSchema.safeParse({ full_name: "R", email: "a@b.co", password: "abcdefghi1" }).success).toBe(true);
  });
});

describe("protected navigation", () => {
  const routes = <Routes><Route path="/login" element={<p>login page</p>} /><Route element={<ProtectedRoute />}><Route path="/" element={<p>private</p>} /></Route>
    <Route element={<AdminRoute />}><Route path="/admin" element={<p>admin area</p>} /></Route></Routes>;
  it("redirects anonymous users to login", () => { wrap(routes, auth(null), "/"); expect(screen.getByText("login page")).toBeInTheDocument(); });
  it("lets signed-in users in", () => { wrap(routes, auth(person("USER")), "/"); expect(screen.getByText("private")).toBeInTheDocument(); });
  it("keeps normal users out of admin", () => { wrap(routes, auth(person("USER")), "/admin"); expect(screen.queryByText("admin area")).not.toBeInTheDocument(); });
  it("lets admins into admin", () => { wrap(routes, auth(person("ADMIN")), "/admin"); expect(screen.getByText("admin area")).toBeInTheDocument(); });
});

describe("resume upload validation", () => {
  it("accepts pdf and docx", () => { expect(validateResumeFile({ name: "cv.PDF", size: 1000 })).toBeNull(); expect(validateResumeFile({ name: "cv.docx", size: 1000 })).toBeNull(); });
  it("rejects other types, empty and oversize files", () => {
    expect(validateResumeFile({ name: "cv.exe", size: 1000 })).toMatch(/PDF or DOCX/);
    expect(validateResumeFile({ name: "cv.pdf", size: 0 })).toMatch(/empty/);
    expect(validateResumeFile({ name: "cv.pdf", size: 6 * 1024 * 1024 })).toMatch(/larger/);
  });
});

const comparison: Comparison = {
  score: 62.5,
  score_explanation: { formula: "100 x (sum of weight x credit) / (sum of weights)", weights: { required: 3, uncertain: 2, preferred: 1 }, credits: { demonstrated: 1, listed: 0.6, not_found: 0 }, total_weight: 8, earned_points: 5, disclaimer: "This is not a prediction of interviews or job offers." },
  coverage: { required: { total: 2, demonstrated: 1, listed: 0, not_found: 1, percent: 50 }, preferred: { total: 1, demonstrated: 0, listed: 0, not_found: 1, percent: 0 }, uncertain: { total: 0, demonstrated: 0, listed: 0, not_found: 0, percent: null } },
  items: [], matched: [{ skill: "Python", category: "programming_language", level: "required", confidence: "high", reason: "Sentence contains \"strong\"", evidence: [{ section: "projects", snippet: "Built a quiz app with Python" }], status: "demonstrated", weight: 3, credit: 1, points: 3 }],
  not_found: [{ skill: "Kubernetes", category: "cloud_devops", level: "required", confidence: "high", reason: "Listed under requirements", evidence: [], status: "not_found", weight: 3, credit: 0, points: 0 }],
  manual_confirmation: [{ kind: "education", skill: null, note: "Confirm yourself: \"Bachelor's degree\"" }],
  priorities: [{ skill: "Kubernetes", priority: "high", why: "Required by the posting and not found in your resume." }],
};

describe("job analysis rendering", () => {
  it("shows matched skills with evidence, missing skills with careful wording, score and disclaimer", () => {
    render(<ComparisonView c={comparison} />);
    expect(screen.getByLabelText(/Alignment score 62.5/)).toBeInTheDocument();
    expect(screen.getByText(/Built a quiz app with Python/)).toBeInTheDocument();
    expect(screen.getByText(/Not found in your resume \(1\)/)).toBeInTheDocument();
    expect(screen.getAllByText("Kubernetes").length).toBeGreaterThan(0);
    expect(screen.getByText(/not a prediction/i)).toBeInTheDocument();
    expect(screen.getByText(/Please confirm yourself/)).toBeInTheDocument();
    expect(screen.queryByText(/lacks|do not have/i)).not.toBeInTheDocument();
  });
  it("renders without a score for empty postings", () => {
    render(<ComparisonView c={{ ...comparison, score: null, matched: [], not_found: [], priorities: [], manual_confirmation: [] }} />);
    expect(screen.getByText(/No score/)).toBeInTheDocument();
  });
});

describe("roadmap progress", () => {
  it("exposes progress accessibly", () => {
    render(<Progress percent={40} label="Roadmap progress" />);
    expect(screen.getByRole("progressbar", { name: "Roadmap progress" })).toHaveAttribute("aria-valuenow", "40");
  });
});

describe("application editing", () => {
  const app = { id: "1", company: "Acme", job_title: "Dev", job_url: null, status: "SAVED", applied_on: null, deadline: null, notes: null, analysis_id: null };
  it("pre-fills, validates and submits changes", async () => {
    const onSubmit = vi.fn();
    render(<ApplicationForm initial={app} onSubmit={onSubmit} onCancel={() => {}} />);
    expect(screen.getByLabelText("Company")).toHaveValue("Acme");
    await userEvent.clear(screen.getByLabelText("Company"));
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Enter the company name.")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
    await userEvent.type(screen.getByLabelText("Company"), "Globex");
    await userEvent.selectOptions(screen.getByLabelText("Status"), "INTERVIEWING");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ company: "Globex", status: "INTERVIEWING" })));
  });
  it("rejects non-http links", async () => {
    render(<ApplicationForm onSubmit={vi.fn()} onCancel={() => {}} />);
    await userEvent.type(screen.getByLabelText("Company"), "A"); await userEvent.type(screen.getByLabelText("Job title"), "B");
    await userEvent.type(screen.getByLabelText("Application link"), "javascript:alert(1)");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText(/full link starting with http/)).toBeInTheDocument();
  });
});
