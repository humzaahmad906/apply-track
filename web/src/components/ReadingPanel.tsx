import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, ApiError, type ReadingList } from "../api/client";

/**
 * Recommended reading for one application: what the job wants that the resume
 * does not show. Study aid only — none of this reaches the PDF, because it is a
 * list of things the candidate cannot yet claim.
 */
export default function ReadingPanel({
  applicationId,
  hasJd,
}: {
  applicationId: number;
  hasJd: boolean;
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState<Set<string>>(new Set());

  const reading = useQuery<ReadingList>({
    queryKey: ["reading", applicationId],
    queryFn: () => api.reading(applicationId),
    enabled: open,
    // A 404 just means it has never been run; that is not an error state.
    retry: false,
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

  const data = reading.data;
  const missing =
    reading.isError && reading.error instanceof ApiError
      ? reading.error.status === 404
      : false;

  const toggleDone = (path: string) =>
    setDone((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });

  return (
    <div className="card tight">
      <div className="actions">
        <button
          type="button"
          className="ghost small"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? "Hide" : "Show"} recommended reading
        </button>
        {data && (
          <span className="muted small">
            {data.gaps.length} gap{data.gaps.length === 1 ? "" : "s"}
            {data.stale ? " · out of date" : ""}
          </span>
        )}
      </div>

      {open && (
        <div style={{ marginTop: 9 }}>
          {!hasJd && (
            <div className="banner warn">
              Paste the job description above first — there is nothing to compare
              your resume against.
            </div>
          )}
          {error && <div className="banner bad">{error}</div>}

          {data?.stale && (
            <div className="banner warn">
              The job description or your resume changed since this ran. Refresh
              for current advice.
            </div>
          )}

          {reading.isLoading && <div className="muted small">Loading…</div>}

          {missing && !run.isPending && (
            <p className="muted small" style={{ marginTop: 0 }}>
              Compares this job description against the resume you are about to
              send, then recommends lessons from your applied-ml-academy repo for
              whatever is missing. Basics you already have are listed separately,
              never as reading.
            </p>
          )}

          <div className="actions" style={{ marginBottom: 10 }}>
            <button
              type="button"
              className={data ? "" : "primary"}
              disabled={!hasJd || run.isPending}
              onClick={() => run.mutate()}
            >
              {run.isPending
                ? "Analysing… (~20s)"
                : data
                  ? "Refresh analysis"
                  : "Analyse this job"}
            </button>
          </div>

          {data && (
            <>
              <h2 style={{ fontSize: 13, margin: "10px 0 6px" }}>
                Recommended reading
              </h2>
              {data.gaps.length === 0 ? (
                <p className="muted small">
                  Nothing missing — this job asks for nothing your resume does
                  not already show.
                </p>
              ) : (
                data.gaps.map((gap) => (
                  <div key={gap.skill} style={{ marginBottom: 10 }}>
                    <strong className="small">{gap.skill}</strong>
                    {gap.why && (
                      <div className="muted small" style={{ marginBottom: 3 }}>
                        {gap.why}
                      </div>
                    )}
                    {gap.lessons.length === 0 && (
                      <div className="muted small">
                        No lesson in your repo covers this yet.
                      </div>
                    )}
                    {gap.lessons.map((lesson) => (
                      <label
                        key={lesson.path}
                        className="small"
                        style={{
                          display: "flex",
                          gap: 6,
                          alignItems: "baseline",
                          marginBottom: 2,
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={done.has(lesson.path)}
                          onChange={() => toggleDone(lesson.path)}
                        />
                        <a
                          href={lesson.url}
                          target="_blank"
                          rel="noreferrer"
                          style={{
                            textDecoration: done.has(lesson.path)
                              ? "line-through"
                              : undefined,
                          }}
                        >
                          {lesson.title}
                        </a>
                        <span className="muted" style={{ fontSize: 11 }}>
                          {lesson.course}
                        </span>
                      </label>
                    ))}
                  </div>
                ))
              )}

              {data.covered.length > 0 && (
                <>
                  <h2 style={{ fontSize: 13, margin: "14px 0 4px" }}>
                    Already covered
                  </h2>
                  <p className="muted small" style={{ margin: "0 0 5px" }}>
                    The job asks for these and your resume proves them — make
                    sure the bullets below are switched on.
                  </p>
                  {data.covered.map((c) => (
                    <div key={c.skill} className="small" style={{ marginBottom: 3 }}>
                      <strong>{c.skill}</strong>
                      {c.evidence && (
                        <span className="muted"> — {c.evidence}</span>
                      )}
                    </div>
                  ))}
                </>
              )}

              {data.basics.length > 0 && (
                <>
                  <h2 style={{ fontSize: 13, margin: "14px 0 4px" }}>
                    Basics — noted, not recommended
                  </h2>
                  <p className="muted small" style={{ margin: 0 }}>
                    {data.basics.join(", ")}
                  </p>
                </>
              )}

              <p className="muted" style={{ fontSize: 11, marginTop: 12 }}>
                Ran against {data.lesson_count} lessons. Never included in the
                exported PDF.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
