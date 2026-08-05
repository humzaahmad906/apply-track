import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  api,
  ApiError,
  APP_STATUSES,
  type ApplicationRow,
  type AppStatus,
} from "../api/client";
import InterviewPanel from "../components/InterviewPanel";
import ProjectPanel from "../components/ProjectPanel";
import ReadingPanel from "../components/ReadingPanel";
import StageTimeline from "../components/StageTimeline";
import { fromDateTimeInput, longDate, shortDate, toDateTimeInput } from "../format";

/** Pick a base resume to fork, once per job. */
function ResumeCard({ app }: { app: ApplicationRow }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const resumes = useQuery({
    queryKey: ["resumes"],
    queryFn: api.listResumes,
    enabled: app.variant_id === null,
  });

  const fork = useMutation({
    mutationFn: (baseResumeId: number) =>
      api.forkVariant(app.id, { base_resume_id: baseResumeId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["application", app.id] });
      navigate(`/jobs/${app.id}/resume`);
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  const exportPdf = useMutation({
    mutationFn: () => api.exportVariant(app.variant_id!),
    onSuccess: ({ blob, filename }) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      setNote(`Exported ${filename}`);
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (err) =>
      setError(
        err instanceof ApiError && err.status === 503
          ? `${err.message} You can still open the composer and print from the browser.`
          : err instanceof ApiError
            ? err.message
            : String(err),
      ),
  });

  return (
    <div className="card">
      <h2>Resume</h2>
      {error && <div className="banner bad">{error}</div>}
      {note && <div className="banner info">{note}</div>}

      {app.variant_id === null ? (
        <>
          <p className="sub">
            Fork a base resume, then switch off whatever this job does not need.
            The base is never touched.
          </p>
          {resumes.data?.length === 0 && (
            <p className="muted small">
              No base resume yet — add one under <Link to="/material">Material</Link>.
            </p>
          )}
          <div className="actions wrap">
            {resumes.data?.map((r) => (
              <button
                key={r.id}
                type="button"
                disabled={fork.isPending}
                onClick={() => fork.mutate(r.id)}
              >
                Fork “{r.name}”
              </button>
            ))}
          </div>
        </>
      ) : (
        <>
          <p className="sub">
            {app.status === "wishlist" && !note
              ? "Tailored and ready. Export it, send it, then move this to Applied."
              : "Tailored for this job."}
          </p>
          <div className="actions wrap">
            <button
              type="button"
              className="primary"
              onClick={() => navigate(`/jobs/${app.id}/resume`)}
            >
              Open composer
            </button>
            <button
              type="button"
              disabled={exportPdf.isPending}
              onClick={() => exportPdf.mutate()}
            >
              {exportPdf.isPending ? "Rendering…" : "Export PDF"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default function JobPage() {
  const { applicationId } = useParams();
  const appId = Number(applicationId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [jd, setJd] = useState("");
  const [notes, setNotes] = useState("");
  const [step, setStep] = useState("");
  const [stepAt, setStepAt] = useState("");
  const [error, setError] = useState("");

  const application = useQuery({
    queryKey: ["application", appId],
    queryFn: () => api.application(appId),
    enabled: Number.isFinite(appId),
  });

  const timeline = useQuery({
    queryKey: ["timeline", appId],
    queryFn: () => api.timeline(appId),
    enabled: Number.isFinite(appId),
  });

  // Seed the editable fields whenever the server view changes.
  useEffect(() => {
    const app = application.data;
    if (!app) return;
    setJd(app.job_description);
    setNotes(app.notes);
    setStep(app.next_action);
    setStepAt(toDateTimeInput(app.next_action_at));
  }, [application.data]);

  const patch = useMutation({
    mutationFn: (body: Partial<ApplicationRow>) => api.patchApplication(appId, body),
    onSuccess: () => {
      setError("");
      queryClient.invalidateQueries({ queryKey: ["application", appId] });
      queryClient.invalidateQueries({ queryKey: ["timeline", appId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["reading", appId] });
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  const remove = useMutation({
    mutationFn: () => api.deleteApplication(appId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      navigate("/");
    },
  });

  if (application.isLoading) {
    return (
      <div className="page">
        <div className="empty">Loading…</div>
      </div>
    );
  }

  if (application.isError || !application.data) {
    return (
      <div className="page">
        <div className="banner bad">That job is not here.</div>
        <Link to="/">Back to the dashboard</Link>
      </div>
    );
  }

  const app = application.data;
  const hasJd = Boolean(app.job_description.trim());
  const jdDirty = jd !== app.job_description;
  const notesDirty = notes !== app.notes;
  const stepDirty =
    step !== app.next_action || stepAt !== toDateTimeInput(app.next_action_at);

  return (
    <div className="page">
      <Link to="/" className="small">
        ← Dashboard
      </Link>

      <div className="job-head" style={{ marginTop: 10 }}>
        <div className="grow">
          <h1>
            {app.company} <span className="muted">— {app.role}</span>
          </h1>
          <div className="flex wrap" style={{ marginTop: 4 }}>
            <span className={`pill ${app.status}`}>{app.status}</span>
            {app.applied_at && (
              <span className="faint small">
                applied {shortDate(app.applied_at)}
              </span>
            )}
            {app.job_url && (
              <a
                href={app.job_url}
                target="_blank"
                rel="noreferrer"
                className="small"
              >
                posting ↗
              </a>
            )}
          </div>
        </div>
        <label className="field" style={{ width: 150, marginBottom: 0 }}>
          <span>Stage</span>
          <select
            value={app.status}
            onChange={(e) =>
              patch.mutate({ status: e.target.value as AppStatus })
            }
          >
            {APP_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="card tight">
        <StageTimeline events={timeline.data ?? []} current={app.status} />
      </div>

      {error && <div className="banner bad">{error}</div>}

      <div className="job-grid">
        <div>
          <div className="card">
            <h2>Next step</h2>
            <p className="sub">
              What happens next and when. This is what puts the job at the top
              of your dashboard on the right day.
            </p>
            <div className="row">
              <label className="field">
                <span>What</span>
                <input
                  value={step}
                  placeholder="Recruiter call with Dana"
                  onChange={(e) => setStep(e.target.value)}
                />
              </label>
              <label className="field" style={{ flex: "0 0 210px" }}>
                <span>When</span>
                <input
                  type="datetime-local"
                  value={stepAt}
                  onChange={(e) => setStepAt(e.target.value)}
                />
              </label>
            </div>
            <div className="actions">
              <button
                type="button"
                disabled={!stepDirty || patch.isPending}
                onClick={() =>
                  patch.mutate({
                    next_action: step,
                    next_action_at: fromDateTimeInput(stepAt),
                  })
                }
              >
                Save next step
              </button>
              {(app.next_action || app.next_action_at) && (
                <button
                  type="button"
                  className="ghost small"
                  onClick={() => {
                    setStep("");
                    setStepAt("");
                    patch.mutate({ next_action: "", next_action_at: null });
                  }}
                >
                  Clear
                </button>
              )}
              {app.snoozed_until && (
                <button
                  type="button"
                  className="ghost small"
                  onClick={() => patch.mutate({ snoozed_until: null })}
                >
                  Un-snooze
                </button>
              )}
            </div>
          </div>

          <div className="card">
            <div className="flex">
              <h2 className="grow">Job description</h2>
              <span className="faint small">
                {hasJd ? `${app.job_description.length} chars` : "none yet"}
              </span>
            </div>
            <p className="sub">
              Saving this starts the comparison against your resume on its own.
            </p>
            <textarea
              value={jd}
              placeholder="Paste the posting here."
              style={{ minHeight: 200 }}
              onChange={(e) => setJd(e.target.value)}
            />
            <div className="actions" style={{ marginTop: 8 }}>
              <button
                type="button"
                className={jdDirty ? "primary" : ""}
                disabled={!jdDirty || patch.isPending}
                onClick={() => patch.mutate({ job_description: jd })}
              >
                {patch.isPending ? "Saving…" : "Save"}
              </button>
              {jdDirty && (
                <button
                  type="button"
                  className="ghost small"
                  onClick={() => setJd(app.job_description)}
                >
                  Revert
                </button>
              )}
            </div>
          </div>

          <div className="card">
            <h2>Notes</h2>
            <textarea
              value={notes}
              placeholder="Who you spoke to, what they asked, what to remember."
              onChange={(e) => setNotes(e.target.value)}
            />
            <div className="actions" style={{ marginTop: 8 }}>
              <button
                type="button"
                disabled={!notesDirty || patch.isPending}
                onClick={() => patch.mutate({ notes })}
              >
                Save notes
              </button>
            </div>
          </div>
        </div>

        <div>
          <ResumeCard app={app} />

          <div className="card">
            <h2>Activity</h2>
            <ul className="log">
              {(timeline.data ?? [])
                .slice()
                .reverse()
                .map((event, i) => (
                  <li key={`${event.at}-${i}`}>
                    <span className={`pill ${event.status}`}>{event.status}</span>
                    <span className="when">{longDate(event.at)}</span>
                  </li>
                ))}
            </ul>
            {app.last_contact_at && (
              <p className="faint small" style={{ marginBottom: 0 }}>
                Last contact {shortDate(app.last_contact_at)}.
              </p>
            )}
          </div>

          <div className="card tight">
            <button
              type="button"
              className="ghost small danger"
              onClick={() => {
                if (
                  window.confirm(
                    `Delete ${app.company} — ${app.role}? Its tailored resume and history go too.`,
                  )
                ) {
                  remove.mutate();
                }
              }}
            >
              Delete this job
            </button>
          </div>
        </div>
      </div>

      {/* Full width, not the sidebar. A reading list, an architecture and a
          question bank all need the room; a 320px column made them unreadable
          and left the other half of the page empty. */}
      <ReadingPanel
        applicationId={appId}
        hasJd={hasJd}
        hasResume={app.variant_id !== null}
      />

      <ProjectPanel
        applicationId={appId}
        variantId={app.variant_id}
        hasJd={hasJd}
        hasResume={app.variant_id !== null}
      />

      <InterviewPanel
        applicationId={appId}
        hasJd={hasJd}
        hasResume={app.variant_id !== null}
      />
    </div>
  );
}
