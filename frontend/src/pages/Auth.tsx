import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";
import { Button, ErrorNote, Field, Input } from "../components/ui";
import { AuthLayout } from "../layouts/AuthLayout";
import { loginSchema, LoginForm, passwordRule, registerSchema, RegisterForm } from "../schemas/auth";
import { api, ApiError } from "../services/api";
import type { User } from "../types";

export function LoginPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const loc = useLocation() as { state?: { from?: string } };
  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });
  const m = useMutation({
    mutationFn: (v: LoginForm) => api.post<User>("/auth/login", v),
    onSuccess: (u) => { qc.setQueryData(["me"], u); navigate(loc.state?.from || "/", { replace: true }); },
  });
  const unverified = m.error instanceof ApiError && m.error.code === "email_not_verified";
  return (
    <AuthLayout title="Sign in" subtitle="Welcome back.">
      <form onSubmit={handleSubmit((v) => m.mutate(v))} className="space-y-4" noValidate>
        <Field id="email" label="Email" error={errors.email?.message}><Input id="email" type="email" autoComplete="email" {...register("email")} /></Field>
        <Field id="password" label="Password" error={errors.password?.message}><Input id="password" type="password" autoComplete="current-password" {...register("password")} /></Field>
        <ErrorNote error={m.error} />
        {unverified && <ResendVerification email={(document.getElementById("email") as HTMLInputElement)?.value} />}
        <Button type="submit" busy={m.isPending} className="w-full">Sign in</Button>
      </form>
      <p className="mt-4 text-sm"><Link className="underline" to="/forgot-password">Forgot your password?</Link></p>
      <p className="mt-2 text-sm text-ink-soft">New here? <Link className="font-semibold underline" to="/register">Create an account</Link></p>
    </AuthLayout>
  );
}

function ResendVerification({ email }: { email: string }) {
  const m = useMutation({ mutationFn: () => api.post("/auth/resend-verification", { email }) });
  return <div className="text-sm"><Button type="button" variant="secondary" busy={m.isPending} onClick={() => m.mutate()}>Resend verification email</Button>{m.isSuccess && <p className="mt-2 text-teal-dark">If that account needs verification, a new email is on its way.</p>}</div>;
}

export function RegisterPage() {
  const { register, handleSubmit, formState: { errors } } = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) });
  const m = useMutation({ mutationFn: (v: RegisterForm) => api.post<{ message: string }>("/auth/register", v) });
  if (m.isSuccess) return (
    <AuthLayout title="Check your email"><p className="text-sm text-ink-soft">We sent a verification link. It is valid for 24 hours. In local development the link is printed in the backend terminal.</p><Link className="mt-4 inline-block text-sm font-semibold underline" to="/login">Back to sign in</Link></AuthLayout>
  );
  return (
    <AuthLayout title="Create your account" subtitle="Free to use. Your data stays private to you.">
      <form onSubmit={handleSubmit((v) => m.mutate(v))} className="space-y-4" noValidate>
        <Field id="full_name" label="Full name" error={errors.full_name?.message}><Input id="full_name" autoComplete="name" {...register("full_name")} /></Field>
        <Field id="email" label="Email" error={errors.email?.message}><Input id="email" type="email" autoComplete="email" {...register("email")} /></Field>
        <Field id="password" label="Password" hint="At least 10 characters, with letters and numbers." error={errors.password?.message}><Input id="password" type="password" autoComplete="new-password" {...register("password")} /></Field>
        <ErrorNote error={m.error} />
        <Button type="submit" busy={m.isPending} className="w-full">Create account</Button>
      </form>
      <p className="mt-4 text-sm text-ink-soft">Already registered? <Link className="font-semibold underline" to="/login">Sign in</Link></p>
    </AuthLayout>
  );
}

export function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [state, setState] = useState<"working" | "ok" | "bad">("working");
  useEffect(() => {
    let live = true;
    api.post("/auth/verify-email", { token }).then(() => live && setState("ok")).catch(() => live && setState("bad"));
    return () => { live = false; };
  }, [token]);
  return (
    <AuthLayout title="Email verification">
      {state === "working" && <p className="text-sm">Verifying…</p>}
      {state === "ok" && <p className="text-sm text-teal-dark">Your email is verified. <Link className="font-semibold underline" to="/login">Sign in</Link></p>}
      {state === "bad" && <p className="text-sm text-clay">This link is invalid or has expired. Sign in to request a new one.</p>}
    </AuthLayout>
  );
}

export function ForgotPasswordPage() {
  const schema = z.object({ email: z.string().email("Enter a valid email.") });
  const { register, handleSubmit, formState: { errors } } = useForm<{ email: string }>({ resolver: zodResolver(schema) });
  const m = useMutation({ mutationFn: (v: { email: string }) => api.post("/auth/forgot-password", v) });
  return (
    <AuthLayout title="Reset your password" subtitle="Enter your email and we will send a reset link.">
      {m.isSuccess ? <p className="text-sm text-teal-dark">If that email has an account, a reset link is on its way. The link works once and expires in 1 hour.</p> : (
        <form onSubmit={handleSubmit((v) => m.mutate(v))} className="space-y-4" noValidate>
          <Field id="email" label="Email" error={errors.email?.message}><Input id="email" type="email" {...register("email")} /></Field>
          <ErrorNote error={m.error} />
          <Button type="submit" busy={m.isPending} className="w-full">Send reset link</Button>
        </form>)}
      <Link className="mt-4 inline-block text-sm underline" to="/login">Back to sign in</Link>
    </AuthLayout>
  );
}

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const schema = z.object({ password: passwordRule });
  const { register, handleSubmit, formState: { errors } } = useForm<{ password: string }>({ resolver: zodResolver(schema) });
  const m = useMutation({ mutationFn: (v: { password: string }) => api.post("/auth/reset-password", { token: params.get("token") || "", ...v }) });
  return (
    <AuthLayout title="Choose a new password">
      {m.isSuccess ? <p className="text-sm text-teal-dark">Password updated. <Link className="font-semibold underline" to="/login">Sign in</Link></p> : (
        <form onSubmit={handleSubmit((v) => m.mutate(v))} className="space-y-4" noValidate>
          <Field id="password" label="New password" hint="At least 10 characters, with letters and numbers." error={errors.password?.message}><Input id="password" type="password" autoComplete="new-password" {...register("password")} /></Field>
          <ErrorNote error={m.error} />
          <Button type="submit" busy={m.isPending} className="w-full">Update password</Button>
        </form>)}
    </AuthLayout>
  );
}
