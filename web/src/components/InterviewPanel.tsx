import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, ApiError, type InterviewPrep } from "../api/client";
import { longDate } from "../format";
import { Chat } from "../icons";

/**
 * What they are going to ask, from the exact resume that was sent.
 *
 * Generated on request rather than in the background: you only prep for an
 * interview you actually have, and most applications never get one.
 */
export default function InterviewPanel({
  applicationId,
  hasJd,
  hasResume,
}: {
  applicationId: number;
  hasJd: boolean;
  hasResume: boolean;
}) {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [open, setOpen] = useState<Set<string>>(new Set());

  const prep = useQuery<InterviewPrep>({
    queryKey: ["interview", applicationId],
    queryFn: () => api.interview(applicationId),
    retry: false,
  });

  const make = useMutation({
    mutationFn: () => api.makeInterview(applicationId),
    onSuccess: (data) => {
      setError("");
      queryClient.setQueryData(["interview", applicationId], data);
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  const toggle = (key: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const data = prep.data;
  const missing =
    prep.isError && prep.error instanceof ApiError && prep.error.status === 404;

  return (
    <div className="card">
      <div className="flex">
        <h2 className="grow">
          <Chat size={15} /> Interview prep
        </h2>
        {data && (
          <span className="faint small">{longDate(data.created_at)}</span>
        )}
      </div>

      {error && <div className="banner bad">{error}</div>}

      {(!hasJd || !hasResume) && (
        <p className="sub">
          {!hasJd
            ? "Paste the job description to work out what they will ask."
            : "Compose the resume you are sending — the questions come from it."}
        </p>
      )}

      {data?.stale && (
        <div className="banner warn">
          Your resume changed since this was written, so some of it asks about a
          document you are no longer sending.
        </div>
      )}

      {hasJd && hasResume && (missing || !data) && !make.isPending && (
        <>
          <p className="sub">
            Drills into every claim on the resume you sent and every technology
            the job asks for.
          </p>
          <button type="button" className="primary" onClick={() => make.mutate()}>
            Work out the questions
          </button>
        </>
      )}

      {make.isPending && <span className="working">reading them both closely</span>}

      {data && !make.isPending && (
        <>
          {data.weak_spots.length > 0 && (
            <div className="weak">
              <h3 className="mini-head">Where you are exposed</h3>
              <ul>
                {data.weak_spots.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {data.rounds.map((round) => (
            <section className="round" key={round.name}>
              <h3 className="mini-head">
                {round.name}
                <span className="faint"> · {round.questions.length}</span>
              </h3>
              {round.focus && <p className="faint small">{round.focus}</p>}
              {round.questions.map((q, i) => {
                const key = `${round.name}-${i}`;
                return (
                  <div className="qa" key={key}>
                    <button
                      type="button"
                      className="q"
                      onClick={() => toggle(key)}
                      aria-expanded={open.has(key)}
                    >
                      {open.has(key) ? "▾" : "▸"} {q.question}
                    </button>
                    {open.has(key) && (
                      <div className="a">
                        {q.anchor && (
                          <p className="anchor">From: “{q.anchor}”</p>
                        )}
                        {q.tests && (
                          <p className="muted small">Testing: {q.tests}</p>
                        )}
                        {q.strong_answer && <p>{q.strong_answer}</p>}
                      </div>
                    )}
                  </div>
                );
              })}
            </section>
          ))}

          {data.ask_them.length > 0 && (
            <section className="round">
              <h3 className="mini-head">Ask them</h3>
              <ul className="bullets">
                {data.ask_them.map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </ul>
            </section>
          )}

          <div className="actions" style={{ marginTop: 12 }}>
            <button
              type="button"
              className="ghost small"
              disabled={make.isPending}
              onClick={() => make.mutate()}
            >
              Redo from the current resume
            </button>
          </div>
        </>
      )}
    </div>
  );
}
