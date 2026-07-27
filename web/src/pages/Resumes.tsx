import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, ApiError } from "../api/client";

/** Flow one: upload a resume, watch it get parsed, then review it. */
export default function Resumes() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);

  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const resumes = useQuery({ queryKey: ["resumes"], queryFn: api.listResumes });
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });

  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.job(jobId!),
    enabled: jobId !== null,
    // Poll while the CLI works; a parse takes a few seconds.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "running" ? 1200 : false;
    },
  });

  // Hand a finished parse straight to the review screen.
  useEffect(() => {
    if (job.data?.status === "done") {
      setJobId(null);
      navigate(`/resumes/review/${job.data.id}`);
    } else if (job.data?.status === "error") {
      setError(job.data.error || "Parsing failed.");
      setJobId(null);
    }
  }, [job.data, navigate]);

  const upload = useMutation({
    mutationFn: (file: File) => api.uploadResume(file),
    onSuccess: (res) => {
      setError("");
      setJobId(res.job_id);
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteResume(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["resumes"] }),
  });

  const busy = upload.isPending || jobId !== null;

  return (
    <div className="page">
      <div className="page-head">
        <h1>Base resumes</h1>
        <span className="sub">
          Parsed once into JSON sections, then reused for every application.
        </span>
      </div>

      {health.data && !health.data.claude_cli && (
        <div className="banner bad">{health.data.claude_cli_error}</div>
      )}
      {error && <div className="banner bad">{error}</div>}

      <div className="card">
        <h2>Add a resume</h2>
        <p className="sub" style={{ margin: "6px 0 12px" }}>
          PDF, DOCX, TXT or MD. The file is read locally and its text is sent to
          the Claude CLI to extract sections — you review the result before
          anything is saved.
        </p>
        <div className="actions">
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            disabled={busy}
            style={{ flex: 1 }}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) upload.mutate(file);
            }}
          />
          {busy && (
            <span className="muted small" style={{ whiteSpace: "nowrap" }}>
              {job.data?.status === "running" ? "Extracting sections…" : "Uploading…"}
            </span>
          )}
        </div>
        {busy && (
          <p className="muted small" style={{ marginBottom: 0 }}>
            Using {health.data?.parse_model ?? "the configured model"}. Usually a
            few seconds.
          </p>
        )}
      </div>

      {resumes.isLoading && <div className="empty">Loading…</div>}

      {resumes.data && resumes.data.length === 0 && (
        <div className="empty">No base resumes yet. Upload one above.</div>
      )}

      {resumes.data && resumes.data.length > 0 && (
        <div className="card tight">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Source file</th>
                <th>Sections</th>
                <th style={{ width: 210 }} />
              </tr>
            </thead>
            <tbody>
              {resumes.data.map((r) => (
                <tr key={r.id}>
                  <td>{r.name}</td>
                  <td className="muted small">{r.source_filename || "—"}</td>
                  <td>{r.section_count}</td>
                  <td>
                    <div className="actions" style={{ justifyContent: "flex-end" }}>
                      <a
                        href={`/api/resumes/${r.id}/preview`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <button type="button" className="ghost small">
                          Preview
                        </button>
                      </a>
                      <button
                        type="button"
                        className="ghost small"
                        onClick={() => navigate(`/resumes/${r.id}/edit`)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="ghost small danger"
                        disabled={remove.isPending}
                        onClick={() => {
                          if (
                            window.confirm(
                              `Delete "${r.name}"? Variants already composed from it are kept.`,
                            )
                          ) {
                            remove.mutate(r.id);
                          }
                        }}
                      >
                        Delete
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
