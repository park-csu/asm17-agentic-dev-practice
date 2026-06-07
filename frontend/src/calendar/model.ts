import type { CalendarSchedule, TaskDateGroup } from "./types";

const dateFormatter = new Intl.DateTimeFormat("ko-KR", {
  month: "long",
  day: "numeric",
  weekday: "short",
});

const timeFormatter = new Intl.DateTimeFormat("ko-KR", {
  hour: "2-digit",
  minute: "2-digit",
});

export function findClosestScheduleId(schedules: CalendarSchedule[], now = new Date()): string {
  if (schedules.length === 0) {
    return "";
  }

  const upcoming = schedules
    .filter((schedule) => new Date(schedule.end_time).getTime() >= now.getTime())
    .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());

  if (upcoming[0]) {
    return upcoming[0].id;
  }

  return [...schedules].sort((a, b) => new Date(b.end_time).getTime() - new Date(a.end_time).getTime())[0].id;
}

export function buildTaskGroups(schedules: CalendarSchedule[]): TaskDateGroup[] {
  const groups = new Map<string, TaskDateGroup>();

  for (const schedule of schedules) {
    const dateKey = toDateKey(schedule.start_time);
    const current = groups.get(dateKey) ?? {
      dateKey,
      dateLabel: formatDateLabel(schedule.start_time),
      taskCount: 0,
      schedules: [],
    };

    const sortedTasks = [...schedule.tasks].sort((a, b) => a.order_index - b.order_index);
    current.taskCount += sortedTasks.length;
    current.schedules.push({
      id: schedule.id,
      title: schedule.title,
      start_time: schedule.start_time,
      end_time: schedule.end_time,
      tasks: sortedTasks,
    });
    groups.set(dateKey, current);
  }

  return [...groups.values()]
    .map((group) => ({
      ...group,
      schedules: [...group.schedules].sort(
        (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime(),
      ),
    }))
    .sort((a, b) => a.dateKey.localeCompare(b.dateKey));
}

export function formatDateLabel(value: string): string {
  return dateFormatter.format(new Date(value));
}

export function formatTimeRange(start: string, end: string): string {
  return `${timeFormatter.format(new Date(start))} - ${timeFormatter.format(new Date(end))}`;
}

function toDateKey(value: string): string {
  return value.slice(0, 10);
}
