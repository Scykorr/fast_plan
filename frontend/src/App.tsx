import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { GuestRoute, ProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import { CalendarPage } from "./pages/CalendarPage";
import { DashboardPage } from "./pages/DashboardPage";
import { FinancePage } from "./pages/FinancePage";
import { KanbanPage } from "./pages/KanbanPage";
import { LoginPage } from "./pages/LoginPage";
import { ProjectDetailPage } from "./pages/ProjectDetailPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { RegisterPage } from "./pages/RegisterPage";
import { SettingsPage } from "./pages/SettingsPage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
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
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="projects" element={<ProjectsPage />} />
            <Route path="projects/:projectId" element={<ProjectDetailPage />} />
            <Route path="kanban" element={<KanbanPage />} />
            <Route path="calendar" element={<CalendarPage />} />
            <Route path="finance" element={<FinancePage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
