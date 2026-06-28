import { describe, expect, it } from "vitest";

import type { WBSNode } from "../../../api/projects";
import { computeWBSMove } from "./wbsDragDrop";

const tree: WBSNode[] = [
  {
    id: 1,
    code: "1",
    title: "Root",
    description: "",
    node_type: "deliverable",
    position: 0,
    parent_id: null,
    schedule: null,
    card_id: null,
    children: [
      {
        id: 2,
        code: "1.1",
        title: "A",
        description: "",
        node_type: "work_package",
        position: 0,
        parent_id: 1,
        schedule: null,
        card_id: null,
        children: [],
      },
      {
        id: 3,
        code: "1.2",
        title: "B",
        description: "",
        node_type: "work_package",
        position: 1,
        parent_id: 1,
        schedule: null,
        card_id: null,
        children: [
          {
            id: 4,
            code: "1.2.1",
            title: "B1",
            description: "",
            node_type: "work_package",
            position: 0,
            parent_id: 3,
            schedule: null,
            card_id: null,
            children: [],
          },
        ],
      },
    ],
  },
];

describe("computeWBSMove", () => {
  it("reparents node when dropped onto another node", () => {
    const dragged = tree[0].children[0];
    const action = computeWBSMove(
      dragged,
      ["3"],
      new Map([
        [2, { x: 0, y: 0 }],
        [3, { x: 100, y: 0 }],
      ]),
      tree,
    );
    expect(action).toEqual({ parentId: 3, position: 1 });
  });

  it("reorders siblings by vertical position", () => {
    const dragged = tree[0].children[0];
    const action = computeWBSMove(
      dragged,
      [],
      new Map([
        [2, { x: 0, y: 200 }],
        [3, { x: 0, y: 100 }],
      ]),
      tree,
    );
    expect(action).toEqual({ parentId: 1, position: 1 });
  });

  it("rejects moving into own descendant", () => {
    const dragged = tree[0].children[1];
    const action = computeWBSMove(
      dragged,
      ["4"],
      new Map([[3, { x: 0, y: 0 }]]),
      tree,
    );
    expect(action).toBeNull();
  });
});
