import { describe, expect, it } from "vitest";

import { fetchSchedule, fetchSchedules } from "./client";
import type { ApiSchedule } from "./types";

const runRealApi = import.meta.env.RUN_REAL_API === "1";
const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8001";

function expectScheduleShape(schedule: ApiSchedule) {
  expect(schedule).toEqual(
    expect.objectContaining({
      id: expect.any(String),
      title: expect.any(String),
      detail: expect.any(String),
      location: expect.any(String),
      status: expect.stringMatching(/^(ok|needs_question|fallback)$/),
      fallback_reason: expect.any(String),
      is_decomposable: expect.any(Boolean),
      created_at: expect.any(String),
      tasks: expect.any(Array),
    }),
  );
  expect(schedule.start_time === null || typeof schedule.start_time === "string").toBe(true);
  expect(schedule.end_time === null || typeof schedule.end_time === "string").toBe(true);
}

describe.skipIf(!runRealApi)("실제 API 응답", () => {
  it("저장된 일정 목록을 백엔드에서 조회한다", async () => {
    const schedules = await fetchSchedules({ baseUrl });

    expect(Array.isArray(schedules)).toBe(true);
    for (const schedule of schedules) {
      expectScheduleShape(schedule);
      for (const task of schedule.tasks) {
        expect(task).toEqual(
          expect.objectContaining({
            id: expect.any(String),
            title: expect.any(String),
            description: expect.any(String),
            estimated_minutes: expect.any(Number),
            order_index: expect.any(Number),
            is_done: expect.any(Boolean),
          }),
        );
      }
    }
  });

  it("목록의 첫 일정 상세를 조회한다", async () => {
    const schedules = await fetchSchedules({ baseUrl });
    if (schedules.length === 0) {
      return;
    }

    const schedule = await fetchSchedule(schedules[0].id, { baseUrl });

    expectScheduleShape(schedule);
    expect(schedule.id).toBe(schedules[0].id);
  });
});
