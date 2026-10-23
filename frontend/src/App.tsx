import { Navigate, Route, Routes } from "react-router-dom";
import { AdminRoute, ProtectedRoute } from "./components/RouteGuards";
import { AppLayout } from "./layouts/AppLayout";
import { AdminPage } from "./pages/Admin";
import { ProfilePage, SettingsPage } from "./pages/Account";
import { AnalysisDetailPage, AnalyzerListPage, NewAnalysisPage } from "./pages/Analyzer";
import { ApplicationsPage } from "./pages/Applications";
import { ForgotPasswordPage, LoginPage, RegisterPage, ResetPasswordPage, VerifyEmailPage } from "./pages/Auth";
import { CoverLettersPage } from "./pages/CoverLetters";
import { DashboardPage } from "./pages/Dashboard";
import { ResumesPage } from "./pages/Resumes";
import { RoadmapDetailPage, RoadmapsPage } from "./pages/Roadmaps";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="resumes" element={<ResumesPage />} />
          <Route path="analyzer" element={<AnalyzerListPage />} />
          <Route path="analyzer/new" element={<NewAnalysisPage />} />
          <Route path="analyzer/:id" element={<AnalysisDetailPage />} />
          <Route path="roadmaps" element={<RoadmapsPage />} />
          <Route path="roadmaps/:id" element={<RoadmapDetailPage />} />
          <Route path="cover-letters" element={<CoverLettersPage />} />
          <Route path="applications" element={<ApplicationsPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route element={<AdminRoute />}><Route path="admin" element={<AdminPage />} /></Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
