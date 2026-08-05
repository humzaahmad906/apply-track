import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  api,
  ApiError,
  type BuildStatus,
  type ProjectSpec,
} from "../api/client";
import { ArrowRight, Check, Lightbulb, Target } from "../icons";

const STATUS_LABEL: Record<BuildStatus, string> = {
  idea: "Just an idea",
  building: "Building it",
  built: "Built",
};

/**
 * The project this company would be impressed by.
 *
 * Deliberately a plan first. It only becomes a resume entry once you mark it
 * built — an interviewer will ask a second question about anything on there,
 * and there is no good answer to that if the thing does not exist.
 */
export default function ProjectPanel({
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
  const [note, setNote] = useState("");

  const project = useQuery<ProjectSpec>({
    queryKey: ["project", applicationId],
    queryFn: () => api.project(applicationId),
    retry: false,
  });

  const make = useMutation({
    mutationFn: () => api.makeProject(applicationId),
    onSuccess: (data) => {
      setError("");
      queryClient.setQueryData(["project", applicationId], data);
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  const setStatus = useMutation({
    mutationFn: (status: BuildStatus) => api.setProjectStatus(applicationId, status),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["project", applicationId] }),
  });

  const adopt = useMutation({
    mutationFn: () => api.adoptProject(applicationId),
    onSuccess: () => {
      setError("");
      setNote("Added to this job's resume. Edit the wording in the composer.");
      queryClient.invalidateQueries({ queryKey: ["application", applicationId] });
      queryClient.invalidateQueries({ queryKey: ["reading", applicationId] });
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  const spec = project.data;
  const missing =
    project.isError &&
    project.error instanceof ApiError &&
    project.error.status === 404;

  return (
    <div className="card">
      <div className="flex">
        <h2 className="grow">
          <Lightbulb size={15} /> Project to build
        </h2>
        {spec && (
          <select
            className="mini"
            value={spec.status}
            onChange={(e) => setStatus.mutate(e.target.value as BuildStatus)}
          >
            {(["idea", "building", "built"] as BuildStatus[]).map((s) => (
              <option key={s} value={s}>
                {STATUS_LABEL[s]}
              </option>
            ))}
          </select>
        )}
      </div>

      {error && <div className="banner bad">{error}</div>}
      {note && <div className="banner info">{note}</div>}

      {(!hasJd || !hasResume) && (
        <p className="sub">
          {!hasJd
            ? "Paste the job description and this can design something aimed at them."
            : "Compose a resume first — the design builds on what you already know."}
        </p>
      )}

      {hasJd && hasResume && (missing || !spec) && !make.isPending && (
        <>
          <p className="sub">
            Designs a project in this company's own domain that exercises every
            technology the job asks for — or finds the sharper angle on one you
            have already built.
          </p>
          <button
            type="button"
            className="primary"
            onClick={() => make.mutate()}
          >
            Design one
          </button>
        </>
      )}

      {make.isPending && (
        <span className="working">designing something worth building</span>
      )}

      {spec && !make.isPending && (
        <>
          <div className="proj-head">
            <span className={`pill ${spec.mode === "reframe" ? "screen" : "applied"}`}>
              {spec.mode === "reframe" ? "reframe" : "new build"}
            </span>
            <strong>{spec.title}</strong>
          </div>
          {spec.based_on && (
            <p className="faint small">Building on: {spec.based_on}</p>
          )}
          <p className="stack small">{spec.stack}</p>

          <p>{spec.problem}</p>
          {spec.why_them && (
            <p className="muted small">
              <Target size={13} /> {spec.why_them}
            </p>
          )}

          {spec.covers.length > 0 && (
            <>
              <h3 className="mini-head">What it proves</h3>
              <ul className="covers">
                {spec.covers.map((c) => (
                  <li key={c.requirement}>
                    <span>{c.requirement}</span>
                    <ArrowRight size={12} />
                    <span className="muted">{c.where}</span>
                  </li>
                ))}
              </ul>
            </>
          )}

          {spec.architecture.length > 0 && (
            <>
              <h3 className="mini-head">How it is put together</h3>
              {spec.architecture.map((c) => (
                <div key={c.name} className="piece">
                  <strong>{c.name}</strong>
                  {c.tech && <span className="tag">{c.tech}</span>}
                  <div className="muted small">{c.what}</div>
                </div>
              ))}
            </>
          )}

          {spec.milestones.length > 0 && (
            <>
              <h3 className="mini-head">Order to build it in</h3>
              <ol className="milestones">
                {spec.milestones.map((m) => (
                  <li key={m.name}>
                    <strong>{m.name}</strong>
                    {m.effort && <span className="tag">{m.effort}</span>}
                    <div className="muted small">{m.outcome}</div>
                  </li>
                ))}
              </ol>
            </>
          )}

          {spec.done_means && (
            <p className="done-means">
              <Check size={14} /> Done means: {spec.done_means}
            </p>
          )}
          {spec.risks && (
            <p className="faint small">Most likely to bite: {spec.risks}</p>
          )}

          {spec.bullets.length > 0 && (
            <>
              <h3 className="mini-head">Resume entry, once it exists</h3>
              <ul className="bullets">
                {spec.bullets.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </>
          )}

          <div className="actions" style={{ marginTop: 12, flexWrap: "wrap" }}>
            <button
              type="button"
              className={spec.status === "built" ? "primary" : ""}
              disabled={spec.status !== "built" || adopt.isPending}
              title={
                spec.status === "built"
                  ? "Add it to this job's resume"
                  : "Mark it built first — an interviewer will ask about it"
              }
              onClick={() => adopt.mutate()}
            >
              Add to this resume
            </button>
            <button
              type="button"
              className="ghost small"
              disabled={make.isPending}
              onClick={() => make.mutate()}
            >
              Design a different one
            </button>
          </div>
          {spec.status !== "built" && (
            <p className="faint small" style={{ marginBottom: 0 }}>
              Placeholders like &lt;throughput&gt; get real numbers once you have
              measured them.
            </p>
          )}
        </>
      )}
    </div>
  );
}
