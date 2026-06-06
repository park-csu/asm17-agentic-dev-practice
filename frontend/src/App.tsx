import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin, { DateClickArg } from "@fullcalendar/interaction";
import listPlugin from "@fullcalendar/list";
import timeGridPlugin from "@fullcalendar/timegrid";
import { EventClickArg, EventContentArg, EventInput } from "@fullcalendar/core";
import { FormEvent, useMemo, useState } from "react";

import { mockSchedules } from "./calendar/mockData";
import { buildTaskGroups, findClosestScheduleId, formatDateLabel, formatTimeRange } from "./calendar/model";
import type { CalendarSchedule, ScheduleStatus } from "./calendar/types";

const statusLabel: Record<ScheduleStatus, string> = {
  ok: "ok",
  needs_question: "needs_question",
  fallback: "fallback",
  pending: "대기",
};

type ScheduleFormState = {
  title: string;
  detail: string;
  location: string;
  start_time: string;
  end_time: string;
};

const emptyForm: ScheduleFormState = {
  title: "",
  detail: "",
  location: "",
  start_time: "",
  end_time: "",
};

function toCalendarEvents(schedules: CalendarSchedule[], selectedScheduleId: string): EventInput[] {
  return schedules.map((schedule) => ({
    id: schedule.id,
    title: schedule.title,
    start: schedule.start_time,
    end: schedule.end_time,
    classNames: [
      "taskpilot-event",
      `taskpilot-event-${schedule.status}`,
      getDurationMinutes(schedule.start_time, schedule.end_time) <= 60 ? "taskpilot-event-compact" : "",
      schedule.id === selectedScheduleId ? "taskpilot-event-selected" : "",
    ].filter(Boolean),
    extendedProps: {
      status: schedule.status,
      location: schedule.location,
    },
  }));
}

function renderEventContent(info: EventContentArg) {
  const status = info.event.extendedProps.status as ScheduleStatus;
  return (
    <div className="calendar-event-content">
      <span className={`calendar-event-status status-${status}`} aria-hidden="true" />
      <span className="calendar-event-time">{info.timeText}</span>
      <span className="calendar-event-title">{info.event.title}</span>
    </div>
  );
}

function getDurationMinutes(start: string, end: string): number {
  return Math.max(0, Math.round((new Date(end).getTime() - new Date(start).getTime()) / 60000));
}

function toInputDateTime(value: string): string {
  return value.slice(0, 16);
}

