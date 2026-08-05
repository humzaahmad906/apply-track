import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  api,
  ApiError,
  emptyItem,
  newId,
  SECTION_KINDS,
  type Item,
  type SectionKind,
} from "../api/client";

/** Upload a resume and let it parse itself into sections. */
function BaseResumes() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const resumes = useQuery({ queryKey: ["resumes"], queryFn: api.listResumes });

  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.job(jobId!),
    enabled: jobId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "running" ? 1200 : false;
    },
  });

  // A finished parse goes straight to the review screen.
  useEffect(() => {
    if (job.data?.status === "done") {
      setJobId(null);
      navigate(`/material/review/${job.data.id}`);
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
    <>
      <div className="section-head" style={{ marginTop: 0 }}>
        <h2>Base resumes</h2>
        <span className="sub">Parsed once, then forked for every job.</span>
      </div>

      {error && <div className="banner bad">{error}</div>}

      <div className="card">
        <div className="actions">
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            disabled={busy}
            className="grow"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) upload.mutate(file);
            }}
          />
          {busy && (
            <span className="working nowrap">
              {job.data?.status === "running" ? "reading it" : "uploading"}
            </span>
          )}
        </div>
        <p className="sub" style={{ margin: "8px 0 0" }}>
          PDF, DOCX, TXT or MD. The file is read locally and its sections are
          extracted for you to check before anything is saved.
        </p>
      </div>

      {resumes.data?.length === 0 && (
        <div className="empty">No base resume yet. Upload one above.</div>
      )}

      {resumes.data && resumes.data.length > 0 && (
        <div className="card tight">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>From</th>
                <th style={{ width: 70 }}>Sections</th>
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
                        onClick={() => navigate(`/material/${r.id}/edit`)}
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
                              `Delete "${r.name}"? Resumes already composed from it are kept.`,
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
    </>
  );
}

/** Author a reusable item once — a capstone project, a side project, a role. */
function NewLibraryItem({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const [kind, setKind] = useState<SectionKind>("projects");
  const [form, setForm] = useState({
    title: "",
    subtitle: "",
    url: "",
    description: "",
    bulletText: "",
  });
  const [error, setError] = useState("");

  const create = useMutation({
    mutationFn: () => {
      const item: Item = {
        ...emptyItem(),
        title: form.title.trim(),
        subtitle: form.subtitle.trim(),
        url: form.url.trim(),
        description: form.description.trim(),
        bullets: form.bulletText
          .split("\n")
          .map((line) => line.replace(/^\s*[-*•]\s*/, "").trim())
          .filter(Boolean)
          .map((text) => ({ id: newId(), text, include: true })),
      };
      return api.addLibraryItem({
        label: item.title || "Untitled",
        section_kind: kind,
        data: item,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["library"] });
      onDone();
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  const set = (k: keyof typeof form, v: string) => setForm({ ...form, [k]: v });

  return (
    <div className="card">
      <h2>New reusable item</h2>
      {error && <div className="banner bad">{error}</div>}
      <div className="row" style={{ marginTop: 10 }}>
        <label className="field">
          <span>Title</span>
          <input
            value={form.title}
            placeholder="On-device VLM capstone"
            onChange={(e) => set("title", e.target.value)}
          />
        </label>
        <label className="field" style={{ flex: "0 0 170px" }}>
          <span>Goes in section</span>
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value as SectionKind)}
          >
            {SECTION_KINDS.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="row">
        <label className="field">
          <span>Subtitle (tech stack, or employer)</span>
          <input
            value={form.subtitle}
            placeholder="Swift, MLX, CoreML"
            onChange={(e) => set("subtitle", e.target.value)}
          />
        </label>
        <label className="field">
          <span>Link</span>
          <input
            value={form.url}
            placeholder="github.com/you/project"
            onChange={(e) => set("url", e.target.value)}
          />
        </label>
      </div>
      <label className="field">
        <span>Description (prose, optional)</span>
        <textarea
          value={form.description}
          onChange={(e) => set("description", e.target.value)}
        />
      </label>
      <label className="field">
        <span>Bullets — one per line</span>
        <textarea
          value={form.bulletText}
          placeholder={
            "Quantised Qwen3.5-VL to 4-bit; 30 tok/s on an M3.\nWrote the KV-cache path used by the iOS demo."
          }
          style={{ minHeight: 90 }}
          onChange={(e) => set("bulletText", e.target.value)}
        />
      </label>
      <div className="actions">
        <button
          type="button"
          className="primary"
          disabled={!form.title.trim() || create.isPending}
          onClick={() => create.mutate()}
        >
          {create.isPending ? "Saving…" : "Save to library"}
        </button>
        <button type="button" onClick={onDone}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function ReusableItems() {
  const queryClient = useQueryClient();
  const [adding, setAdding] = useState(false);

  const library = useQuery({ queryKey: ["library"], queryFn: api.listLibrary });

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteLibraryItem(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["library"] }),
  });

  return (
    <>
      <div className="section-head">
        <h2>Reusable items</h2>
        <span className="sub">
          Capstones and side projects you drop into whichever job wants them.
        </span>
        <span className="push" />
        {!adding && (
          <button type="button" onClick={() => setAdding(true)}>
            New item
          </button>
        )}
      </div>

      {adding && <NewLibraryItem onDone={() => setAdding(false)} />}

      {library.data?.length === 0 && !adding && (
        <div className="empty">
          Nothing saved yet. Add one here, or click ★ on any item inside a
          composer.
        </div>
      )}

      {library.data?.map((row) => (
        <div className="card tight" key={row.id}>
          <div className="actions">
            <div className="grow">
              <strong>{row.label}</strong>
              <div className="muted small">
                {row.section_kind}
                {row.data.subtitle ? ` · ${row.data.subtitle}` : ""}
                {row.data.bullets?.length
                  ? ` · ${row.data.bullets.length} bullets`
                  : ""}
              </div>
            </div>
            {row.data.url && (
              <a href={row.data.url} target="_blank" rel="noreferrer">
                <button type="button" className="ghost small">
                  Link
                </button>
              </a>
            )}
            <button
              type="button"
              className="icon danger"
              title="Remove from the library"
              onClick={() => {
                if (window.confirm(`Remove "${row.label}"?`)) remove.mutate(row.id);
              }}
            >
              ✕
            </button>
          </div>
        </div>
      ))}
    </>
  );
}

export default function Material() {
  return (
    <div className="page">
      <div className="page-head">
        <h1>Material</h1>
        <span className="sub">Everything your tailored resumes are built from.</span>
      </div>
      <BaseResumes />
      <ReusableItems />
    </div>
  );
}
