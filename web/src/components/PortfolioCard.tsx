import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api, ApiError } from "../api/client";
import { Check, External } from "../icons";

/**
 * Put the project on humzaahmad906.github.io.
 *
 * Everything is editable before it goes, because a card is public writing and
 * the generated wording is sized for a resume rather than a portfolio. The
 * write lands uncommitted so the diff can be read; pushing stays a decision.
 */
export default function PortfolioCard({
  applicationId,
  built,
}: {
  applicationId: number;
  built: boolean;
}) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [blurb, setBlurb] = useState("");
  const [tags, setTags] = useState("");
  const [section, setSection] = useState("featured");
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const state = useQuery({
    queryKey: ["portfolio", applicationId],
    queryFn: () => api.portfolioState(applicationId),
    enabled: built,
  });

  // Seed the editable fields once the defaults arrive.
  useEffect(() => {
    if (!state.data) return;
    setTitle(state.data.title);
    setBlurb(state.data.blurb);
    setTags(state.data.tags);
  }, [state.data]);

  const publish = useMutation({
    mutationFn: () =>
      api.publishToPortfolio(applicationId, { section, title, blurb, tags }),
    onSuccess: (res) => {
      setError("");
      setNote(
        `Written into ${res.path}. It is uncommitted — read the diff, then commit and push.`,
      );
      queryClient.invalidateQueries({ queryKey: ["portfolio", applicationId] });
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  if (!built) return null;

  // The server checks the page for the *spec* title, and the card that went up
  // usually has an edited one, so remember that this one landed.
  if (publish.isSuccess) {
    return (
      <p className="done-means">
        <Check size={14} /> Added to <code>projects.html</code>, uncommitted.
        Read the diff, then commit and push.
      </p>
    );
  }

  if (state.data && !state.data.available) {
    return (
      <div className="gate">
        <strong>Portfolio</strong>
        <p className="muted small">{state.data.error}</p>
      </div>
    );
  }

  if (state.data?.published) {
    return (
      <p className="done-means">
        <Check size={14} /> Already on the portfolio site.
      </p>
    );
  }

  return (
    <div className="gate">
      <strong>Also put it on the portfolio</strong>
      <p className="muted small">
        Writes a card into <code>projects.html</code> and leaves it
        uncommitted, so you read the diff before anything is public. Trim the
        wording first — site cards are shorter than resume bullets.
      </p>

      {error && <div className="banner bad">{error}</div>}
      {note && <div className="banner info">{note}</div>}

      <div className="row">
        <label className="field">
          <span>Title</span>
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label className="field" style={{ flex: "0 0 150px" }}>
          <span>Section</span>
          <select value={section} onChange={(e) => setSection(e.target.value)}>
            <option value="featured">Featured</option>
            <option value="earlier">Earlier work</option>
          </select>
        </label>
      </div>
      <label className="field">
        <span>Tags — separated by ·</span>
        <input value={tags} onChange={(e) => setTags(e.target.value)} />
      </label>
      <label className="field">
        <span>
          Description{" "}
          <span className="faint">
            {blurb.length} chars — the cards on your site run 200–320
          </span>
        </span>
        <textarea
          value={blurb}
          style={{ minHeight: 90 }}
          onChange={(e) => setBlurb(e.target.value)}
        />
      </label>

      <div className="actions wrap">
        <button
          type="button"
          className="primary"
          disabled={publish.isPending || !title.trim() || !blurb.trim()}
          onClick={() => publish.mutate()}
        >
          {publish.isPending ? "Writing…" : "Add to portfolio"}
        </button>
        <a
          href="https://humzaahmad906.github.io/projects/"
          target="_blank"
          rel="noreferrer"
          className="small"
        >
          see the page <External size={12} />
        </a>
      </div>
    </div>
  );
}
