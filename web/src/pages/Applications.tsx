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

type Draft = {
  company: string;
  role: string;
  job_url: string;
  job_description: string;
  notes: string;
};

const BLANK: Draft = {
  company: "",
  role: "",
  job_url: "",
  job_description: "",
  notes: "",
};

/** Create a new application, or edit an existing one. Same fields either way. */
function ApplicationForm({
  existing,
  onDone,
}: {
  existing?: ApplicationRow;
  onDone: () => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<Draft>(
    existing
      ? {
          company: existing.company,
          role: existing.role,
          job_url: existing.job_url,
          job_description: existing.job_description,
          notes: existing.notes,
        }
      : BLANK,
  );
  const [error, setError] = useState("");

  const submit = useMutation({
    mutationFn: () =>
      existing
        ? api.patchApplication(existing.id, form)
        : api.createApplication(form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      if (existing) {
        // The composer reads the JD off the application record.
        queryClient.invalidateQueries({ queryKey: ["application", existing.id] });
      }
      onDone();
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  const set = <K extends keyof Draft>(key: K, v: Draft[K]) =>
    setForm({ ...form, [key]: v });
  const ready = form.company.trim() && form.role.trim();

  return (
    <div className="card">
      <h2 style={{ marginBottom: 10 }}>
        {existing ? `Edit ${existing.company} — ${existing.role}` : "Track a new application"}
      </h2>
      {error && <div className="banner bad">{error}</div>}
      <div className="row">
        <label className="field">
          <span>Company *</span>
          <input value={form.company} onChange={(e) => set("company", e.target.value)} />
        </label>
        <label className="field">
          <span>Role *</span>
          <input value={form.role} onChange={(e) => set("role", e.target.value)} />
        </label>
      </div>
      <label className="field">
        <span>Job posting URL</span>
        <input
          value={form.job_url}
          placeholder="https://…"
          onChange={(e) => set("job_url", e.target.value)}
        />
      </label>
      <label className="field">
        <span>
          Job description — paste it here; it shows beside the composer while you
          tailor
        </span>
        <textarea
          value={form.job_description}
          style={{ minHeight: 150 }}
          onChange={(e) => set("job_description", e.target.value)}
        />
      </label>
      <label className="field">
        <span>Notes</span>
        <textarea
          value={form.notes}
          onChange={(e) => set("notes", e.target.value)}
        />
      </label>
      <div className="actions">
        <button
          type="button"
          className="primary"
          disabled={!ready || submit.isPending}
          onClick={() => submit.mutate()}
        >
          {submit.isPending
            ? "Saving…"
            : existing
              ? "Save changes"
              : "Add application"}
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
  const [editingId, setEditingId] = useState<number | null>(null);

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

  const editing = apps.data?.find((a) => a.id === editingId);

  return (
    <div className="page">
      <div className="page-head">
        <h1>Applications</h1>
        <span className="sub">Each one gets its own tailored resume.</span>
        <span className="spacer" style={{ marginLeft: "auto" }} />
        {!adding && editingId === null && (
          <button type="button" className="primary" onClick={() => setAdding(true)}>
            New application
          </button>
        )}
      </div>

      {adding && <ApplicationForm onDone={() => setAdding(false)} />}
      {editing && (
        <ApplicationForm existing={editing} onDone={() => setEditingId(null)} />
      )}

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
                <th style={{ width: 66 }}>JD</th>
                <th style={{ width: 130 }}>Status</th>
                <th style={{ width: 240 }}>Resume</th>
                <th style={{ width: 110 }} />
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
                  <td
                    className="muted small"
                    title={
                      app.job_description
                        ? `${app.job_description.length} characters`
                        : "No job description saved — click Edit to paste one"
                    }
                  >
                    {app.job_description ? "saved" : "—"}
                  </td>
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
                    <div className="actions" style={{ justifyContent: "flex-end" }}>
                      <button
                        type="button"
                        className="ghost small"
                        onClick={() => {
                          setAdding(false);
                          setEditingId(app.id);
                        }}
                      >
                        Edit
                      </button>
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
                    </div>
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
