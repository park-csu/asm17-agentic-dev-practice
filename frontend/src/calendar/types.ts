export type ScheduleStatus = "ok" | "needs_question" | "fallback" | "pending";

export type CalendarTask = {
  id: string;
  title: string;
  description: string;
  estimated_minutes: number;
  order_index: number;
  is_done: boolean;
};

export type CalendarSchedule = {
  id: string;
  title: string;
  detail: string;
  location: string;
  start_time: string;
  end_time: string;
  status: ScheduleStatus;
  tasks: CalendarTask[];
};

export type TaskGroupSchedule = Pick<CalendarSchedule, "id" | "title" | "start_time" | "end_time" | "tasks">;

export type TaskDateGroup = {
  dateKey: string;
  dateLabel: string;
  taskCount: number;
  schedules: TaskGroupSchedule[];
};
