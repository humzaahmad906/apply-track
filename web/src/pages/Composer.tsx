import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  api,
  ApiError,
  type Item,
  type ResumeJSON,
  type SectionKind,
} from "../api/client";
import { BasicsFields, SectionList } from "../components/ResumeFields";

const AUTOSAVE_MS = 1200;

/** Pull a saved item into the section the user clicked "From library" on. */
function LibraryDrawer({
  onClose,
  onPick,
}: {
  onClose: () => void;
  onPick: (item: Item) => void;
}) {
  const queryClient = useQueryClient();
  const library = useQuery({ queryKey: ["library"], queryFn: api.listLibrary });

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteLibraryItem(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["library"] }),
  });

  const take = useMutation({
    mutationFn: (id: number) => api.libraryInstance(id),
    onSuccess: (item) => {
      onPick(item);
      onClose();
    },
  });

  return (
    <div
      className="drawer"
      role="dialog"
      aria-modal="true"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="drawer-panel">
        <div className="page-head">
          <h1 style={{ fontSize: 17 }}>Library</h1>
          <span className="spacer" style={{ marginLeft: "auto" }} />
          <button type="button" onClick={onClose}>
            Close
          </button>
        </div>
        <p className="sub">
          Reusable items — capstone projects, side projects, a role you describe
          differently per application. Star an item in the tree to add it here.
        </p>

        {library.isLoading && <div className="empty">Loading…</div>}
        {library.data?.length === 0 && (
          <div className="empty">
            Nothing saved yet. Click ★ on any item to save it for reuse.
          </div>
        )}

        {library.data?.map((row) => (
          <div className="card tight" key={row.id}>
            <div className="actions">
              <div className="grow" style={{ flex: 1, minWidth: 0 }}>
                <strong>{row.label}</strong>
                <div className="muted small">
                  {row.section_kind}
                  {row.data.subtitle ? ` · ${row.data.subtitle}` : ""}
                  {row.data.bullets?.length
                    ? ` · ${row.data.bullets.length} bullets`
                    : ""}
                </div>
              </div>
              <button
                type="button"
                className="ghost small"
                disabled={take.isPending}
                onClick={() => take.mutate(row.id)}
              >
                Add
              </button>
              <button
                type="button"
                className="icon danger"
                title="Remove from library"
                onClick={() => remove.mutate(row.id)}
              >
                ✕
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Composer() {
  const { applicationId } = useParams();
  const appId = Number(applicationId);
  const queryClient = useQueryClient();

  const [draft, setDraft] = useState<ResumeJSON | null>(null);
  const [title, setTitle] = useState("");
  const [savedSnapshot, setSavedSnapshot] = useState("");
  const [previewVersion, setPreviewVersion] = useState(0);
  const [drawerTarget, setDrawerTarget] = useState<string | null>(null);
  const [showJd, setShowJd] = useState(false);
  const [jd, setJd] = useState("");
  const [notice, setNotice] = useState<{ kind: string; text: string } | null>(null);
  const timer = useRef<number | null>(null);

  const application = useQuery({
    queryKey: ["application", appId],
    queryFn: () => api.application(appId),
    enabled: Number.isFinite(appId),
  });

  const variantId = application.data?.variant_id ?? null;

  const variant = useQuery({
    queryKey: ["variant", variantId],
    queryFn: () => api.variant(variantId!),
    enabled: variantId !== null,
  });

  useEffect(() => {
    if (variant.data && draft === null) {
      setDraft(variant.data.data);
      setTitle(variant.data.title);
      setSavedSnapshot(JSON.stringify(variant.data.data));
    }
  }, [variant.data, draft]);

  // Keep the JD box in step with whatever the server holds.
  useEffect(() => {
    if (application.data) setJd(application.data.job_description);
  }, [application.data]);

  const saveJd = useMutation({
    mutationFn: () => api.patchApplication(appId, { job_description: jd }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["application", appId] });
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      setNotice({ kind: "info", text: "Job description saved." });
    },
    onError: (err) =>
      setNotice({
        kind: "bad",
        text: `Could not save the job description: ${
          err instanceof ApiError ? err.message : String(err)
        }`,
      }),
  });

  const dirty = useMemo(
    () => draft !== null && JSON.stringify(draft) !== savedSnapshot,
    [draft, savedSnapshot],
  );

  const save = useMutation({
    mutationFn: async () => {
      if (!draft || variantId === null) throw new Error("Nothing to save.");
      return api.saveVariant(variantId, { title, data: draft });
    },
    onSuccess: (saved) => {
      setSavedSnapshot(JSON.stringify(saved.data));
      // The preview is server-rendered from the same template as the PDF, so
      // refreshing it after each save keeps the two in lockstep.
      setPreviewVersion((v) => v + 1);
      setNotice(null);
    },
    onError: (err) =>
      setNotice({
        kind: "bad",
        text: `Save failed: ${err instanceof ApiError ? err.message : String(err)}`,
      }),
  });

  // Debounced autosave; the explicit button calls the same mutation.
  const scheduleSave = useCallback(() => {
    if (timer.current !== null) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      timer.current = null;
      save.mutate();
    }, AUTOSAVE_MS);
  }, [save]);

  useEffect(() => {
    if (dirty && !save.isPending) scheduleSave();
    return () => {
      if (timer.current !== null) window.clearTimeout(timer.current);
    };
    // scheduleSave is recreated per render; depending on `dirty` is what matters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dirty, draft, title]);

  // Warn if the tab closes with the debounce still pending.
  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (dirty) e.preventDefault();
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [dirty]);

  const exportPdf = useMutation({
    mutationFn: async () => {
      if (variantId === null) throw new Error("No variant.");
      if (dirty) await save.mutateAsync();
      return api.exportVariant(variantId);
    },
    onSuccess: ({ blob, filename }) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      setNotice({ kind: "info", text: `Exported ${filename}` });
      queryClient.invalidateQueries({ queryKey: ["variant", variantId] });
    },
    onError: (err) => {
      const text = err instanceof ApiError ? err.message : String(err);
      setNotice({
        kind: "warn",
        // 503 means Chromium is absent, which is expected on a fresh machine or
        // while the install is still downloading.
        text:
          err instanceof ApiError && err.status === 503
            ? `${text} You can still open the preview in a new tab and print it to PDF from the browser.`
            : `Export failed: ${text}`,
      });
    },
  });

  const saveToLibrary = useMutation({
    mutationFn: ({ item, kind }: { item: Item; kind: SectionKind }) =>
      api.addLibraryItem({
        label: item.title || "Untitled",
        section_kind: kind,
        data: item,
      }),
    onSuccess: (row) => {
      queryClient.invalidateQueries({ queryKey: ["library"] });
      setNotice({ kind: "info", text: `Saved “${row.label}” to the library.` });
    },
  });

  const addItemToSection = (sectionId: string, item: Item) => {
    if (!draft) return;
    setDraft({
      ...draft,
      sections: draft.sections.map((s) =>
        s.id === sectionId ? { ...s, items: [...s.items, item] } : s,
      ),
    });
  };

  if (application.isLoading || (variantId !== null && variant.isLoading)) {
    return (
      <div className="page">
        <div className="empty">Loading…</div>
      </div>
    );
  }

  if (application.isError) {
    return (
      <div className="page">
        <div className="banner bad">Application not found.</div>
        <Link to="/">Back to applications</Link>
      </div>
    );
  }

  if (variantId === null) {
    return (
      <div className="page">
        <div className="banner info">
          This application has no tailored resume yet. Go back and pick a base
          resume to fork from.
        </div>
        <Link to="/">Back to applications</Link>
      </div>
    );
  }

  if (!draft) {
    return (
      <div className="page">
        <div className="banner bad">Could not load this variant.</div>
        <Link to="/">Back to applications</Link>
      </div>
    );
  }

  const app = application.data!;
  const previewUrl = `/api/variants/${variantId}/preview?v=${previewVersion}`;
  const included = draft.sections
    .filter((s) => s.include)
    .reduce((n, s) => n + s.items.filter((i) => i.include).length, 0);

  return (
    <div className="composer">
      <div className="left">
        <div className="composer-bar">
          <Link to="/" className="small">
            ← Applications
          </Link>
          <span className="spacer" style={{ marginLeft: "auto" }} />
          <span className="muted small">
            {save.isPending ? "Saving…" : dirty ? "Unsaved" : "Saved"}
          </span>
          <button
            type="button"
            disabled={!dirty || save.isPending}
            onClick={() => save.mutate()}
          >
            Save
          </button>
        </div>

        <div className="page-head" style={{ marginBottom: 10 }}>
          <div>
            <h1 style={{ fontSize: 17 }}>
              {app.company} — {app.role}
            </h1>
            <span className="sub">{included} items switched on</span>
          </div>
        </div>

        {notice && <div className={`banner ${notice.kind}`}>{notice.text}</div>}

        <div className="card tight">
          <div className="actions">
            <button
              type="button"
              className="ghost small"
              onClick={() => setShowJd((v) => !v)}
            >
              {showJd ? "Hide" : "Show"} job description
            </button>
            <span className="muted small">
              {app.job_description
                ? `${app.job_description.length} chars`
                : "none saved yet"}
            </span>
          </div>
          {showJd && (
            <>
              <textarea
                className="small"
                value={jd}
                placeholder="Paste the job description here to keep it beside you while you tailor."
                style={{ minHeight: 190, marginTop: 8 }}
                onChange={(e) => setJd(e.target.value)}
              />
              <div className="actions" style={{ marginTop: 6 }}>
                <button
                  type="button"
                  disabled={jd === app.job_description || saveJd.isPending}
                  onClick={() => saveJd.mutate()}
                >
                  {saveJd.isPending ? "Saving…" : "Save job description"}
                </button>
                {jd !== app.job_description && (
                  <button
                    type="button"
                    className="ghost small"
                    onClick={() => setJd(app.job_description)}
                  >
                    Revert
                  </button>
                )}
              </div>
            </>
          )}
        </div>

        <div className="card">
          <label className="field" style={{ marginBottom: 0 }}>
            <span>Variant name (yours, not printed)</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
        </div>

        <BasicsFields
          value={draft.basics}
          onChange={(basics) => setDraft({ ...draft, basics })}
        />

        <h2 style={{ margin: "18px 0 10px" }}>Sections</h2>
        <p className="sub" style={{ marginTop: 0 }}>
          Untick anything to leave it out of this application's resume. The base
          resume is untouched.
        </p>

        <SectionList
          value={draft}
          onChange={setDraft}
          showToggles
          onAddFromLibrary={setDrawerTarget}
          onSaveToLibrary={(item, kind) => saveToLibrary.mutate({ item, kind })}
        />
      </div>

      <div className="right">
        <header>
          <strong className="small">Preview</strong>
          <span className="muted small">
            {dirty ? "refreshes after save" : "matches the PDF"}
          </span>
          <span className="spacer" style={{ marginLeft: "auto" }} />
          <a href={previewUrl} target="_blank" rel="noreferrer">
            <button type="button" className="ghost small">
              Open · print
            </button>
          </a>
          <button
            type="button"
            className="primary"
            disabled={exportPdf.isPending}
            onClick={() => exportPdf.mutate()}
          >
            {exportPdf.isPending ? "Rendering…" : "Export PDF"}
          </button>
        </header>
        <iframe title="Resume preview" src={previewUrl} />
      </div>

      {drawerTarget !== null && (
        <LibraryDrawer
          onClose={() => setDrawerTarget(null)}
          onPick={(item) => addItemToSection(drawerTarget, item)}
        />
      )}
    </div>
  );
}
