import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  api,
  ApiError,
  APP_STATUSES,
  type ApplicationRow,
  type AppStatus,
} from "../api/client";

function NewApplication({ onDone }: { onDone: () => void }) {
  const [form, setForm] = useState({
    company: "",
    role: "",
    job_url: "",
    job_description: "",
    notes: "",
  });
  const [error, setError] = useState("");

  const create = useMutation({
    mutationFn: () => api.createApplication(form),
    onSuccess: onDone,
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  const ready = form.company.trim() && form.role.trim();

  return (
    <div className="card">
      <h2 style={{ marginBottom: 10 }}>Track a new application</h2>
      {error && <div className="banner bad">{error}</div>}
      <div className="row">
        <label className="field">
          <span>Company *</span>
          <input
            value={form.company}
            onChange={(e) => setForm({ ...form, company: e.target.value })}
          />
        </label>
        <label className="field">
          <span>Role *</span>
          <input
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
          />
        </label>
      </div>
      <label className="field">
        <span>Job posting URL</span>
        <input
          value={form.job_url}
          placeholder="https://…"
          onChange={(e) => setForm({ ...form, job_url: e.target.value })}
        />
      </label>
      <label className="field">
        <span>Job description (paste it — handy to have beside the composer)</span>
        <textarea
          value={form.job_description}
          onChange={(e) => setForm({ ...form, job_description: e.target.value })}
        />
      </label>
      <label className="field">
        <span>Notes</span>
        <textarea
          value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })}
        />
      </label>
      <div className="actions">
        <button
          type="button"
          className="primary"
          disabled={!ready || create.isPending}
          onClick={() => create.mutate()}
        >
          {create.isPending ? "Adding…" : "Add application"}
        </button>
        <button type="button" onClick={onDone}>
          Cancel
        </button>
      </div>
    </div>
  );
}

/** Pick a base resume to fork, then jump into the composer. */
function ComposeButton({ app }: { app: ApplicationRow }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [picking, setPicking] = useState(false);
  const [error, setError] = useState("");

  const resumes = useQuery({
    queryKey: ["resumes"],
    queryFn: api.listResumes,
    enabled: picking,
  });

  const fork = useMutation({
    mutationFn: (baseResumeId: number) =>
      api.forkVariant(app.id, { base_resume_id: baseResumeId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      navigate(`/applications/${app.id}/compose`);
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  if (app.variant_id !== null) {
    return (
      <button
        type="button"
        className="ghost small"
        onClick={() => navigate(`/applications/${app.id}/compose`)}
      >
        Open composer
      </button>
    );
  }

  if (!picking) {
    return (
      <button type="button" className="ghost small" onClick={() => setPicking(true)}>
        Compose resume
      </button>
    );
  }

  return (
    <div style={{ textAlign: "left" }}>
      {error && <div className="banner bad">{error}</div>}
      {resumes.isLoading && <span className="muted small">Loading resumes…</span>}
      {resumes.data && resumes.data.length === 0 && (
        <span className="muted small">
          No base resume yet — add one under “Base resumes” first.
        </span>
      )}
      {resumes.data && resumes.data.length > 0 && (
        <div className="actions" style={{ flexWrap: "wrap" }}>
          <span className="muted small">Fork from:</span>
          {resumes.data.map((r) => (
            <button
              type="button"
              key={r.id}
              className="ghost small"
              disabled={fork.isPending}
              onClick={() => fork.mutate(r.id)}
            >
              {r.name}
            </button>
          ))}
        </div>
      )}
      <button
        type="button"
        className="icon"
        style={{ marginTop: 4 }}
        onClick={() => setPicking(false)}
      >
        cancel
      </button>
    </div>
  );
}

export default function Applications() {
  const queryClient = useQueryClient();
  const [adding, setAdding] = useState(false);

  const apps = useQuery({
    queryKey: ["applications"],
    queryFn: api.listApplications,
  });

  const patch = useMutation({
    mutationFn: ({ id, status }: { id: number; status: AppStatus }) =>
      api.patchApplication(id, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteApplication(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  return (
    <div className="page">
      <div className="page-head">
        <h1>Applications</h1>
        <span className="sub">Each one gets its own tailored resume.</span>
        <span className="spacer" style={{ marginLeft: "auto" }} />
        {!adding && (
          <button type="button" className="primary" onClick={() => setAdding(true)}>
            New application
          </button>
        )}
      </div>

      {adding && <NewApplication onDone={() => setAdding(false)} />}

      {apps.isLoading && <div className="empty">Loading…</div>}

      {apps.data && apps.data.length === 0 && !adding && (
        <div className="empty">
          Nothing tracked yet. Add an application, then compose a resume for it.
        </div>
      )}

      {apps.data && apps.data.length > 0 && (
        <div className="card tight">
          <table>
            <thead>
              <tr>
                <th>Company</th>
                <th>Role</th>
                <th style={{ width: 130 }}>Status</th>
                <th style={{ width: 240 }}>Resume</th>
                <th style={{ width: 70 }} />
              </tr>
            </thead>
            <tbody>
              {apps.data.map((app) => (
                <tr key={app.id}>
                  <td>
                    {app.job_url ? (
                      <a href={app.job_url} target="_blank" rel="noreferrer">
                        {app.company}
                      </a>
                    ) : (
                      app.company
                    )}
                  </td>
                  <td>{app.role}</td>
                  <td>
                    <select
                      value={app.status}
                      className={`pill ${app.status}`}
                      onChange={(e) =>
                        patch.mutate({
                          id: app.id,
                          status: e.target.value as AppStatus,
                        })
                      }
                    >
                      {APP_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <ComposeButton app={app} />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="icon danger"
                      title="Delete application"
                      onClick={() => {
                        if (
                          window.confirm(
                            `Delete ${app.company} — ${app.role}? Its tailored resume goes too.`,
                          )
                        ) {
                          remove.mutate(app.id);
                        }
                      }}
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
