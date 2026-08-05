import { ACTIVE_STATUSES, type AppStatus, type DashboardPayload } from "../api/client";

/**
 * Counts per stage, and a way to narrow the board to one of them.
 *
 * Only the five active stages appear. Rejected and withdrawn live in the
 * archive, where a closed application belongs.
 */
export default function FunnelStrip({
  funnel,
  filter,
  onFilter,
}: {
  funnel: DashboardPayload["funnel"];
  filter: AppStatus | null;
  onFilter: (status: AppStatus | null) => void;
}) {
  const counts = new Map(funnel.map((f) => [f.status, f.count]));

  return (
    <div className="funnel">
      {ACTIVE_STATUSES.map((status) => {
        const count = counts.get(status) ?? 0;
        return (
          <button
            key={status}
            type="button"
            className={[
              `stage-${status}`,
              filter === status ? "on" : "",
              count === 0 ? "zero" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            title={
              filter === status
                ? "Show every stage again"
                : `Show only ${status}`
            }
            onClick={() => onFilter(filter === status ? null : status)}
          >
            <span className="dot" />
            <span style={{ textTransform: "capitalize" }}>{status}</span>
            <span className="n">{count}</span>
          </button>
        );
      })}
    </div>
  );
}
