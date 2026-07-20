import { useEffect, useRef, useState } from "react";

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
};

export function ReactionPicker({ onPick, onClose }: Props) {
  const [tab, setTab] = useState<"emoji" | "gif">("emoji");
  const [gifUrl, setGifUrl] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDoc = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        onClose();
      }
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
  }, [onClose]);

  return (
    <div
      ref={rootRef}
      className="absolute bottom-full left-0 z-20 mb-2 w-72 rounded-xl border border-border bg-surface p-3 shadow-lg"
      role="dialog"
      aria-label="Выбор реакции"
    >
      <div className="mb-2 flex gap-2">
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
      {tab === "emoji" ? (
        <div className="grid grid-cols-8 gap-1">
          {EMOJI_GRID.map((emoji) => (
            <button
              key={emoji}
              type="button"
              className="rounded-md p-1 text-lg hover:bg-cream"
              onClick={() => onPick({ kind: "emoji", emoji })}
            >
              {emoji}
            </button>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          <div className="grid grid-cols-3 gap-2">
            {CURATED_GIFS.map((gif) => (
              <button
                key={gif.url}
                type="button"
                title={gif.label}
                className="overflow-hidden rounded-md border border-border hover:border-primary"
                onClick={() => onPick({ kind: "gif", gif_url: gif.url })}
              >
                <img src={gif.url} alt={gif.label} className="h-16 w-full object-cover" />
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
  );
}
