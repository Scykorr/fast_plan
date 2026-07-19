import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Stakeholder, WBSNode } from "../../api/projects";
import { StakeholderPanel } from "./StakeholderPanel";

const wbs: WBSNode[] = [
  {
    id: 1,
    code: "1",
    title: "Root",
    description: "",
    node_type: "deliverable",
    position: 0,
    parent_id: null,
    tracker_id: null,
    tracker_name: null,
    workflow_status_id: null,
    workflow_status_name: null,
    assignee_id: null,
    assignee_name: null,
    custom_values: [],
    schedule: null,
    card_id: null,
    children: [
      {
        id: 2,
        code: "1.1",
        title: "WP",
        description: "",
        node_type: "work_package",
        position: 0,
        parent_id: 1,
        tracker_id: null,
        tracker_name: null,
        workflow_status_id: null,
        workflow_status_name: null,
        assignee_id: null,
        assignee_name: null,
        custom_values: [],
        schedule: null,
        card_id: null,
        children: [],
      },
    ],
  },
];

const stakeholders: Stakeholder[] = [
  {
    id: 10,
    name: "Alice",
    role: "Sponsor",
    interest: 3,
    influence: 4,
    contact_email: "",
    notes: "",
    created_at: "2026-01-01T00:00:00Z",
  },
];

describe("StakeholderPanel", () => {
  it("submits stakeholder form", async () => {
    const onAddStakeholder = vi.fn().mockResolvedValue(undefined);
    render(
      <StakeholderPanel
        stakeholders={stakeholders}
        raci={[]}
        wbs={wbs}
        onAddStakeholder={onAddStakeholder}
        onUpdateStakeholder={vi.fn()}
        onDeleteStakeholder={vi.fn()}
        onAddRACI={vi.fn()}
        onDeleteRACI={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "+ Добавить" }));
    fireEvent.change(screen.getByLabelText("Имя"), {
      target: { value: "Bob" },
    });
    fireEvent.change(screen.getByLabelText("Роль"), {
      target: { value: "PM" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => {
      expect(onAddStakeholder).toHaveBeenCalledWith({ name: "Bob", role: "PM" });
    });
  });

  it("submits explicit RACI selection", async () => {
    const onAddRACI = vi.fn().mockResolvedValue(undefined);
    render(
      <StakeholderPanel
        stakeholders={stakeholders}
        raci={[]}
        wbs={wbs}
        onAddStakeholder={vi.fn()}
        onUpdateStakeholder={vi.fn()}
        onDeleteStakeholder={vi.fn()}
        onAddRACI={onAddRACI}
        onDeleteRACI={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "+ Назначение" }));
    fireEvent.change(screen.getByLabelText("WBS"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Стейкхолдер"), {
      target: { value: "10" },
    });
    fireEvent.change(screen.getByLabelText("Тип RACI"), {
      target: { value: "A" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => {
      expect(onAddRACI).toHaveBeenCalledWith({
        wbs_node_id: 2,
        stakeholder_id: 10,
        raci_type: "A",
      });
    });
  });
});
