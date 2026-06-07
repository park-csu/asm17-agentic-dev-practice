import type {
  ApiSchedule,
  ApiTask,
  CreateSchedulePayload,
  RegenerateSchedulePayload,
  StreamDoneData,
  StreamEvent,
  UpdateSchedulePayload,
} from "./types";

type FetchLike = typeof fetch;

type ClientOptions = {
  baseUrl?: string;
  fetcher?: FetchLike;
};

type StreamOptions = ClientOptions & {
  onEvent?: (event: StreamEvent) => void;
};

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8001";

const jsonHeaders = { "Content-Type": "application/json" };

function resolveBaseUrl(baseUrl?: string) {
  return baseUrl ?? apiBaseUrl;
}

function resolveFetcher(fetcher?: FetchLike) {
  return fetcher ?? fetch;
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API 요청 실패: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function parseEmptyResponse(response: Response): Promise<void> {
  if (!response.ok) {
    throw new Error(`API 요청 실패: ${response.status}`);
  }
}

function compactBody<T extends Record<string, unknown>>(body: T): T {
  return Object.fromEntries(
    Object.entries(body).filter(([, value]) => value !== undefined),
  ) as T;
}

async function parseSseDone(response: Response, onEvent?: (event: StreamEvent) => void): Promise<StreamDoneData> {
  if (!response.ok) {
    throw new Error(`API 요청 실패: ${response.status}`);
  }
  if (!response.body) {
    throw new Error("SSE 응답 본문이 비어 있습니다.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let doneData: StreamDoneData | null = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const event = parseSseFrame(frame);
      if (!event) {
        continue;
      }
      onEvent?.(event);
      if (event.event === "done") {
        doneData = JSON.parse(event.data) as StreamDoneData;
      }
    }
  }

  if (!doneData && buffer.trim()) {
    const event = parseSseFrame(buffer);
    if (event) {
      onEvent?.(event);
      if (event.event === "done") {
        doneData = JSON.parse(event.data) as StreamDoneData;
      }
    }
  }

  if (!doneData) {
    throw new Error("SSE 완료 이벤트를 찾지 못했습니다.");
  }
  return doneData;
}

function parseSseFrame(frame: string): StreamEvent | null {
  const dataLine = frame
    .split("\n")
    .map((line) => line.trim())
    .find((line) => line.startsWith("data:"));

  if (!dataLine) {
    return null;
  }

  return JSON.parse(dataLine.slice("data:".length).trim()) as StreamEvent;
}

export async function fetchSchedules(options: ClientOptions = {}): Promise<ApiSchedule[]> {
  const response = await resolveFetcher(options.fetcher)(`${resolveBaseUrl(options.baseUrl)}/api/v1/schedules`);
  return parseJsonResponse<ApiSchedule[]>(response);
}

export async function fetchSchedule(scheduleId: string, options: ClientOptions = {}): Promise<ApiSchedule> {
  const response = await resolveFetcher(options.fetcher)(
    `${resolveBaseUrl(options.baseUrl)}/api/v1/schedules/${scheduleId}`,
  );
  return parseJsonResponse<ApiSchedule>(response);
}

export async function updateSchedule(
  scheduleId: string,
  payload: UpdateSchedulePayload,
  options: ClientOptions = {},
): Promise<ApiSchedule> {
  const response = await resolveFetcher(options.fetcher)(`${resolveBaseUrl(options.baseUrl)}/api/v1/schedules/${scheduleId}`, {
    method: "PATCH",
    headers: jsonHeaders,
    body: JSON.stringify(compactBody(payload)),
  });
  return parseJsonResponse<ApiSchedule>(response);
}

export async function deleteSchedule(scheduleId: string, options: ClientOptions = {}): Promise<void> {
  const response = await resolveFetcher(options.fetcher)(`${resolveBaseUrl(options.baseUrl)}/api/v1/schedules/${scheduleId}`, {
    method: "DELETE",
  });
  return parseEmptyResponse(response);
}

export async function updateTaskDone(
  scheduleId: string,
  taskId: string,
  isDone: boolean,
  options: ClientOptions = {},
): Promise<ApiTask> {
  const response = await resolveFetcher(options.fetcher)(
    `${resolveBaseUrl(options.baseUrl)}/api/v1/schedules/${scheduleId}/tasks/${taskId}`,
    {
      method: "PATCH",
      headers: jsonHeaders,
      body: JSON.stringify({ is_done: isDone }),
    },
  );
  return parseJsonResponse<ApiTask>(response);
}

export async function streamCreateSchedule(
  payload: CreateSchedulePayload,
  options: StreamOptions = {},
): Promise<StreamDoneData> {
  const response = await resolveFetcher(options.fetcher)(`${resolveBaseUrl(options.baseUrl)}/api/v1/schedules/stream`, {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(compactBody({ max_retry: 2, ...payload })),
  });
  return parseSseDone(response, options.onEvent);
}

export async function streamRegenerateSchedule(
  scheduleId: string,
  payload: RegenerateSchedulePayload = {},
  options: StreamOptions = {},
): Promise<StreamDoneData> {
  const response = await resolveFetcher(options.fetcher)(
    `${resolveBaseUrl(options.baseUrl)}/api/v1/schedules/${scheduleId}/stream`,
    {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(compactBody({ max_retry: 2, ...payload })),
    },
  );
  return parseSseDone(response, options.onEvent);
}
