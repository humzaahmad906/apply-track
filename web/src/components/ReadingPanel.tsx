import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, ApiError, type Reading, type ReadingList } from "../api/client";
import { Book, Check, Sparkles } from "../icons";

/** Defined out here so it is not remounted on every tick of the parent. */
function Lessons({
  lessons,
  done,
  onToggle,
}: {
  lessons: Reading[];
  done: Set<string>;
  onToggle: (path: string) => void;
}) {
  if (lessons.length === 0) {
    return <div className="faint small">Nothing in your repo covers this yet.</div>;
  }
  return (
    <>
      {lessons.map((lesson) => (
        <label key={lesson.path} className="lesson">
          <input
            type="checkbox"
            checked={done.has(lesson.path)}
            onChange={() => onToggle(lesson.path)}
          />
          <a
            href={lesson.url}
            target="_blank"
            rel="noreferrer"
            className={done.has(lesson.path) ? "read" : undefined}
          >
            {lesson.title}
          </a>
          <span className="faint">{lesson.course}</span>
        </label>
      ))}
    </>
  );
}

/**
 * What this job wants that this resume does not show.
 *
 * There is no "analyse" button: saving a job description or editing the resume
 * schedules the comparison, and this panel shows whatever came back. The only
 * button is an escape hatch for when a background run failed.
 *
 * None of it reaches the PDF. It is a list of things you cannot claim yet.
 */
export default function ReadingPanel({
  applicationId,
  hasJd,
  hasResume,
}: {
  applicationId: number;
  hasJd: boolean;
  hasResume: boolean;
}) {
  const queryClient = useQueryClient();
  const [done, setDone] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");

  const reading = useQuery<ReadingList>({
    queryKey: ["reading", applicationId],
    queryFn: () => api.reading(applicationId),
    // Poll only while the queue is actually working on this one.
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      return state === "pending" || state === "running" ? 2000 : false;
    },
  });

  const run = useMutation({
    mutationFn: () => api.runReading(applicationId),
    onSuccess: (data) => {
      setError("");
      queryClient.setQueryData(["reading", applicationId], data);
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  const toggle = (path: string) =>
    setDone((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });

  const data = reading.data;
  const working = data?.state === "pending" || data?.state === "running";
  const nothingYet = !data?.created_at;

  return (
    <div className="card">
      <div className="flex">
        <h2 className="grow">Prep</h2>
        {working && <span className="working">reading the job</span>}
      </div>

      {!hasJd && (
        <p className="sub">
          Paste the job description and this fills itself in — what the role
          wants that your resume does not show yet.
        </p>
      )}
      {hasJd && !hasResume && (
        <p className="sub">
          Compose a resume for this job and the comparison runs on its own.
        </p>
      )}

      {error && <div className="banner bad">{error}</div>}

      {data?.error && !working && (
        <div className="banner warn">
          The last run failed: {data.error}
          <div className="actions" style={{ marginTop: 8 }}>
            <button
              type="button"
              disabled={run.isPending}
              onClick={() => run.mutate()}
            >
              {run.isPending ? "Running…" : "Try again"}
            </button>
          </div>
        </div>
      )}

      {data?.stale && !working && (
        <div className="banner warn">
          Out of date since you last edited this — a refresh is queued.
        </div>
      )}

      {hasJd && hasResume && nothingYet && !working && !data?.error && (
        <p className="sub">Queued — this fills in shortly.</p>
      )}

      {data && !nothingYet && (
        <>
          {data.gaps.length > 0 && (
            <section className="prep-group">
              <h3>
                <Sparkles size={13} /> Learn this
              </h3>
              <p className="faint small">
                The job asks for it and your resume does not show it yet.
              </p>
              {data.gaps.map((gap) => (
                <div className="prep-skill" key={gap.skill}>
                  <strong>{gap.skill}</strong>
                  {gap.why && <div className="muted small">{gap.why}</div>}
                  <Lessons lessons={gap.lessons} done={done} onToggle={toggle} />
                </div>
              ))}
            </section>
          )}

          {data.covered.length > 0 && (
            <section className="prep-group">
              <h3>
                <Check size={13} /> Revise this
              </h3>
              <p className="faint small">
                Your resume proves these — make sure those bullets are switched
                on, then go a level deeper than you wrote.
              </p>
              {data.covered.map((c) => (
                <div className="prep-skill" key={c.skill}>
                  <strong>{c.skill}</strong>
                  {c.evidence && (
                    <div className="muted small">Shown in: {c.evidence}</div>
                  )}
                  <Lessons lessons={c.lessons} done={done} onToggle={toggle} />
                </div>
              ))}
            </section>
          )}

          {data.basics.length > 0 && (
            <section className="prep-group">
              <h3>
                <Book size={13} /> Foundations
              </h3>
              <p className="faint small">
                Assumed for the role. Worth a refresher before the call.
              </p>
              {data.basics.map((b) => (
                <div className="prep-skill" key={b.skill}>
                  <strong>{b.skill}</strong>
                  <Lessons lessons={b.lessons} done={done} onToggle={toggle} />
                </div>
              ))}
            </section>
          )}

          <p className="faint small" style={{ marginTop: 12, marginBottom: 0 }}>
            Every requirement in this job, against {data.lesson_count} lessons.
            Never printed on the resume.
          </p>
        </>
      )}
    </div>
  );
}
