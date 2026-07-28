import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

type Options = {
  onSearchFocus?: () => void;
  onNew?: () => void;
  enabled?: boolean;
};

/**
 * CRM list hotkeys (P1):
 * / or Ctrl+K — focus search
 * n — new entity action
 * g then d/l/c — go deals/leads/clients
 * ? — ignored (browser help)
 */
export function useCrmHotkeys(options: Options = {}) {
  const navigate = useNavigate();
  const { onSearchFocus, onNew, enabled = true } = options;

  useEffect(() => {
    if (!enabled) return;
    let pendingG = false;
    let gTimer: number | undefined;

    const isTypingTarget = (el: EventTarget | null) => {
      if (!(el instanceof HTMLElement)) return false;
      const tag = el.tagName;
      return (
        tag === "INPUT" ||
        tag === "TEXTAREA" ||
        tag === "SELECT" ||
        el.isContentEditable
      );
    };

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.altKey || e.metaKey) return;
      if (e.ctrlKey && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onSearchFocus?.();
        return;
      }
      if (isTypingTarget(e.target) && e.key !== "Escape") {
        pendingG = false;
        return;
      }
      if (e.key === "/" && !e.ctrlKey) {
        e.preventDefault();
        onSearchFocus?.();
        return;
      }
      if (e.key.toLowerCase() === "n" && !e.ctrlKey) {
        e.preventDefault();
        onNew?.();
        return;
      }
      if (e.key.toLowerCase() === "g" && !e.ctrlKey) {
        pendingG = true;
        window.clearTimeout(gTimer);
        gTimer = window.setTimeout(() => {
          pendingG = false;
        }, 800);
        return;
      }
      if (pendingG) {
        pendingG = false;
        window.clearTimeout(gTimer);
        const k = e.key.toLowerCase();
        if (k === "d") {
          e.preventDefault();
          navigate("/deals");
        } else if (k === "l") {
          e.preventDefault();
          navigate("/leads");
        } else if (k === "c") {
          e.preventDefault();
          navigate("/clients");
        }
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.clearTimeout(gTimer);
    };
  }, [enabled, navigate, onNew, onSearchFocus]);
}
