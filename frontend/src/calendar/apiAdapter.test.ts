import { describe, expect, it } from "vitest";

import { apiScheduleToCalendarSchedule, apiSchedulesToCalendarSchedules } from "./apiAdapter";
import type { ApiSchedule } from "../api/types";

const apiSchedule: ApiSchedule = {
  id: "schedule-1",
  title: "API 계약 점검",
  detail: "프론트 요청과 FastAPI 스키마를 맞춘다.",
  location: "개발실",
  start_time: "2026-06-08T10:00:00",
  end_time: "2026-06-08T12:00:00",
  status: "ok",
  fallback_reason: "",
  is_decomposable: true,
  created_at: "2026-06-07T04:00:00",
  tasks: [
    {
      id: "task-1",
      title: "요청 body 확인",
      description: "지원 필드만 전송하는지 확인한다.",
      estimated_minutes: 20,
      order_index: 1,
      is_done: false,
    },
  ],
};

describe("api schedule adapter", () => {
  it("API 일정 응답을 캘린더 UI 일정 타입으로 변환한다", () => {
    expect(apiScheduleToCalendarSchedule(apiSchedule)).toEqual({
      id: "schedule-1",
      title: "API 계약 점검",
      detail: "프론트 요청과 FastAPI 스키마를 맞춘다.",
      location: "개발실",
      start_time: "2026-06-08T10:00:00",
      end_time: "2026-06-08T12:00:00",
      status: "ok",
      fallback_reason: "",
      tasks: [
        {
          id: "task-1",
          title: "요청 body 확인",
          description: "지원 필드만 전송하는지 확인한다.",
          estimated_minutes: 20,
          order_index: 1,
          is_done: false,
        },
      ],
    });
  });

  it("nullable 시간은 UI에서 빈 문자열로 정규화한다", () => {
    const schedule = apiScheduleToCalendarSchedule({
      ...apiSchedule,
      start_time: null,
      end_time: null,
    });

    expect(schedule.start_time).toBe("");
    expect(schedule.end_time).toBe("");
  });

  it("API 상태 배열을 UI 일정 배열로 변환한다", () => {
    expect(apiSchedulesToCalendarSchedules([apiSchedule])).toHaveLength(1);
  });
});
