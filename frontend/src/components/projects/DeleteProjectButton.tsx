import { useConfirm } from "../../hooks/useConfirm";

type Props = {
  projectName: string;
  busy?: boolean;
  variant?: "link" | "button";
  onConfirmDelete: () => Promise<void> | void;
};

export function DeleteProjectButton({
  projectName,
  busy = false,
  variant = "link",
  onConfirmDelete,
}: Props) {
  const { confirm, dialog } = useConfirm();

  const handleClick = async () => {
    if (busy) {
      return;
    }
    const ok = await confirm(
      `Проект «${projectName}» будет удалён вместе с WBS, рисками, стейкхолдерами и связанными данными. Это нельзя отменить.`,
      {
        title: "Удалить проект?",
        confirmLabel: "Удалить",
        danger: true,
      },
    );
    if (!ok) {
      return;
    }
    await onConfirmDelete();
  };

  const className =
    variant === "button"
      ? "rounded-lg border border-primary/40 px-3 py-1.5 text-sm font-medium text-primary hover:bg-primary/10 disabled:opacity-60"
      : "text-xs text-primary hover:underline disabled:opacity-60";

  return (
    <>
      <button
        type="button"
        disabled={busy}
        className={className}
        onClick={() => void handleClick()}
      >
        {busy ? "Удаление..." : "Удалить"}
      </button>
      {dialog}
    </>
  );
}
