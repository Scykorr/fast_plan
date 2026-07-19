import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createWorkspaceApi, type SearchResult } from "../../api/workspace";
import { useAuth } from "../../context/AuthContext";

const DEBOUNCE_MS = 300;

export function GlobalSearchBar() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      setResults([]);
      return;
    }
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setResults([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const api = createWorkspaceApi();
          const response = await api.search(trimmed);
          setResults(response.results);
          setOpen(true);
        } catch {
          setResults([]);
        } finally {
          setLoading(false);
        }
      })();
    }, DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [query, isAuthenticated]);

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleSelect = (result: SearchResult) => {
    setOpen(false);
    setQuery("");
    setResults([]);
    if (result.link) {
      navigate(result.link);
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-xs">
      <input
        type="search"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onFocus={() => {
          if (results.length > 0) {
            setOpen(true);
          }
        }}
        placeholder="Поиск..."
        aria-label="Глобальный поиск"
        className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text placeholder:text-text-muted"
      />
      {open && (query.trim().length >= 2 || results.length > 0) && (
        <div className="absolute right-0 z-50 mt-2 w-80 max-w-[min(20rem,calc(100vw-2rem))] rounded-xl border border-border bg-surface p-2 shadow-lg">
          {loading && (
            <p className="px-3 py-2 text-xs text-text-muted">Поиск...</p>
          )}
          {!loading && results.length === 0 && (
            <p className="px-3 py-2 text-xs text-text-muted">Ничего не найдено</p>
          )}
          {!loading && results.length > 0 && (
            <ul className="max-h-72 overflow-y-auto">
              {results.map((result) => (
                <li key={`${result.type}-${result.id}`}>
                  <button
                    type="button"
                    onClick={() => handleSelect(result)}
                    className="w-full rounded-lg px-3 py-2 text-left hover:bg-cream"
                  >
                    <p className="text-sm font-medium text-text">{result.title}</p>
                    <p className="text-xs text-text-muted">
                      {result.type}
                      {result.subtitle ? ` · ${result.subtitle}` : ""}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
