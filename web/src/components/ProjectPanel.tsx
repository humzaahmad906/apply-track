import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  api,
  ApiError,
  type BuildStatus,
  type ProjectSpec,
} from "../api/client";
import { ArrowRight, Check, Lightbulb, Target } from "../icons";
import PortfolioCard from "./PortfolioCard";

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
  variantId,
  hasJd,
  hasResume,
}: {
  applicationId: number;
  variantId: number | null;
  hasJd: boolean;
  hasResume: boolean;
}) {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [target, setTarget] = useState<string>("");
  const [picked, setPicked] = useState<Set<string> | null>(null);
  const [addSkills, setAddSkills] = useState(true);

  // The entries this could be folded into, newest role first.
  const variant = useQuery({
    queryKey: ["variant", variantId],
    queryFn: () => api.variant(variantId!),
    enabled: variantId !== null,
  });

  const destinations = (variant.data?.data.sections ?? [])
    .filter((s) => s.kind === "experience" || s.kind === "projects")
    .flatMap((s) =>
      s.items.map((i) => ({
        id: i.id,
        label: [i.title, i.subtitle].filter(Boolean).join(" — ") || "(untitled)",
        kind: s.kind,
      })),
    );

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

  const landed = (result: {
    landed_in: string;
    bullets_added: number;
    skills_added: string[];
  }) => {
    setError("");
    const skills = result.skills_added.length
      ? ` ${result.skills_added.length} new skill tag${
          result.skills_added.length === 1 ? "" : "s"
        }: ${result.skills_added.join(", ")}.`
      : "";
    setNote(
      `${result.bullets_added} line${result.bullets_added === 1 ? "" : "s"} added ` +
        `under ${result.landed_in}.${skills} Tune the wording in the composer.`,
    );
    queryClient.invalidateQueries({ queryKey: ["project", applicationId] });
    queryClient.invalidateQueries({ queryKey: ["application", applicationId] });
    queryClient.invalidateQueries({ queryKey: ["reading", applicationId] });
    // The composer holds the variant in cache and autosaves the whole tree.
    // Without this it would reopen on the pre-adopt copy and quietly write
    // the project back out again.
    queryClient.invalidateQueries({ queryKey: ["variant"] });
  };

  const failed = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : String(err));

  const body = () => ({
    item_id: target || null,
    bullets: picked === null ? undefined : [...picked],
    add_skills: addSkills,
  });

  const adopt = useMutation({
    mutationFn: () => api.adoptProject(applicationId, body()),
    onSuccess: landed,
    onError: failed,
  });

  /** One click for the common case: it exists now, put it on the resume. */
  const buildAndAdopt = useMutation({
    mutationFn: async () => {
      await api.setProjectStatus(applicationId, "built");
      return api.adoptProject(applicationId, body());
    },
    onSuccess: landed,
    onError: failed,
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

          {/* Where it lands. Folding it into a role you already have reads as
              work you did there; its own Projects entry reads as your own
              time. Pick whichever is true. */}
          <h3 className="mini-head">Put it on the resume</h3>
          <div className="adopt">
            <label className="field">
              <span>Add it under</span>
              <select value={target} onChange={(e) => setTarget(e.target.value)}>
                <option value="">A new entry under Projects</option>
                {destinations.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.kind === "experience" ? "Role: " : "Project: "}
                    {d.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="field">
              <span>Lines to add</span>
              {spec.bullets.map((b) => {
                const on = picked === null || picked.has(b);
                return (
                  <label key={b} className="pick">
                    <input
                      type="checkbox"
                      checked={on}
                      onChange={() =>
                        setPicked((prev) => {
                          const next = new Set(prev ?? spec.bullets);
                          if (next.has(b)) next.delete(b);
                          else next.add(b);
                          return next;
                        })
                      }
                    />
                    <span>{b}</span>
                  </label>
                );
              })}
            </div>

            <label className="pick">
              <input
                type="checkbox"
                checked={addSkills}
                onChange={(e) => setAddSkills(e.target.checked)}
              />
              <span>
                Also add its stack to your Skills tags
                {spec.stack ? ` (${spec.stack})` : ""}
              </span>
            </label>
          </div>

          <PortfolioCard
            applicationId={applicationId}
            built={spec.status === "built"}
          />

          {spec.status === "built" ? (
            <div className="actions" style={{ marginTop: 12, flexWrap: "wrap" }}>
              <button
                type="button"
                className="primary"
                disabled={adopt.isPending}
                onClick={() => adopt.mutate()}
              >
                {adopt.isPending ? "Adding…" : "Add to this resume"}
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
          ) : (
            /* The gate needs to say what it wants. A greyed-out button with the
               reason hidden in a tooltip just reads as broken. */
            <div className="gate">
              <strong>Built it yet?</strong>
              <p className="muted small">
                It goes on the resume once it exists. Interview prep drills into
                everything on there, and the bullets still have placeholders
                like &lt;throughput&gt; waiting on real numbers.
              </p>
              <div className="actions wrap">
                <button
                  type="button"
                  className="primary"
                  disabled={buildAndAdopt.isPending}
                  onClick={() => buildAndAdopt.mutate()}
                >
                  {buildAndAdopt.isPending
                    ? "Adding…"
                    : "I have built it — add it"}
                </button>
                {spec.status === "idea" && (
                  <button
                    type="button"
                    disabled={setStatus.isPending}
                    onClick={() => setStatus.mutate("building")}
                  >
                    Started on it
                  </button>
                )}
                <button
                  type="button"
                  className="ghost small"
                  disabled={make.isPending}
                  onClick={() => make.mutate()}
                >
                  Design a different one
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
