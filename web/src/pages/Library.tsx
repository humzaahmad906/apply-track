import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  api,
  ApiError,
  emptyItem,
  newId,
  SECTION_KINDS,
  type Item,
  type SectionKind,
} from "../api/client";

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
      <h2 style={{ marginBottom: 10 }}>New reusable item</h2>
      {error && <div className="banner bad">{error}</div>}
      <div className="row">
        <label className="field">
          <span>Title (project or role name)</span>
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
          placeholder={"Quantised Qwen3.5-VL to 4-bit; 30 tok/s on an M3.\nWrote the KV-cache path used by the iOS demo."}
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

/** Status of the lesson index that powers recommended reading. */
function CourseIndexCard() {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");

  const index = useQuery({ queryKey: ["courses"], queryFn: api.courseIndex });
  const refresh = useMutation({
    mutationFn: () => api.refreshCourses(),
    onSuccess: (data) => {
      setError("");
      queryClient.setQueryData(["courses"], data);
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  const data = index.data;
  const courseNames = Object.entries(data?.courses ?? {});

  return (
    <div className="card">
      <h2 style={{ marginBottom: 6 }}>Course index</h2>
      <p className="sub" style={{ marginTop: 0 }}>
        Lessons from your applied-ml-academy repo, used to recommend reading for
        the gaps between a job description and your resume.
      </p>
      {error && <div className="banner bad">{error}</div>}
      {data && !data.indexed && (
        <div className="banner warn">
          Not indexed yet. Refresh to pull the lesson list from GitHub.
        </div>
      )}
      {data?.indexed && (
        <p className="small" style={{ margin: "0 0 8px" }}>
          <strong>{data.lesson_count}</strong> lessons across{" "}
          <strong>{courseNames.length}</strong> courses.
        </p>
      )}
      <div className="actions">
        <button
          type="button"
          disabled={refresh.isPending}
          onClick={() => refresh.mutate()}
        >
          {refresh.isPending ? "Fetching…" : "Refresh from GitHub"}
        </button>
      </div>
      {courseNames.length > 0 && (
        <details style={{ marginTop: 10 }}>
          <summary className="muted small" style={{ cursor: "pointer" }}>
            Show courses
          </summary>
          <div className="small muted" style={{ marginTop: 6, columns: 2 }}>
            {courseNames.map(([name, count]) => (
              <div key={name}>
                {name} <span style={{ opacity: 0.6 }}>({count})</span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

export default function Library() {
  const queryClient = useQueryClient();
  const [adding, setAdding] = useState(false);

  const library = useQuery({ queryKey: ["library"], queryFn: api.listLibrary });

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteLibraryItem(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["library"] }),
  });

  return (
    <div className="page">
      <div className="page-head">
        <h1>Library</h1>
        <span className="sub">
          Capstone projects and other entries you reuse across applications.
        </span>
        <span className="spacer" style={{ marginLeft: "auto" }} />
        {!adding && (
          <button type="button" className="primary" onClick={() => setAdding(true)}>
            New item
          </button>
        )}
      </div>

      {adding && <NewLibraryItem onDone={() => setAdding(false)} />}

      {library.isLoading && <div className="empty">Loading…</div>}

      {library.data?.length === 0 && !adding && (
        <div className="empty">
          Nothing saved yet. Add a capstone project here, or click ★ on any item
          inside a composer to save it for reuse.
        </div>
      )}

      {library.data?.map((row) => (
        <div className="card tight" key={row.id}>
          <div className="actions">
            <div style={{ flex: 1, minWidth: 0 }}>
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
              title="Remove from library"
              onClick={() => {
                if (window.confirm(`Remove "${row.label}" from the library?`)) {
                  remove.mutate(row.id);
                }
              }}
            >
              ✕
            </button>
          </div>
        </div>
      ))}

      <div style={{ marginTop: 26 }}>
        <CourseIndexCard />
      </div>
    </div>
  );
}
