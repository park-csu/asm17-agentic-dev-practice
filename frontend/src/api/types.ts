export type ScheduleStatus = "ok" | "needs_question" | "fallback";

export type QuestionSource = "" | "classification" | "pre_validate";

export type AgentNodeName =
  | ""
  | "pre_validate"
  | "classification"
  | "ask_context"
  | "plan"
  | "post_validate"
  | "output"
  | "fallback";

export type ApiTask = {
  id: string;
  title: string;
  description: string;
  estimated_minutes: number;
  order_index: number;
  is_done: boolean;
};

export type ApiSchedule = {
  id: string;
  title: string;
  detail: string;
  location: string;
  start_time: string | null;
  end_time: string | null;
  status: ScheduleStatus;
  fallback_reason: string;
  is_decomposable: boolean;
  created_at: string;
  tasks: ApiTask[];
};

export type StreamTask = {
  title: string;
  description?: string;
  estimated_minutes?: number;
  order_index?: number;
};

export type StreamEvent = {
  event: "node" | "done" | string;
  node?: AgentNodeName | string;
  data: string;
};

export type StreamDoneData = {
  schedule_id: string;
  status: ScheduleStatus;
  tasks: StreamTask[];
  question: string;
  question_source: QuestionSource;
  classification_retry: number;
  pre_validation_retry: number;
  plan_retry: number;
  detail_with_context: string;
  fallback_reason: string;
  answer?: string;
};

export type CreateSchedulePayload = {
  title?: string | null;
  detail: string;
  location: string;
  start_time: string;
  end_time: string;
  detail_with_context?: string;
  context_answer?: string;
  question?: string;
  question_source?: QuestionSource;
  classification_retry?: number;
  pre_validation_retry?: number;
  plan_retry?: number;
  max_retry?: number;
};

export type RegenerateSchedulePayload = {
  context_answer?: string;
  question?: string;
  question_source?: QuestionSource;
  classification_retry?: number;
  pre_validation_retry?: number;
  plan_retry?: number;
  max_retry?: number;
  detail_with_context?: string;
};

export type UpdateSchedulePayload = {
  title?: string;
  detail?: string;
  location?: string;
};
