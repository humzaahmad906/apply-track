import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, ApiError } from "../api/client";

/**
 * The machinery, all in one place and out of the way.
 *
 * Nothing here needs attention on a normal day. It exists so that when
 * something *is* broken there is one page that says so plainly.
 */
export default function Settings() {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");

  const health = useQuery({ queryKey: ["health"], queryFn: api.health });
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

  const h = health.data;
  const courses = Object.entries(index.data?.courses ?? {});

  return (
    <div className="page">
      <div className="page-head">
        <h1>Settings</h1>
        <span className="sub">
          What this machine can currently do. Nothing here needs you day to day.
        </span>
      </div>

      <div className="card">
        <h2>Resume parsing</h2>
        {h && !h.claude_cli ? (
          <div className="banner bad" style={{ marginTop: 10 }}>
            {h.claude_cli_error}
          </div>
        ) : (
          <p className="sub">
            Claude Code CLI found at <code>{h?.claude_cli}</code>, using{" "}
            <strong>{h?.parse_model}</strong>.
          </p>
        )}
      </div>

      <div className="card">
        <h2>PDF export</h2>
        {h && !h.pdf_export ? (
          <>
            <div className="banner warn" style={{ marginTop: 10 }}>
              {h.pdf_export_error}
            </div>
            <p className="sub">
              Until then, open a resume preview in a new tab and print to PDF
              from the browser.
            </p>
          </>
        ) : (
          <p className="sub">
            Chromium is installed, so exports look the same on any machine.
          </p>
        )}
      </div>

      <div className="card">
        <h2>Job prep</h2>
        <p className="sub">
          {h?.auto_analyse
            ? "Comparisons run on their own about half a minute after you stop editing."
            : "Automatic comparison is switched off (APPLY_TRACK_AUTO_ANALYSE=0)."}
        </p>
        {error && <div className="banner bad">{error}</div>}
        {index.data && !index.data.indexed ? (
          <div className="banner warn">
            The lesson catalogue is empty, so prep cannot recommend anything.
            It refreshes itself on startup — or force it here.
          </div>
        ) : (
          <p className="small">
            <strong>{index.data?.lesson_count ?? 0}</strong> lessons across{" "}
            <strong>{courses.length}</strong> courses.
          </p>
        )}
        <div className="actions">
          <button
            type="button"
            disabled={refresh.isPending}
            onClick={() => refresh.mutate()}
          >
            {refresh.isPending ? "Fetching…" : "Refresh the catalogue"}
          </button>
        </div>
        {courses.length > 0 && (
          <details style={{ marginTop: 10 }}>
            <summary className="muted small" style={{ cursor: "pointer" }}>
              Show courses
            </summary>
            <div className="small muted" style={{ marginTop: 6, columns: 2 }}>
              {courses.map(([name, count]) => (
                <div key={name}>
                  {name} <span className="faint">({count})</span>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>

      <div className="card">
        <h2>Data</h2>
        <p className="sub">
          Everything lives in <code>{h?.data_dir}</code> — the database, uploads
          and exported PDFs. Back it up by copying that folder.
        </p>
      </div>
    </div>
  );
}
