import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { PwaUpdatePrompt } from "./components/PwaUpdatePrompt";
import { GuestRoute, ProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { LocaleProvider } from "./context/LocaleContext";
import { WorkspaceProvider } from "./context/WorkspaceContext";
import { AdministrationPage } from "./pages/AdministrationPage";
import { AutomationsPage } from "./pages/AutomationsPage";
import { CalendarPage } from "./pages/CalendarPage";
import { CapacityPage } from "./pages/CapacityPage";
import { ClientsPage } from "./pages/ClientsPage";
import { CrmAiPage } from "./pages/CrmAiPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DealsPage } from "./pages/DealsPage";
import { FinancePage } from "./pages/FinancePage";
import { LeadsPage } from "./pages/LeadsPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { InviteAcceptPage } from "./pages/InviteAcceptPage";
import { KanbanPage } from "./pages/KanbanPage";
import { LoginPage } from "./pages/LoginPage";
import { MyTasksPage } from "./pages/MyTasksPage";
import { PortfolioPage } from "./pages/PortfolioPage";
import { ProjectDetailPage } from "./pages/ProjectDetailPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { SettingsPage } from "./pages/SettingsPage";
import { ShareStatusPage } from "./pages/ShareStatusPage";
import { VerifyEmailPage } from "./pages/VerifyEmailPage";
import { AuditPage } from "./pages/AuditPage";

export default function App() {
  return (
    <ThemeProvider>
      <LocaleProvider>
        <AuthProvider>
          <WorkspaceProvider>
            <BrowserRouter>
              <PwaUpdatePrompt />
              <Routes>
            <Route
              path="/login"
              element={
                <GuestRoute>
                  <LoginPage />
                </GuestRoute>
              }
            />
            <Route
              path="/register"
              element={
                <GuestRoute>
                  <RegisterPage />
                </GuestRoute>
              }
            />
            <Route
              path="/forgot-password"
              element={
                <GuestRoute>
                  <ForgotPasswordPage />
                </GuestRoute>
              }
            />
            <Route
              path="/reset-password"
              element={
                <GuestRoute>
                  <ResetPasswordPage />
                </GuestRoute>
              }
            />
            <Route path="/invite/:token" element={<InviteAcceptPage />} />
            <Route path="/share/:token" element={<ShareStatusPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="portfolio" element={<PortfolioPage />} />
              <Route path="clients" element={<ClientsPage />} />
              <Route path="deals" element={<DealsPage />} />
              <Route path="leads" element={<LeadsPage />} />
              <Route path="automations" element={<AutomationsPage />} />
              <Route path="crm-ai" element={<CrmAiPage />} />
              <Route path="projects" element={<ProjectsPage />} />
              <Route path="projects/:projectId" element={<ProjectDetailPage />} />
              <Route path="tasks" element={<MyTasksPage />} />
              <Route path="capacity" element={<CapacityPage />} />
              <Route path="kanban" element={<KanbanPage />} />
              <Route path="calendar" element={<CalendarPage />} />
              <Route path="finance" element={<FinancePage />} />
              <Route path="audit" element={<AuditPage />} />
              <Route path="administration" element={<AdministrationPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
            </BrowserRouter>
          </WorkspaceProvider>
        </AuthProvider>
      </LocaleProvider>
    </ThemeProvider>
  );
}
