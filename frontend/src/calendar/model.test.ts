import { describe, expect, it } from "vitest";

import { buildTaskGroups, findClosestScheduleId } from "./model";
import type { CalendarSchedule } from "./types";

const schedules: CalendarSchedule[] = [
  {
    id: "past",
    title: "지난 일정",
    detail: "",
    location: "",
    start_time: "2026-06-06T09:00:00",
    end_time: "2026-06-06T10:00:00",
    status: "ok",
    tasks: [],
  },
  {
    id: "running",
    title: "진행 중",
    detail: "",
    location: "",
    start_time: "2026-06-07T09:00:00",
    end_time: "2026-06-07T11:00:00",
    status: "ok",
    tasks: [],
  },
  {
    id: "future",
    title: "미래 일정",
    detail: "",
    location: "",
    start_time: "2026-06-07T14:00:00",
    end_time: "2026-06-07T15:00:00",
    status: "pending",
    tasks: [],
  },
];

describe("calendar model", () => {
  it("진행 중인 일정이 있으면 가장 먼저 선택한다", () => {
    expect(findClosestScheduleId(schedules, new Date("2026-06-07T10:00:00"))).toBe("running");
  });

  it("진행/미래 일정이 없으면 가장 최근 과거 일정을 선택한다", () => {
    expect(findClosestScheduleId(schedules, new Date("2026-06-08T10:00:00"))).toBe("future");
  });

  it("task를 일정 시작 날짜 기준으로 그룹핑한다", () => {
    const groups = buildTaskGroups([
      {
        ...schedules[1],
        tasks: [
          {
            id: "task-2",
            title: "두 번째",
            description: "",
            estimated_minutes: 20,
            order_index: 2,
            is_done: false,
          },
          {
            id: "task-1",
            title: "첫 번째",
            description: "",
            estimated_minutes: 10,
            order_index: 1,
            is_done: false,
          },
        ],
      },
    ]);

    expect(groups).toHaveLength(1);
    expect(groups[0].dateKey).toBe("2026-06-07");
    expect(groups[0].taskCount).toBe(2);
    expect(groups[0].schedules[0].tasks.map((task) => task.id)).toEqual(["task-1", "task-2"]);
  });
});