function toLocalInputDateTime(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hour = String(date.getHours()).padStart(2, "0");
  const minute = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hour}:${minute}`;
}

function addMinutes(value: string, minutes: number): string {
  const date = new Date(value);
  date.setMinutes(date.getMinutes() + minutes);
  return toLocalInputDateTime(date);
}

function scheduleToForm(schedule: CalendarSchedule): ScheduleFormState {
  return {
    title: schedule.title,
    detail: schedule.detail,
    location: schedule.location,
    start_time: toInputDateTime(schedule.start_time),
    end_time: toInputDateTime(schedule.end_time),
  };
}

export default function App() {
  const [schedules, setSchedules] = useState<CalendarSchedule[]>(mockSchedules);
  const [selectedScheduleId, setSelectedScheduleId] = useState(() => findClosestScheduleId(mockSchedules));
  const [newScheduleForm, setNewScheduleForm] = useState<ScheduleFormState | null>(null);
  const [detailScheduleId, setDetailScheduleId] = useState("");
  const [detailForm, setDetailForm] = useState<ScheduleFormState>(emptyForm);

  const selectedSchedule = schedules.find((schedule) => schedule.id === selectedScheduleId) ?? null;
  const calendarEvents = useMemo(() => toCalendarEvents(schedules, selectedScheduleId), [schedules, selectedScheduleId]);
  const taskGroups = useMemo(() => buildTaskGroups(schedules), [schedules]);

  function handleEventClick(info: EventClickArg) {
    setSelectedScheduleId(info.event.id);
    openDetail(info.event.id);
  }

  function handleDateSelect(info: { startStr: string; endStr: string; view: { calendar: { unselect: () => void } } }) {
    openNewSchedule(info.startStr, info.endStr);
    info.view.calendar.unselect();
  }

  function handleDateClick(info: DateClickArg) {
    openNewSchedule(info.dateStr, addMinutes(info.dateStr, 60));
  }

  function openNewSchedule(start = "", end = "") {
    const now = new Date();
    const fallbackStart = start || toLocalInputDateTime(now);
    setNewScheduleForm({
      title: "",
      detail: "",
      location: "",
      start_time: toInputDateTime(fallbackStart),
      end_time: toInputDateTime(end || addMinutes(fallbackStart, 60)),
    });
  }

  function openDetail(scheduleId: string) {
    const schedule = schedules.find((item) => item.id === scheduleId);
    if (!schedule) {
      return;
    }
    setSelectedScheduleId(scheduleId);
    setDetailScheduleId(scheduleId);
    setDetailForm(scheduleToForm(schedule));
  }

  function closeDetail() {
    setDetailScheduleId("");
    setDetailForm(emptyForm);
  }

  function submitNewSchedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newScheduleForm) {
      return;
    }

    const schedule: CalendarSchedule = {
      id: `mock-${crypto.randomUUID()}`,
      title: newScheduleForm.title.trim() || "제목 없는 일정",
      detail: newScheduleForm.detail,
      location: newScheduleForm.location,
      start_time: newScheduleForm.start_time,
      end_time: newScheduleForm.end_time,
      status: "pending",
      tasks: [],
    };

    setSchedules((current) => [...current, schedule]);
    setSelectedScheduleId(schedule.id);
    setNewScheduleForm(null);
  }

  function submitDetail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSchedules((current) =>
      current.map((schedule) =>
        schedule.id === detailScheduleId
          ? {
              ...schedule,
              title: detailForm.title.trim() || "제목 없는 일정",
              detail: detailForm.detail,
              location: detailForm.location,
            }
          : schedule,
      ),
    );
    closeDetail();
  }

  function deleteDetailSchedule() {
    deleteScheduleById(detailScheduleId);
    closeDetail();
  }

  function deleteScheduleById(scheduleId: string) {
    setSchedules((current) => current.filter((schedule) => schedule.id !== scheduleId));
    if (selectedScheduleId === scheduleId) {
      setSelectedScheduleId("");
    }
    if (detailScheduleId === scheduleId) {
      closeDetail();
    }
  }

  return (
    <main className="app-shell">
      <aside className="schedule-sidebar" aria-label="일정 목록">
        <header className="sidebar-header">
          <div>
            <p className="eyebrow">TaskPilot</p>
            <h1>일정</h1>
          </div>
          <button className="icon-button" type="button" aria-label="새 일정" onClick={() => openNewSchedule()}>
            +
          </button>
        </header>

        <div className="schedule-list">
          {schedules.length === 0 && <p className="empty-text">일정 없음</p>}
          {schedules.map((schedule) => (
            <button
              key={schedule.id}
              className={`schedule-list-item ${schedule.id === selectedScheduleId ? "selected" : ""}`}
              type="button"
              onClick={() => setSelectedScheduleId(schedule.id)}
            >
              <span className="schedule-list-main">
                <strong>{schedule.title}</strong>
                <span>{formatTimeRange(schedule.start_time, schedule.end_time)}</span>
                <span>{schedule.location || "위치 없음"}</span>
              </span>
              <span className={`status-pill status-${schedule.status}`}>{statusLabel[schedule.status]}</span>
              <span className="schedule-list-actions" aria-label={`${schedule.title} 작업`}>
                <span
                  className="list-action-button"
                  role="button"
                  tabIndex={0}
                  aria-label={`${schedule.title} 수정`}
                  title="수정"
                  onClick={(event) => {
                    event.stopPropagation();
                    openDetail(schedule.id);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      event.stopPropagation();
                      openDetail(schedule.id);
                    }
                  }}
                >
                  <i className="fa-solid fa-pen-to-square" aria-hidden="true" />
                </span>
                <span
                  className="list-action-button danger"
                  role="button"
                  tabIndex={0}
                  aria-label={`${schedule.title} 삭제`}
                  title="삭제"
                  onClick={(event) => {
                    event.stopPropagation();
                    deleteScheduleById(schedule.id);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      event.stopPropagation();
                      deleteScheduleById(schedule.id);
                    }
                  }}
                >
                  <i className="fa-solid fa-trash-can" aria-hidden="true" />
                </span>
              </span>
            </button>
          ))}
        </div>
      </aside>

      <section className="calendar-pane" aria-label="캘린더">
        <header className="workspace-topbar">
          <div>
            <p className="eyebrow">Calendar</p>
            <h2>{selectedSchedule ? selectedSchedule.title : "선택된 일정 없음"}</h2>
          </div>
          {selectedSchedule && (
            <div className="selected-meta">
              <span>{formatDateLabel(selectedSchedule.start_time)}</span>
              <span>{formatTimeRange(selectedSchedule.start_time, selectedSchedule.end_time)}</span>
            </div>
          )}
        </header>

        <div className="calendar-surface">
          <FullCalendar
            plugins={[dayGridPlugin, interactionPlugin, listPlugin, timeGridPlugin]}
            initialView="timeGridWeek"
            headerToolbar={{
              left: "prev,next today",
              center: "title",
              right: "dayGridMonth,timeGridWeek,timeGridDay,listWeek",
            }}
            buttonText={{
              today: "오늘",
              month: "월",
              week: "주",
              day: "일",
              list: "목록",
            }}
            allDaySlot={false}
            selectable
            selectMirror
            nowIndicator
            height="100%"
            locale="ko"
            events={calendarEvents}
            eventContent={renderEventContent}
            eventClick={handleEventClick}
            select={handleDateSelect}
            dateClick={handleDateClick}
            slotMinTime="07:00:00"
            slotMaxTime="23:00:00"
          />
        </div>
      </section>

      <aside className="task-board" aria-label="날짜별 task 목록">
        <header className="task-board-header">
          <div>
            <p className="eyebrow">Tasks</p>
            <h2>날짜별 task</h2>
          </div>
          <span>{taskGroups.reduce((sum, group) => sum + group.taskCount, 0)}개</span>
        </header>

        <div className="task-group-list">
          {taskGroups.length === 0 && <p className="empty-text">생성된 task 없음</p>}
          {taskGroups.map((group) => (
            <section key={group.dateKey} className="task-date-group">
              <header className="task-date-header">
                <strong>{group.dateLabel}</strong>
                <span>{group.taskCount}개</span>
              </header>
              {group.schedules.map((schedule) => (
                <button
                  key={schedule.id}
                  className={`task-schedule-block ${schedule.id === selectedScheduleId ? "selected" : ""}`}
                  type="button"
                  onClick={() => setSelectedScheduleId(schedule.id)}
                >
                  <div className="task-schedule-title">
                    <strong>{schedule.title}</strong>
                    <span>{formatTimeRange(schedule.start_time, schedule.end_time)}</span>
                  </div>
                  {schedule.tasks.length === 0 ? (
                    <p className="empty-text">아직 생성된 task가 없습니다.</p>
                  ) : (
                    <ol className="task-list">
                      {schedule.tasks.map((task) => (
                        <li key={task.id}>
                          <span>{task.title}</span>
                          <small>{task.estimated_minutes}분</small>
                        </li>
                      ))}
                    </ol>
                  )}
                </button>
              ))}
            </section>
          ))}
        </div>
      </aside>

      {newScheduleForm && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="new-schedule-title">
            <header className="modal-header">
              <div>
                <p className="eyebrow">New Schedule</p>
                <h2 id="new-schedule-title">새 일정</h2>
              </div>
              <button className="ghost-button" type="button" onClick={() => setNewScheduleForm(null)}>
                닫기
              </button>
            </header>
            <form className="modal-form" onSubmit={submitNewSchedule}>
              <ScheduleFields form={newScheduleForm} onChange={setNewScheduleForm} />
              <footer className="modal-actions">
                <button className="primary-button" type="submit">
                  일정 추가
                </button>
              </footer>
            </form>
          </section>
        </div>
      )}

      {detailScheduleId && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="detail-schedule-title">
            <header className="modal-header">
              <div>
                <p className="eyebrow">Schedule Detail</p>
                <h2 id="detail-schedule-title">상세 일정</h2>
              </div>
              <button className="ghost-button" type="button" onClick={closeDetail}>
                닫기
              </button>
            </header>
            <form className="modal-form" onSubmit={submitDetail}>
              <ScheduleFields form={detailForm} onChange={setDetailForm} readOnlyTime />
              <footer className="modal-actions split">
                <button className="danger-button" type="button" onClick={deleteDetailSchedule}>
                  삭제
                </button>
                <div>
                  <button className="ghost-button" type="button" disabled>
                    task 재생성
                  </button>
                  <button className="primary-button" type="submit">
                    저장
                  </button>
                </div>
              </footer>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}

function ScheduleFields({
  form,
  onChange,
  readOnlyTime = false,
}: {
  form: ScheduleFormState;
  onChange: (value: ScheduleFormState) => void;
  readOnlyTime?: boolean;
}) {
  function update(field: keyof ScheduleFormState, value: string) {
    onChange({ ...form, [field]: value });
  }

  return (
    <>
      <label>
        일정 제목
        <input value={form.title} onChange={(event) => update("title", event.target.value)} autoFocus />
      </label>
      <label>
        상세 내용
        <textarea value={form.detail} onChange={(event) => update("detail", event.target.value)} />
      </label>
      <label>
        위치
        <input value={form.location} onChange={(event) => update("location", event.target.value)} />
      </label>
      <div className="modal-field-grid">
        <label>
          시작 시간
          <input
            type="datetime-local"
            value={form.start_time}
            readOnly={readOnlyTime}
            onChange={(event) => update("start_time", event.target.value)}
          />
        </label>
        <label>
          종료 시간
          <input
            type="datetime-local"
            value={form.end_time}
            readOnly={readOnlyTime}
            onChange={(event) => update("end_time", event.target.value)}
          />
        </label>
      </div>
    </>
  );
}
