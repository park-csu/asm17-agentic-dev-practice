import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin, { DateClickArg } from "@fullcalendar/interaction";
import listPlugin from "@fullcalendar/list";
import timeGridPlugin from "@fullcalendar/timegrid";
import { EventClickArg, EventContentArg, EventInput } from "@fullcalendar/core";
import type { Session } from "@supabase/supabase-js";
import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  deleteSchedule,
  fetchSchedule,
  fetchSchedules,
  streamCreateSchedule,
  streamRegenerateSchedule,
  updateSchedule,
  updateTaskDone,
} from "./api/client";
import type { AgentNodeName, StreamDoneData, StreamEvent } from "./api/types";
import { isSupabaseConfigured, signInWithGoogle, signOut, supabase } from "./auth/supabase";
import { apiScheduleToCalendarSchedule, apiSchedulesToCalendarSchedules } from "./calendar/apiAdapter";
import { buildTaskGroups, findClosestScheduleId, formatDateLabel, formatTimeRange } from "./calendar/model";
import type { CalendarSchedule, ScheduleStatus } from "./calendar/types";

const statusLabel: Record<ScheduleStatus, string> = {
  ok: "ok",
  needs_question: "needs_question",
  fallback: "fallback",
  pending: "대기",
};

const streamNodeLabel: Partial<Record<AgentNodeName | string, string>> = {
  pre_validate: "일정 유효성 검증",
  classification: "분해 필요성 판단",
  ask_context: "추가 맥락 반영",
  plan: "task 생성",
  post_validate: "task 검증",
  output: "결과 정리",
  fallback: "대체 응답 생성",
};

type ScheduleFormState = {
  title: string;
  detail: string;
  location: string;
  start_time: string;
  end_time: string;
};

type Notice = {
  tone: "info" | "danger";
  message: string;
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
      fallbackReason: schedule.fallback_reason,
    },
  }));
}

