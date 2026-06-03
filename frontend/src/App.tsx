import { FormEvent, useState } from "react";

type ScheduleTask = {
  title?: string;
  description?: string;
  estimated_minutes?: number;
  order_index?: number;
};

type ScheduleTaskResponse = {
  status: "ok" | "fallback" | "needs_question";
  title?: string;
  tasks?: ScheduleTask[];
  question?: string;
  fallback_reason?: string;
  answer?: string;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8001";

export default function App() {
  const [title, setTitle] = useState("기말 발표 준비");
  const [detail, setDetail] = useState("자료 조사하고 발표자료를 만들어야 함");
  const [startTime, setStartTime] = useState("2026-06-05 13:00");
  const [endTime, setEndTime] = useState("2026-06-05 15:00");
  const [maxRetry, setMaxRetry] = useState(2);
  const [result, setResult] = useState<ScheduleTaskResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/schedules/tasks/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          detail,
          start_time: startTime,
          end_time: endTime,
          existing_schedules: [],
          max_retry: maxRetry,
        }),
      });

      if (!response.ok) {
        throw new Error(`API 요청 실패: ${response.status}`);
      }

      setResult(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <div className="panel input-panel">
          <div className="panel-heading">
            <p className="eyebrow">TaskPilot</p>
            <h1>일정 task 생성</h1>
          </div>

          <form onSubmit={submit} className="schedule-form">
            <label>
              일정 제목
              <input value={title} onChange={(event) => setTitle(event.target.value)} />
            </label>

            <label>
              상세 내용
              <textarea value={detail} onChange={(event) => setDetail(event.target.value)} />
            </label>

            <div className="field-grid">
              <label>
                시작 시간
                <input value={startTime} onChange={(event) => setStartTime(event.target.value)} />
              </label>
              <label>
                종료 시간
                <input value={endTime} onChange={(event) => setEndTime(event.target.value)} />
              </label>
            </div>

            <label>
              최대 재시도 횟수
              <input
                type="number"
                min={0}
                max={5}
                value={maxRetry}
                onChange={(event) => setMaxRetry(Number(event.target.value))}
              />
            </label>

            <button type="submit" disabled={loading}>
              {loading ? "분석 중" : "task 생성"}
            </button>
          </form>
        </div>

        <div className="panel result-panel">
          <div className="panel-heading">
            <p className="eyebrow">Agent Result</p>
            <h2>생성 결과</h2>
          </div>

          {error && <p className="error-text">{error}</p>}
          {!error && !result && <p className="empty-text">일정을 입력하고 task를 생성하세요.</p>}
          {result?.status === "needs_question" && <p className="warning-text">{result.question}</p>}
          {result?.status === "fallback" && (
            <p className="error-text">{result.fallback_reason || result.answer || "task 생성에 실패했습니다."}</p>
          )}
          {result?.status === "ok" && (
            <div className="task-list">
              <p className="success-text">{result.answer || "task를 생성했습니다."}</p>
              {(result.tasks ?? []).map((task, index) => (
                <article key={`${task.title}-${index}`} className="task-item">
                  <div className="task-meta">
                    <span>{task.order_index ?? index + 1}</span>
                    <strong>{task.title}</strong>
                  </div>
                  <p>{task.description}</p>
                  <small>{task.estimated_minutes ?? "-"}분</small>
                </article>
              ))}
            </div>
          )}

          {result && (
            <details className="raw-response">
              <summary>API 응답</summary>
              <pre>{JSON.stringify(result, null, 2)}</pre>
            </details>
          )}
        </div>
      </section>
    </main>
  );
}
