import { describe, expect, it, vi } from "vitest";

import {
  deleteSchedule,
  fetchSchedules,
  streamCreateSchedule,
  streamRegenerateSchedule,
  updateSchedule,
  updateTaskDone,
} from "./client";

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

function emptyResponse(init: ResponseInit = {}) {
  return new Response(null, { status: 204, ...init });
}

function sseDoneResponse(data: Record<string, unknown>) {
  const event = {
    event: "done",
    node: "",
    data: JSON.stringify({
      schedule_id: "schedule-1",
      status: "ok",
      tasks: [],
      question: "",
      question_source: "",
      classification_retry: 0,
      pre_validation_retry: 0,
      plan_retry: 0,
      detail_with_context: "",
      fallback_reason: "",
      ...data,
    }),
  };
  return new Response(`data: ${JSON.stringify(event)}\n\n`, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function sseResponse(events: Array<Record<string, unknown>>) {
  return new Response(events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join(""), {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function getRequest(fetcher: ReturnType<typeof vi.fn>) {
  return fetcher.mock.calls[0] as [string, RequestInit | undefined];
}

describe("api client 요청 계약", () => {
  const baseUrl = "http://api.test";

  it("일정 목록을 조회한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(jsonResponse([]));

    await fetchSchedules({ baseUrl, fetcher });

    expect(fetcher).toHaveBeenCalledWith(`${baseUrl}/api/v1/schedules`);
  });

  it("인증 토큰이 있으면 일정 목록 요청에 Bearer 헤더를 포함한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(jsonResponse([]));

    await fetchSchedules({ baseUrl, fetcher, accessToken: "access-token" });

    const [url, init] = getRequest(fetcher);
    expect(url).toBe(`${baseUrl}/api/v1/schedules`);
    expect(init?.headers).toEqual({ Authorization: "Bearer access-token" });
  });

  it("일정 수정은 API가 지원하는 메타데이터만 전송한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(jsonResponse({ id: "schedule-1" }));

    await updateSchedule(
      "schedule-1",
      { title: "수정", detail: "상세", location: "서울" },
      { baseUrl, fetcher },
    );

    const [url, init] = getRequest(fetcher);
    expect(url).toBe(`${baseUrl}/api/v1/schedules/schedule-1`);
    expect(init?.method).toBe("PATCH");
    expect(init?.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(init?.body as string)).toEqual({
      title: "수정",
      detail: "상세",
      location: "서울",
    });
  });

  it("일정을 삭제한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(emptyResponse());

    await deleteSchedule("schedule-1", { baseUrl, fetcher });

    const [url, init] = getRequest(fetcher);
    expect(url).toBe(`${baseUrl}/api/v1/schedules/schedule-1`);
    expect(init?.method).toBe("DELETE");
  });

  it("task 완료 여부만 수정한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(jsonResponse({ id: "task-1" }));

    await updateTaskDone("schedule-1", "task-1", true, { baseUrl, fetcher });

    const [url, init] = getRequest(fetcher);
    expect(url).toBe(`${baseUrl}/api/v1/schedules/schedule-1/tasks/task-1`);
    expect(init?.method).toBe("PATCH");
    expect(JSON.parse(init?.body as string)).toEqual({ is_done: true });
  });

  it("새 일정은 stream 생성 엔드포인트로 요청한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(sseDoneResponse({ status: "needs_question" }));

    const result = await streamCreateSchedule(
      {
        title: "발표 준비",
        detail: "자료 조사",
        location: "회의실",
        start_time: "2026-06-10T10:00",
        end_time: "2026-06-10T12:00",
      },
      { baseUrl, fetcher },
    );

    const [url, init] = getRequest(fetcher);
    expect(url).toBe(`${baseUrl}/api/v1/schedules/stream`);
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual({
      max_retry: 2,
      title: "발표 준비",
      detail: "자료 조사",
      location: "회의실",
      start_time: "2026-06-10T10:00",
      end_time: "2026-06-10T12:00",
    });
    expect(result.status).toBe("needs_question");
  });

  it("stream 생성 요청에 인증 토큰을 포함한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(sseDoneResponse({ status: "ok" }));

    await streamCreateSchedule(
      {
        title: "발표 준비",
        detail: "자료 조사",
        location: "회의실",
        start_time: "2026-06-10T10:00",
        end_time: "2026-06-10T12:00",
      },
      { baseUrl, fetcher, accessToken: "access-token" },
    );

    const [, init] = getRequest(fetcher);
    expect(init?.headers).toEqual({
      "Content-Type": "application/json",
      Authorization: "Bearer access-token",
    });
  });

  it("stream 중간 node 이벤트를 콜백으로 전달한다", async () => {
    const nodeEvent = {
      event: "node",
      node: "plan",
      data: JSON.stringify({ tasks: [{ title: "초안 작성" }] }),
    };
    const doneEvent = {
      event: "done",
      node: "",
      data: JSON.stringify({
        schedule_id: "schedule-1",
        status: "ok",
        tasks: [],
        question: "",
        question_source: "",
        classification_retry: 0,
        pre_validation_retry: 0,
        plan_retry: 0,
        detail_with_context: "",
        fallback_reason: "",
      }),
    };
    const fetcher = vi.fn().mockResolvedValue(sseResponse([nodeEvent, doneEvent]));
    const onEvent = vi.fn();

    await streamCreateSchedule(
      {
        title: "발표 준비",
        detail: "자료 조사",
        location: "회의실",
        start_time: "2026-06-10T10:00",
        end_time: "2026-06-10T12:00",
      },
      { baseUrl, fetcher, onEvent },
    );

    expect(onEvent).toHaveBeenCalledWith(nodeEvent);
    expect(onEvent).toHaveBeenCalledWith(doneEvent);
  });

  it("기존 일정 재생성은 이어가기 필드를 포함해 요청한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(sseDoneResponse({ status: "ok" }));

    await streamRegenerateSchedule(
      "schedule-1",
      {
        context_answer: "온라인 발표입니다.",
        question: "현장 이동이 필요한가요?",
        question_source: "pre_validate",
        classification_retry: 1,
        pre_validation_retry: 1,
        plan_retry: 0,
        detail_with_context: "자료 조사\n온라인 발표입니다.",
      },
      { baseUrl, fetcher },
    );

    const [url, init] = getRequest(fetcher);
    expect(url).toBe(`${baseUrl}/api/v1/schedules/schedule-1/stream`);
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual({
      max_retry: 2,
      context_answer: "온라인 발표입니다.",
      question: "현장 이동이 필요한가요?",
      question_source: "pre_validate",
      classification_retry: 1,
      pre_validation_retry: 1,
      plan_retry: 0,
      detail_with_context: "자료 조사\n온라인 발표입니다.",
    });
  });
});
