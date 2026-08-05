import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api, ApiError } from "../api/client";
import { Check, External } from "../icons";

/** Same shape the server refuses, so nothing surprises you on submit. */
const PLACEHOLDER = /<[A-Za-z][A-Za-z0-9 _/+-]*>/g;

function placeholdersIn(...text: string[]): string[] {
  const found = text.join(" ").match(PLACEHOLDER) ?? [];
  return [...new Set(found)];
}

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
  const [fills, setFills] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const pending = placeholdersIn(title, blurb);

  /** Substitute one number everywhere it appears, then drop the field. */
  const apply = (slot: string) => {
    const value = (fills[slot] ?? "").trim();
    if (!value) return;
    setTitle((t) => t.split(slot).join(value));
    setBlurb((b) => b.split(slot).join(value));
    setFills(({ [slot]: _drop, ...rest }) => rest);
  };

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

      {/* The generated bullets carry a slot per measurement. Rather than
          refusing the card and sending you back to the text, ask for the
          numbers — they are the only thing missing. */}
      {pending.length > 0 && (
        <div className="fills">
          <strong className="small">
            {pending.length} number{pending.length === 1 ? "" : "s"} to fill in
          </strong>
          <p className="faint small">
            Only you have these. They go in everywhere the slot appears.
          </p>
          {pending.map((slot) => (
            <label className="fill" key={slot}>
              <code>{slot}</code>
              <input
                value={fills[slot] ?? ""}
                placeholder="the real number"
                onChange={(e) =>
                  setFills((f) => ({ ...f, [slot]: e.target.value }))
                }
                onBlur={() => apply(slot)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    apply(slot);
                  }
                }}
              />
            </label>
          ))}
        </div>
      )}

      <div className="actions wrap">
        <button
          type="button"
          className="primary"
          disabled={
            publish.isPending ||
            !title.trim() ||
            !blurb.trim() ||
            pending.length > 0
          }
          title={
            pending.length > 0
              ? "Fill in the numbers first — they would show as <slots> on the page"
              : "Write the card into projects.html"
          }
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
