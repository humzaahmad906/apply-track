import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api, ApiError, type ResumeJSON } from "../api/client";
import { BasicsFields, SectionList } from "../components/ResumeFields";

/**
 * Review a freshly parsed resume before saving it, or edit a saved one.
 * Extraction is the fuzzy step, so nothing is persisted until it is checked.
 */
export default function ResumeEditor({ mode }: { mode: "review" | "edit" }) {
  const { jobId, resumeId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [name, setName] = useState("");
  const [data, setData] = useState<ResumeJSON | null>(null);
  const [error, setError] = useState("");

  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.job(jobId!),
    enabled: mode === "review" && !!jobId,
  });

  const saved = useQuery({
    queryKey: ["resume", resumeId],
    queryFn: () => api.resume(Number(resumeId)),
    enabled: mode === "edit" && !!resumeId,
  });

  // Seed local state once the source loads.
  useEffect(() => {
    if (mode === "review" && job.data?.result && data === null) {
      setData(job.data.result);
      setName(
        job.data.result.basics.name
          ? `${job.data.result.basics.name} — base`
          : (job.data.filename ?? "Base resume"),
      );
    }
  }, [mode, job.data, data]);

  useEffect(() => {
    if (mode === "edit" && saved.data && data === null) {
      setData(saved.data.data);
      setName(saved.data.name);
    }
  }, [mode, saved.data, data]);

  const persist = useMutation({
    mutationFn: async () => {
      if (!data) throw new Error("Nothing to save.");
      if (mode === "edit") {
        return api.updateResume(Number(resumeId), { name, data });
      }
      return api.saveResume({
        name,
        source_filename: job.data?.filename ?? "",
        data,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
      navigate("/material");
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  const loading =
    (mode === "review" && job.isLoading) || (mode === "edit" && saved.isLoading);

  if (loading) {
    return (
      <div className="page">
        <div className="empty">Loading…</div>
      </div>
    );
  }

  if (mode === "review" && job.data && job.data.status !== "done") {
    return (
      <div className="page">
        <div className="banner bad">
          {job.data.error || `This parse job is ${job.data.status}.`}
        </div>
        <button type="button" onClick={() => navigate("/material")}>
          Back to resumes
        </button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="page">
        <div className="banner bad">
          Could not load this resume. The parse job may have expired — upload the
          file again.
        </div>
        <button type="button" onClick={() => navigate("/material")}>
          Back to resumes
        </button>
      </div>
    );
  }

  const itemCount = data.sections.reduce((n, s) => n + s.items.length, 0);

  return (
    <div className="page">
      <div className="page-head">
        <h1>{mode === "review" ? "Review extracted sections" : "Edit base resume"}</h1>
        <span className="sub">
          {data.sections.length} sections · {itemCount} items
        </span>
      </div>

      {mode === "review" && (
        <div className="banner info">
          Extraction copies text verbatim but can still mis-split a section. Fix
          anything wrong here — this becomes the master record every tailored
          resume is forked from.
        </div>
      )}
      {error && <div className="banner bad">{error}</div>}

      <div className="card">
        <label className="field" style={{ marginBottom: 0 }}>
          <span>Resume name (for your reference only, not printed)</span>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
      </div>

      <BasicsFields
        value={data.basics}
        onChange={(basics) => setData({ ...data, basics })}
      />

      <h2 style={{ margin: "18px 0 10px" }}>Sections</h2>
      <SectionList value={data} onChange={setData} />

      <div
        className="actions"
        style={{ marginTop: 22, position: "sticky", bottom: 0, paddingBottom: 8 }}
      >
        <button
          type="button"
          className="primary"
          disabled={persist.isPending}
          onClick={() => persist.mutate()}
        >
          {persist.isPending
            ? "Saving…"
            : mode === "review"
              ? "Save base resume"
              : "Save changes"}
        </button>
        <button type="button" onClick={() => navigate("/material")}>
          Cancel
        </button>
      </div>
    </div>
  );
}
