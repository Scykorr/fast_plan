import type { CrmSku } from "../../api/crm";

export type DocumentLineDraft = {
  key: string;
  sku_id: string;
  title: string;
  qty: string;
  price: string;
};

type DocumentLineEditorProps = {
  lines: DocumentLineDraft[];
  skus: CrmSku[];
  onChange: (lines: DocumentLineDraft[]) => void;
};

function newLine(): DocumentLineDraft {
  return {
    key: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    sku_id: "",
    title: "",
    qty: "1",
    price: "",
  };
}

export function emptyDocumentLines(): DocumentLineDraft[] {
  return [newLine()];
}

export function linesToPayload(lines: DocumentLineDraft[]) {
  return lines
    .filter((line) => line.sku_id || line.title.trim())
    .map((line) => {
      const payload: Record<string, unknown> = {
        title: line.title.trim(),
        qty: Number(line.qty) || 1,
      };
      if (line.sku_id) payload.sku_id = Number(line.sku_id);
      if (line.price !== "") payload.price = Number(line.price);
      return payload;
    });
}

export function linesTotal(lines: DocumentLineDraft[]): number {
  return lines.reduce((sum, line) => {
    const qty = Number(line.qty) || 0;
    const price = Number(line.price) || 0;
    return sum + qty * price;
  }, 0);
}

export function DocumentLineEditor({
  lines,
  skus,
  onChange,
}: DocumentLineEditorProps) {
  const update = (key: string, patch: Partial<DocumentLineDraft>) => {
    onChange(lines.map((line) => (line.key === key ? { ...line, ...patch } : line)));
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-text-muted">Позиции (SKU)</p>
        <button
          type="button"
          className="rounded border border-border px-2 py-1 text-xs"
          onClick={() => onChange([...lines, newLine()])}
        >
          + строка
        </button>
      </div>
      <ul className="space-y-2">
        {lines.map((line) => (
          <li
            key={line.key}
            className="grid gap-2 rounded-lg border border-border p-2 sm:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_5rem_6rem_auto]"
          >
            <select
              className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
              value={line.sku_id}
              onChange={(e) => {
                const skuId = e.target.value;
                const sku = skus.find((row) => String(row.id) === skuId);
                update(line.key, {
                  sku_id: skuId,
                  title: sku?.name || line.title,
                  price:
                    sku != null
                      ? String(sku.unit_price)
                      : line.price,
                });
              }}
            >
              <option value="">Без SKU / вручную</option>
              {skus.map((sku) => (
                <option key={sku.id} value={sku.id}>
                  {sku.code} · {sku.name}
                </option>
              ))}
            </select>
            <input
              className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
              placeholder="Название"
              value={line.title}
              onChange={(e) => update(line.key, { title: e.target.value })}
            />
            <input
              className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
              placeholder="Кол-во"
              value={line.qty}
              onChange={(e) => update(line.key, { qty: e.target.value })}
            />
            <input
              className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
              placeholder="Цена"
              value={line.price}
              onChange={(e) => update(line.key, { price: e.target.value })}
            />
            <button
              type="button"
              className="rounded border border-border px-2 py-1 text-xs"
              onClick={() => onChange(lines.filter((row) => row.key !== line.key))}
              disabled={lines.length <= 1}
            >
              ×
            </button>
          </li>
        ))}
      </ul>
      <p className="text-xs text-text-muted">
        Итого по строкам: {linesTotal(lines).toFixed(2)}
      </p>
    </div>
  );
}
