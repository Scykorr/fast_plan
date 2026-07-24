import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";

export type ReactionPick =
  | { kind: "emoji"; emoji: string }
  | { kind: "gif"; gif_url: string };

const EMOJI_GRID = [
  "👍",
  "👎",
  "❤️",
  "😂",
  "😄",
  "😮",
  "😢",
  "😡",
  "🎉",
  "🔥",
  "👀",
  "👏",
  "✅",
  "❌",
  "🤔",
  "🙏",
  "💯",
  "🚀",
  "✨",
  "😅",
  "😎",
  "🤝",
  "💪",
  "⭐",
];

/** Curated HTTPS GIFs from allowlisted hosts (Giphy). */
export const CURATED_GIFS: Array<{ label: string; url: string }> = [
  {
    label: "Thumbs up",
    url: "https://media.giphy.com/media/111ebonMs90YLu/giphy.gif",
  },
  {
    label: "Clap",
    url: "https://media.giphy.com/media/7rj2ZgEhX3zEs/giphy.gif",
  },
  {
    label: "Party",
    url: "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",
  },
  {
    label: "Mind blown",
    url: "https://media.giphy.com/media/xT0xeJpnrWC4XWcyEk/giphy.gif",
  },
  {
    label: "Facepalm",
    url: "https://media.giphy.com/media/XsUtdieRKf562Y97cs/giphy.gif",
  },
  {
    label: "Heart",
    url: "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif",
  },
];

type Props = {
  onPick: (reaction: ReactionPick) => void;
  onClose: () => void;
  /** Button that opened the picker — used for fixed placement outside overflow. */
  anchorRef: RefObject<HTMLElement | null>;
};

const PICKER_WIDTH = 288;
const PICKER_MAX_HEIGHT = 260;

export function ReactionPicker({ onPick, onClose, anchorRef }: Props) {
  const [tab, setTab] = useState<"emoji" | "gif">("emoji");
  const [gifUrl, setGifUrl] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const [style, setStyle] = useState<CSSProperties>({
    position: "fixed",
    top: 0,
    left: 0,
    zIndex: 80,
    visibility: "hidden",
  });

  useLayoutEffect(() => {
    const place = () => {
      const anchor = anchorRef.current;
      if (!anchor) {
        return;
      }
      const rect = anchor.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom - 8;
      const spaceAbove = rect.top - 8;
      const openDown =
        spaceBelow >= Math.min(PICKER_MAX_HEIGHT, 160) || spaceBelow >= spaceAbove;
      const height = Math.min(
        PICKER_MAX_HEIGHT,
        openDown ? Math.max(spaceBelow, 120) : Math.max(spaceAbove, 120),
      );
      let left = rect.left;
      left = Math.max(8, Math.min(left, window.innerWidth - PICKER_WIDTH - 8));
      const top = openDown
        ? rect.bottom + 4
        : Math.max(8, rect.top - height - 4);
      setStyle({
        position: "fixed",
        top,
        left,
        zIndex: 80,
        width: PICKER_WIDTH,
        height,
        maxHeight: height,
        visibility: "visible",
      });
    };
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [anchorRef]);

  useEffect(() => {
    const onDoc = (event: MouseEvent) => {
      const target = event.target as Node;
      if (rootRef.current?.contains(target)) {
        return;
      }
      if (anchorRef.current?.contains(target)) {
        return;
      }
      onClose();
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [onClose, anchorRef]);

  return createPortal(
    <div
      ref={rootRef}
      style={style}
      className="flex flex-col overflow-hidden rounded-xl border border-border bg-surface p-2 shadow-lg"
      role="dialog"
      aria-label="Выбор реакции"
    >
      <div className="mb-2 flex shrink-0 gap-1">
        <button
          type="button"
          onClick={() => setTab("emoji")}
          className={`rounded-md px-2 py-1 text-xs font-medium ${
            tab === "emoji" ? "bg-primary text-white" : "bg-cream text-text"
          }`}
        >
          Emoji
        </button>
        <button
          type="button"
          onClick={() => setTab("gif")}
          className={`rounded-md px-2 py-1 text-xs font-medium ${
            tab === "gif" ? "bg-primary text-white" : "bg-cream text-text"
          }`}
        >
          GIF
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
        {tab === "emoji" ? (
          <div className="grid grid-cols-8 gap-0.5">
            {EMOJI_GRID.map((emoji) => (
              <button
                key={emoji}
                type="button"
                className="rounded-md p-1.5 text-lg leading-none hover:bg-cream"
                onClick={() => onPick({ kind: "emoji", emoji })}
              >
                {emoji}
              </button>
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            <div className="grid grid-cols-3 gap-1.5">
              {CURATED_GIFS.map((gif) => (
                <button
                  key={gif.url}
                  type="button"
                  title={gif.label}
                  className="overflow-hidden rounded-md border border-border hover:border-primary"
                  onClick={() => onPick({ kind: "gif", gif_url: gif.url })}
                >
                  <img
                    src={gif.url}
                    alt={gif.label}
                    className="h-14 w-full object-cover"
                  />
                </button>
              ))}
            </div>
            <div className="flex gap-1">
              <input
                value={gifUrl}
                onChange={(event) => setGifUrl(event.target.value)}
                placeholder="HTTPS URL (giphy/tenor)"
                className="min-w-0 flex-1 rounded-md border border-border bg-cream px-2 py-1 text-xs"
              />
              <button
                type="button"
                disabled={!gifUrl.trim()}
                onClick={() => onPick({ kind: "gif", gif_url: gifUrl.trim() })}
                className="rounded-md bg-primary px-2 py-1 text-xs font-medium text-white disabled:opacity-50"
              >
                OK
              </button>
            </div>
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}
