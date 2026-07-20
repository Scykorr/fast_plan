import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { fetchPublicStatusReport } from "../api/projects";
import type { ProjectStatusReport } from "../api/projects";
import { ErrorMessage } from "../components/ErrorMessage";
import { StatusReportDigest } from "../components/projects/StatusReportDigest";

export function ShareStatusPage() {
  const { token } = useParams<{ token: string }>();
  const [report, setReport] = useState<ProjectStatusReport | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      setError("Ссылка недействительна");
      setLoading(false);
      return;
    }
    void fetchPublicStatusReport(token)
      .then(setReport)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-cream">
        <p className="text-text-muted">Загрузка отчёта...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-cream px-4">
        <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-8 shadow-sm">
          <h1 className="text-2xl font-bold text-text">Статус-отчёт</h1>
          <div className="mt-4">
            <ErrorMessage
              message={error || "Ссылка не найдена или истекла"}
            />
          </div>
          <Link
            to="/login"
            className="mt-4 inline-block text-sm text-primary hover:underline"
          >
            Войти в Fast Plan
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-cream px-4 py-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="rounded-2xl border border-border bg-surface p-6 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
            {report.share?.workspace_name ?? "Fast Plan"}
          </p>
          <h1 className="mt-1 text-2xl font-bold text-text">
            {report.share?.project_name ?? report.project.name}
          </h1>
          {report.share?.label && (
            <p className="mt-1 text-sm text-text-muted">{report.share.label}</p>
          )}
          <p className="mt-2 text-xs text-text-muted">
            Гостевой просмотр · только чтение
          </p>
        </header>
        <div className="rounded-2xl border border-border bg-surface p-6 shadow-sm">
          <StatusReportDigest report={report} readOnly />
        </div>
      </div>
    </div>
  );
}