function renderEventContent(info: EventContentArg) {
  const status = info.event.extendedProps.status as ScheduleStatus;
  const fallbackReason = String(info.event.extendedProps.fallbackReason ?? "");
  const title = status === "fallback" ? getFallbackReason(fallbackReason) : undefined;
  return (
    <div className="calendar-event-content" title={title}>
      <span className={`calendar-event-status status-${status}`} aria-hidden="true" />
      <span className="calendar-event-time">{info.timeText}</span>
      <span className="calendar-event-title">{info.event.title}</span>
      {status === "fallback" && <span className="calendar-event-reason">{getFallbackReason(fallbackReason)}</span>}
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

function buildContinuationPayload(doneData: StreamDoneData, contextAnswer: string) {
  return {
    context_answer: contextAnswer,
    question: doneData.question,
    question_source: doneData.question_source,
    classification_retry: doneData.classification_retry,
    pre_validation_retry: doneData.pre_validation_retry,
    plan_retry: doneData.plan_retry,
    detail_with_context: doneData.detail_with_context,
  };
}

function getFallbackReason(reason: string): string {
  return reason.trim() || "task 생성에 실패했습니다.";
}

function createTemporaryScheduleId(): string {
  return `temp-schedule-${crypto.randomUUID()}`;
}

export default function App() {
  const [schedules, setSchedules] = useState<CalendarSchedule[]>([]);
  const [selectedScheduleId, setSelectedScheduleId] = useState("");
  const [newScheduleForm, setNewScheduleForm] = useState<ScheduleFormState | null>(null);
  const [detailScheduleId, setDetailScheduleId] = useState("");
  const [detailForm, setDetailForm] = useState<ScheduleFormState>(emptyForm);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [loadingScheduleId, setLoadingScheduleId] = useState("");
  const [streamProgress, setStreamProgress] = useState("");
  const [notice, setNotice] = useState<Notice | null>(null);
  const [streamContextByScheduleId, setStreamContextByScheduleId] = useState<Record<string, StreamDoneData>>({});
  const [contextAnswer, setContextAnswer] = useState("");
  const [authSession, setAuthSession] = useState<Session | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isSigningIn, setIsSigningIn] = useState(false);
  const [authError, setAuthError] = useState("");

  const accessToken = authSession?.access_token ?? "";
  const isCreatingNewSchedule = loadingScheduleId.startsWith("temp-schedule-");
  const selectedSchedule = schedules.find((schedule) => schedule.id === selectedScheduleId) ?? null;
  const calendarEvents = useMemo(() => toCalendarEvents(schedules, selectedScheduleId), [schedules, selectedScheduleId]);
  const taskGroups = useMemo(() => buildTaskGroups(schedules), [schedules]);
  const selectedContinuation = selectedSchedule ? streamContextByScheduleId[selectedSchedule.id] : undefined;
  const canAnswerQuestion =
    selectedSchedule?.status === "needs_question" && selectedContinuation && selectedContinuation.question.trim().length > 0;

  useEffect(() => {
    if (!supabase) {
      setIsAuthLoading(false);
      setIsInitialLoading(false);
      return;
    }

    let isMounted = true;
    void supabase.auth.getSession().then(({ data, error }) => {
      if (!isMounted) {
        return;
      }
      if (error) {
        setAuthError(error.message);
      }
      setAuthSession(data.session);
      setIsAuthLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setAuthSession(session);
      setAuthError("");
      setIsAuthLoading(false);
      if (!session) {
        setSchedules([]);
        setSelectedScheduleId("");
        setStreamContextByScheduleId({});
      }
    });

    return () => {
      isMounted = false;
      subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (isAuthLoading) {
      return;
    }
    if (!isSupabaseConfigured || !accessToken) {
      setSchedules([]);
      setSelectedScheduleId("");
      setIsInitialLoading(false);
      return;
    }
    void loadSchedules(accessToken);
  }, [accessToken, isAuthLoading]);

  async function loadSchedules(token = accessToken) {
    setIsInitialLoading(true);
    try {
      const apiSchedules = await fetchSchedules({ accessToken: token });
      const nextSchedules = apiSchedulesToCalendarSchedules(apiSchedules);
      setSchedules(nextSchedules);
      setSelectedScheduleId((current) => {
        if (current && nextSchedules.some((schedule) => schedule.id === current)) {
          return current;
        }
        return findClosestScheduleId(nextSchedules);
      });
      setNotice(null);
    } catch (error) {
      setNotice({ tone: "danger", message: getErrorMessage(error, "일정 목록을 불러오지 못했습니다.") });
    } finally {
      setIsInitialLoading(false);
    }
  }

  async function refreshSchedule(scheduleId: string) {
    const apiSchedule = await fetchSchedule(scheduleId, { accessToken });
    const nextSchedule = apiScheduleToCalendarSchedule(apiSchedule);
    setSchedules((current) => {
      const exists = current.some((schedule) => schedule.id === scheduleId);
      if (!exists) {
        return [...current, nextSchedule];
      }
      return current.map((schedule) => (schedule.id === scheduleId ? nextSchedule : schedule));
    });
    return nextSchedule;
  }

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

  async function submitNewSchedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newScheduleForm) {
      return;
    }

    const payload = {
      title: newScheduleForm.title.trim() || "제목 없는 일정",
      detail: newScheduleForm.detail,
      location: newScheduleForm.location,
      start_time: newScheduleForm.start_time,
      end_time: newScheduleForm.end_time,
    };

    const temporaryScheduleId = createTemporaryScheduleId();
    const temporarySchedule: CalendarSchedule = {
      id: temporaryScheduleId,
      title: payload.title,
      detail: payload.detail,
      location: payload.location,
      start_time: payload.start_time,
      end_time: payload.end_time,
      status: "pending",
      fallback_reason: "",
      tasks: [],
    };

    setNewScheduleForm(null);
    setSchedules((current) => [temporarySchedule, ...current]);
    setSelectedScheduleId(temporaryScheduleId);
    setLoadingScheduleId(temporaryScheduleId);
    setStreamProgress("에이전트 실행 중");
    setNotice({ tone: "info", message: "새 일정 생성 중: 에이전트 실행 중" });

    try {
      const doneData = await streamCreateSchedule(payload, { accessToken, onEvent: handleStreamEvent });
      const apiSchedule = await fetchSchedule(doneData.schedule_id, { accessToken });
      const schedule = apiScheduleToCalendarSchedule(apiSchedule);
      setSchedules((current) => {
        const withoutDuplicate = current.filter((item) => item.id !== doneData.schedule_id);
        const replaced = withoutDuplicate.map((item) => (item.id === temporaryScheduleId ? schedule : item));
        if (replaced.some((item) => item.id === schedule.id)) {
          return replaced;
        }
        return [schedule, ...replaced.filter((item) => item.id !== temporaryScheduleId)];
      });
      setSelectedScheduleId(schedule.id);
      rememberContinuation(doneData);
      setNotice({ tone: "info", message: "일정 생성이 완료되었습니다." });
    } catch (error) {
      setNotice({ tone: "danger", message: getErrorMessage(error, "일정 생성에 실패했습니다.") });
      await loadSchedules();
    } finally {
      setLoadingScheduleId("");
      setStreamProgress("");
    }
  }

  async function submitDetail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!detailScheduleId) {
      return;
    }

    setLoadingScheduleId(detailScheduleId);
    try {
      const apiSchedule = await updateSchedule(
        detailScheduleId,
        {
          title: detailForm.title.trim() || "제목 없는 일정",
          detail: detailForm.detail,
          location: detailForm.location,
        },
        { accessToken },
      );
      const nextSchedule = apiScheduleToCalendarSchedule(apiSchedule);
      setSchedules((current) => current.map((schedule) => (schedule.id === detailScheduleId ? nextSchedule : schedule)));
      setNotice({ tone: "info", message: "일정을 저장했습니다." });
      closeDetail();
    } catch (error) {
      setNotice({ tone: "danger", message: getErrorMessage(error, "일정 저장에 실패했습니다.") });
    } finally {
      setLoadingScheduleId("");
    }
  }

  async function deleteDetailSchedule() {
    await deleteScheduleById(detailScheduleId);
    closeDetail();
  }

  async function deleteScheduleById(scheduleId: string) {
    if (!scheduleId) {
      return;
    }

    setLoadingScheduleId(scheduleId);
    try {
      await deleteSchedule(scheduleId, { accessToken });
      setSchedules((current) => current.filter((schedule) => schedule.id !== scheduleId));
      setStreamContextByScheduleId((current) => {
        const next = { ...current };
        delete next[scheduleId];
        return next;
      });
      if (selectedScheduleId === scheduleId) {
        setSelectedScheduleId("");
      }
      if (detailScheduleId === scheduleId) {
        closeDetail();
      }
      setNotice({ tone: "info", message: "일정을 삭제했습니다." });
    } catch (error) {
      setNotice({ tone: "danger", message: getErrorMessage(error, "일정 삭제에 실패했습니다.") });
    } finally {
      setLoadingScheduleId("");
    }
  }

  async function regenerateScheduleById(scheduleId: string, payload?: ReturnType<typeof buildContinuationPayload>) {
    if (!scheduleId) {
      return;
    }

    closeDetail();
    setLoadingScheduleId(scheduleId);
    setStreamProgress("에이전트 실행 중");
    setNotice({ tone: "info", message: "task 재생성 중: 에이전트 실행 중" });

    try {
      const doneData = await streamRegenerateSchedule(scheduleId, payload, { accessToken, onEvent: handleStreamEvent });
      await refreshSchedule(scheduleId);
      rememberContinuation(doneData);
      setSelectedScheduleId(scheduleId);
      setContextAnswer("");
      setNotice({ tone: "info", message: "task 재생성이 완료되었습니다." });
    } catch (error) {
      setNotice({ tone: "danger", message: getErrorMessage(error, "task 재생성에 실패했습니다.") });
    } finally {
      setLoadingScheduleId("");
      setStreamProgress("");
    }
  }

  async function submitContextAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedSchedule || !selectedContinuation || !contextAnswer.trim()) {
      return;
    }

    await regenerateScheduleById(selectedSchedule.id, buildContinuationPayload(selectedContinuation, contextAnswer.trim()));
  }

  async function toggleTask(scheduleId: string, taskId: string, isDone: boolean) {
    setSchedules((current) =>
      current.map((schedule) =>
        schedule.id === scheduleId
          ? {
              ...schedule,
              tasks: schedule.tasks.map((task) => (task.id === taskId ? { ...task, is_done: isDone } : task)),
            }
          : schedule,
      ),
    );

    try {
      const apiTask = await updateTaskDone(scheduleId, taskId, isDone, { accessToken });
      setSchedules((current) =>
        current.map((schedule) =>
          schedule.id === scheduleId
            ? {
                ...schedule,
                tasks: schedule.tasks.map((task) => (task.id === taskId ? { ...task, ...apiTask } : task)),
              }
            : schedule,
        ),
      );
    } catch (error) {
      setSchedules((current) =>
        current.map((schedule) =>
          schedule.id === scheduleId
            ? {
                ...schedule,
                tasks: schedule.tasks.map((task) => (task.id === taskId ? { ...task, is_done: !isDone } : task)),
              }
            : schedule,
        ),
      );
      setNotice({ tone: "danger", message: getErrorMessage(error, "task 상태 저장에 실패했습니다.") });
    }
  }

  function rememberContinuation(doneData: StreamDoneData) {
    setStreamContextByScheduleId((current) => {
      if (doneData.status !== "needs_question") {
        const next = { ...current };
        delete next[doneData.schedule_id];
        return next;
      }
      return { ...current, [doneData.schedule_id]: doneData };
    });
  }

  function handleStreamEvent(event: StreamEvent) {
    if (event.event === "node") {
      const nodeName = event.node ?? "";
      const label = streamNodeLabel[nodeName] ?? nodeName;
      const message = label ? `${label} 완료` : "에이전트 실행 중";
      setStreamProgress(message);
      setNotice({ tone: "info", message: `에이전트 진행: ${message}` });
      return;
    }
    if (event.event === "done") {
      setStreamProgress("결과 저장 중");
      setNotice({ tone: "info", message: "에이전트 결과 저장 중" });
    }
  }

  async function handleGoogleLogin() {
    setIsSigningIn(true);
    setAuthError("");
    try {
      await signInWithGoogle();
    } catch (error) {
      setAuthError(getErrorMessage(error, "Google 로그인에 실패했습니다."));
    } finally {
      setIsSigningIn(false);
    }
  }

  async function handleSignOut() {
    try {
      await signOut();
      setNotice({ tone: "info", message: "로그아웃했습니다." });
    } catch (error) {
      setNotice({ tone: "danger", message: getErrorMessage(error, "로그아웃에 실패했습니다.") });
    }
  }

  if (isAuthLoading || !authSession) {
    return (
      <main className="auth-shell">
        <section className="auth-panel" aria-labelledby="auth-title">
          <p className="eyebrow">TaskPilot</p>
          <h1 id="auth-title">{isAuthLoading ? "로그인 확인 중" : "로그인"}</h1>
          {!isSupabaseConfigured && <p className="error-text">Supabase 환경변수가 필요합니다.</p>}
          {authError && <p className="error-text">{authError}</p>}
          {!isAuthLoading && isSupabaseConfigured && (
            <button className="primary-button" type="button" disabled={isSigningIn} onClick={() => void handleGoogleLogin()}>
              {isSigningIn ? "연결 중" : "Google로 로그인"}
            </button>
          )}
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      {notice && (
        <div className={`app-toast ${notice.tone}`} role="status">
          <span>{notice.message}</span>
          <button type="button" aria-label="알림 닫기" onClick={() => setNotice(null)}>
            <i className="fa-solid fa-xmark" aria-hidden="true" />
          </button>
        </div>
      )}

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

        {(isInitialLoading || isCreatingNewSchedule) && (
          <div className="inline-notice">
            <strong>{isInitialLoading ? "불러오는 중" : "생성 중"}</strong>
            {streamProgress && <span>{streamProgress}</span>}
          </div>
        )}

        <div className="schedule-list">
          {!isInitialLoading && schedules.length === 0 && <p className="empty-text">일정 없음</p>}
          {schedules.map((schedule) => (
            <button
              key={schedule.id}
              className={`schedule-list-item ${schedule.id === selectedScheduleId ? "selected" : ""} ${
                schedule.status === "fallback" ? "failed" : ""
              }`}
              type="button"
              disabled={loadingScheduleId === schedule.id}
              onClick={() => setSelectedScheduleId(schedule.id)}
            >
              <span className="schedule-list-main">
                <strong>{schedule.title}</strong>
                <span>{formatTimeRange(schedule.start_time, schedule.end_time)}</span>
                <span>{schedule.location || "위치 없음"}</span>
              </span>
              {schedule.status === "fallback" && (
                <span className="fallback-reason">{getFallbackReason(schedule.fallback_reason)}</span>
              )}
              <span className={`status-pill status-${schedule.status}`}>
                {loadingScheduleId === schedule.id ? "생성 중" : statusLabel[schedule.status]}
              </span>
              {loadingScheduleId === schedule.id && streamProgress && <span className="schedule-progress">{streamProgress}</span>}
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
                    void deleteScheduleById(schedule.id);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      event.stopPropagation();
                      void deleteScheduleById(schedule.id);
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
          <div className="topbar-actions">
            {selectedSchedule && (
              <div className="selected-meta">
                <span>{formatDateLabel(selectedSchedule.start_time)}</span>
                <span>{formatTimeRange(selectedSchedule.start_time, selectedSchedule.end_time)}</span>
                {selectedSchedule.status === "fallback" && (
                  <span className="selected-fallback-reason">{getFallbackReason(selectedSchedule.fallback_reason)}</span>
                )}
              </div>
            )}
            <div className="account-box">
              <span>{authSession.user.email ?? "로그인됨"}</span>
              <button className="ghost-button" type="button" onClick={() => void handleSignOut()}>
                로그아웃
              </button>
            </div>
          </div>
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

        {canAnswerQuestion && (
          <form className="clarification-panel" onSubmit={submitContextAnswer}>
            <strong>{selectedContinuation.question}</strong>
            <textarea
              value={contextAnswer}
              placeholder="답변"
              onChange={(event) => setContextAnswer(event.target.value)}
            />
            <button className="primary-button" type="submit" disabled={loadingScheduleId === selectedSchedule?.id}>
              답변 제출
            </button>
          </form>
        )}

        <div className="task-group-list">
          {taskGroups.length === 0 && <p className="empty-text">생성된 task 없음</p>}
          {taskGroups.map((group) => (
            <section key={group.dateKey} className="task-date-group">
              <header className="task-date-header">
                <strong>{group.dateLabel}</strong>
                <span>{group.taskCount}개</span>
              </header>
              {group.schedules.map((schedule) => (
                <div
                  key={schedule.id}
                  className={`task-schedule-block ${schedule.id === selectedScheduleId ? "selected" : ""}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => setSelectedScheduleId(schedule.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelectedScheduleId(schedule.id);
                    }
                  }}
                >
                  <div className="task-schedule-title">
                    <strong>{schedule.title}</strong>
                    <span>{formatTimeRange(schedule.start_time, schedule.end_time)}</span>
                  </div>
                  {schedule.status === "fallback" && (
                    <p className="fallback-reason board">{getFallbackReason(schedule.fallback_reason)}</p>
                  )}
                  {schedule.tasks.length === 0 ? (
                    <p className="empty-text">아직 생성된 task가 없습니다.</p>
                  ) : (
                    <ol className="task-list">
                      {schedule.tasks.map((task) => (
                        <li key={task.id}>
                          <label className="task-check" onClick={(event) => event.stopPropagation()}>
                            <input
                              type="checkbox"
                              checked={task.is_done}
                              onChange={(event) => void toggleTask(schedule.id, task.id, event.target.checked)}
                            />
                            <span>{task.title}</span>
                          </label>
                          <small>{task.estimated_minutes}분</small>
                        </li>
                      ))}
                    </ol>
                  )}
                </div>
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
                <button className="primary-button" type="submit" disabled={isCreatingNewSchedule}>
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
                <button className="danger-button" type="button" onClick={() => void deleteDetailSchedule()}>
                  삭제
                </button>
                <div>
                  <button
                    className="ghost-button"
                    type="button"
                    disabled={loadingScheduleId === detailScheduleId}
                    onClick={() => void regenerateScheduleById(detailScheduleId)}
                  >
                    task 재생성
                  </button>
                  <button className="primary-button" type="submit" disabled={loadingScheduleId === detailScheduleId}>
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
        <textarea value={form.detail} required onChange={(event) => update("detail", event.target.value)} />
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
            required
            readOnly={readOnlyTime}
            onChange={(event) => update("start_time", event.target.value)}
          />
        </label>
        <label>
          종료 시간
          <input
            type="datetime-local"
            value={form.end_time}
            required
            readOnly={readOnlyTime}
            onChange={(event) => update("end_time", event.target.value)}
          />
        </label>
      </div>
    </>
  );
}

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}
