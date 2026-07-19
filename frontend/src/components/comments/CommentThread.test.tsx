import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { WorkItemComment } from "../../api/projects";
import { CommentThread } from "./CommentThread";

const comments: WorkItemComment[] = [
  {
    id: 1,
    kind: "comment",
    body: "Existing note",
    author: 2,
    author_name: "Bob",
    wbs_node_id: 10,
    card_id: null,
    created_at: "2026-07-19T09:00:00Z",
    updated_at: "2026-07-19T09:00:00Z",
  },
];

describe("CommentThread", () => {
  it("submits a new comment", async () => {
    const onAdd = vi.fn().mockResolvedValue(undefined);
    render(<CommentThread comments={comments} onAdd={onAdd} />);

    fireEvent.change(screen.getByLabelText("Текст комментария"), {
      target: { value: "New decision" },
    });
    fireEvent.change(screen.getByLabelText("Тип комментария"), {
      target: { value: "decision" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Отправить" }));

    await waitFor(() => {
      expect(onAdd).toHaveBeenCalledWith("New decision", "decision");
    });
  });

  it("renders existing comments", () => {
    render(<CommentThread comments={comments} onAdd={vi.fn()} />);
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("Existing note")).toBeInTheDocument();
  });
});
