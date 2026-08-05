import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, ApiError, type AppStatus, type DashboardPayload } from "../api/client";
import ActionQueue from "../components/ActionQueue";
import FunnelStrip from "../components/FunnelStrip";
import PipelineBoard from "../components/PipelineBoard";
import { shortDate } from "../format";
import { Confetti, Flame, Plus, ProgressRing, Trophy } from "../icons";

/** Says something true and encouraging about where the week actually is. */
function weekNote(stats: DashboardPayload["stats"]): string {
  const left = stats.weekly_goal - stats.this_week;
  if (stats.this_week === 0) return "No applications out this week yet.";
  if (left <= 0) return "Weekly target hit. Anything more is a bonus.";
  if (left === 1) return "One more this week and you have hit the target.";
  return `${left} more this week to hit the target.`;
}

function Momentum({ stats }: { stats: DashboardPayload["stats"] }) {
  return (
    <>
      {stats.offers > 0 && (
        <div className="celebrate">
          <Confetti />
          <div>
            <b>
              {stats.offers === 1 ? "You have an offer." : `${stats.offers} offers.`}
            </b>
            <div className="sub">
              Everything else on this page just became optional.
            </div>
          </div>
          <Trophy size={26} className="push" />
        </div>
      )}

      <div className="card momentum">
        <ProgressRing value={stats.this_week} goal={stats.weekly_goal} />
        <div className="goal-copy">
          <b>
            {stats.this_week} of {stats.weekly_goal} out this week
          </b>
          <span>{weekNote(stats)}</span>
        </div>

        {stats.streak > 1 && (
          <span className="streak" title="Consecutive days you moved something">
            <Flame size={14} />
            {stats.streak} day streak
          </span>
        )}

        <span className="push" />

        <div className="stat">
          <b>{stats.active}</b>
          <span>open</span>
        </div>
        <div className="stat">
          <b>{stats.sent}</b>
          <span>applied</span>
        </div>
        <div className="stat">
          <b>{stats.replies}</b>
          <span>replies</span>
        </div>
        <div className="stat">
          <b>{stats.sent ? `${Math.round(stats.reply_rate * 100)}%` : "—"}</b>
          <span>reply rate</span>
        </div>
      </div>
    </>
  );
}

/** The only form on the dashboard: start tracking something new. */
function NewJob({ onDone }: { onDone: () => void }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ company: "", role: "", job_url: "" });
  const [error, setError] = useState("");

  const create = useMutation({
    mutationFn: () => api.createApplication(form),
    onSuccess: (app) => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      // Straight to the job page, which is where the description goes.
      navigate(`/jobs/${app.id}`);
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  const ready = form.company.trim() && form.role.trim();

  return (
    <div className="card">
      <h2>Track a job</h2>
      {error && <div className="banner bad">{error}</div>}
      <div className="row" style={{ marginTop: 10 }}>
        <label className="field">
          <span>Company *</span>
          <input
            autoFocus
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
        <label className="field">
          <span>Posting link</span>
          <input
            value={form.job_url}
            placeholder="https://…"
            onChange={(e) => setForm({ ...form, job_url: e.target.value })}
          />
        </label>
      </div>
      <div className="actions">
        <button
          type="button"
          className="primary"
          disabled={!ready || create.isPending}
          onClick={() => create.mutate()}
        >
          {create.isPending ? "Adding…" : "Add and open"}
        </button>
        <button type="button" onClick={onDone}>
          Cancel
        </button>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [adding, setAdding] = useState(false);
  const [filter, setFilter] = useState<AppStatus | null>(null);
  const [showArchive, setShowArchive] = useState(false);

  const dash = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.dashboard,
    // Analyses land in the background, so the page keeps itself current.
    refetchInterval: 15_000,
  });

  if (dash.isLoading) {
    return (
      <div className="page wide">
        <div className="empty">Loading…</div>
      </div>
    );
  }

  if (dash.isError || !dash.data) {
    return (
      <div className="page wide">
        <div className="banner bad">
          Could not reach the API. Is it running on port 8000?
        </div>
      </div>
    );
  }

  const { stats, funnel, actions, archive } = dash.data;
  const total = funnel.reduce((n, f) => n + f.count, 0);

  const headline =
    stats.needs_action === 0
      ? "Nothing needs you"
      : `${stats.needs_action} thing${stats.needs_action === 1 ? "" : "s"} need${
          stats.needs_action === 1 ? "s" : ""
        } you`;

  return (
    <div className="page wide">
      <div className="headline">
        <h1>{headline}</h1>
        <span className="push" />
        {!adding && (
          <button type="button" className="primary" onClick={() => setAdding(true)}>
            <Plus size={15} /> Track a job
          </button>
        )}
      </div>

      {adding && <NewJob onDone={() => setAdding(false)} />}

      {total === 0 && !adding ? (
        <div className="empty">
          Nothing tracked yet. Add the first job and this becomes your morning
          view: what stage everything is at, and what needs you today.
        </div>
      ) : (
        <>
          <Momentum stats={stats} />

          <div className="section-head">
            <h2>Needs you</h2>
          </div>
          <ActionQueue actions={actions} />

          <div className="section-head">
            <h2>Pipeline</h2>
            {filter && (
              <button
                type="button"
                className="icon"
                onClick={() => setFilter(null)}
              >
                show all stages
              </button>
            )}
          </div>
          <FunnelStrip funnel={funnel} filter={filter} onFilter={setFilter} />
          <PipelineBoard data={dash.data} filter={filter} />

          {archive.length > 0 && (
            <>
              <button
                type="button"
                className="archive-toggle"
                onClick={() => setShowArchive((v) => !v)}
              >
                {showArchive ? "▾" : "▸"} Archive — {archive.length} closed
              </button>
              {showArchive && (
                <div className="card tight">
                  <table>
                    <tbody>
                      {archive.map((card) => (
                        <tr
                          key={card.id}
                          onClick={() => navigate(`/jobs/${card.id}`)}
                          style={{ cursor: "pointer" }}
                        >
                          <td>{card.company}</td>
                          <td className="muted">{card.role}</td>
                          <td style={{ width: 110 }}>
                            <span className={`pill ${card.status}`}>
                              {card.status}
                            </span>
                          </td>
                          <td className="muted small" style={{ width: 90 }}>
                            {shortDate(card.stage_since)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
