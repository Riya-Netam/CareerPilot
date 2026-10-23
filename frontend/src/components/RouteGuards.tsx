import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Spinner } from "./ui";

export function ProtectedRoute() {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <Spinner label="Checking your session" />;
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  return <Outlet />;
}

/** UI convenience only. The backend enforces admin access on every /admin API call. */
export function AdminRoute() {
  const { user, loading } = useAuth();
  if (loading) return <Spinner label="Checking your session" />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "USER") return <Navigate to="/" replace state={{ notice: "You do not have access to the admin area." }} />;
  return <Outlet />;
}
