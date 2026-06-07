import type { ApiSchedule, ApiTask, ScheduleStatus as ApiScheduleStatus } from "../api/types";
import type { CalendarSchedule, CalendarTask, ScheduleStatus } from "./types";

const supportedStatuses: ReadonlySet<ApiScheduleStatus> = new Set(["ok", "needs_question", "fallback"]);

export function apiScheduleToCalendarSchedule(schedule: ApiSchedule): CalendarSchedule {
  return {
    id: schedule.id,
    title: schedule.title,
    detail: schedule.detail,
    location: schedule.location,
    start_time: schedule.start_time ?? "",
    end_time: schedule.end_time ?? "",
    status: normalizeStatus(schedule.status),
    tasks: schedule.tasks.map(apiTaskToCalendarTask),
  };
}

export function apiSchedulesToCalendarSchedules(schedules: ApiSchedule[]): CalendarSchedule[] {
  return schedules.map(apiScheduleToCalendarSchedule);
}

function apiTaskToCalendarTask(task: ApiTask): CalendarTask {
  return {
    id: task.id,
    title: task.title,
    description: task.description,
    estimated_minutes: task.estimated_minutes,
    order_index: task.order_index,
    is_done: task.is_done,
  };
}

function normalizeStatus(status: ApiSchedule["status"]): ScheduleStatus {
  return supportedStatuses.has(status) ? status : "pending";
}
