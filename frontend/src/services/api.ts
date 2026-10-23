const BASE = (import.meta.env.VITE_API_BASE as string | undefined) || "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: { field: string; message: string }[]) {
    super(message);
  }
}

function csrfToken(): string {
  const m = document.cookie.match(/(?:^|; )cp_csrf=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

async function request<T>(method: string, path: string, body?: unknown, form?: FormData): Promise<T> {
  const headers: Record<string, string> = {};
  if (method !== "GET") headers["X-CSRF-Token"] = csrfToken();
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(BASE + path, { method, headers, credentials: "include", body: form ?? (body !== undefined ? JSON.stringify(body) : undefined) });
  } catch {
    throw new ApiError(0, "network", "Cannot reach the server. Check your connection and try again.");
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("json") ? await res.json() : await res.text();
  if (!res.ok) {
    const e = (data as any)?.error;
    throw new ApiError(res.status, e?.code || "error", e?.message || "Something went wrong.", e?.details);
  }
  return data as T;
}

export const api = {
  get: <T,>(p: string) => request<T>("GET", p),
  post: <T,>(p: string, b?: unknown) => request<T>("POST", p, b ?? {}),
  patch: <T,>(p: string, b: unknown) => request<T>("PATCH", p, b),
  del: <T,>(p: string, b?: unknown) => request<T>("DELETE", p, b),
  upload: <T,>(p: string, file: File) => { const f = new FormData(); f.append("file", file); return request<T>("POST", p, undefined, f); },
  /** Download a file the API returns (uses the signed-in cookie). */
  async download(path: string, filename: string) {
    const res = await fetch(BASE + path, { credentials: "include" });
    if (!res.ok) throw new ApiError(res.status, "download_failed", "The file could not be downloaded.");
    const url = URL.createObjectURL(await res.blob());
    const a = document.createElement("a");
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  },
};
