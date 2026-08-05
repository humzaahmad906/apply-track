import { ACTIVE_STATUSES, type AppStatus, type StageEvent } from "../api/client";
import { shortDate } from "../format";

/**
 * The pipeline for one job. Stages it has reached are filled in with the date
 * it got there; the current one is ringed.
 *
 * A closed job keeps the five stages and gains its ending, so you can still
 * see how far it went before it stopped.
 */
export default function StageTimeline({
  events,
  current,
}: {
  events: StageEvent[];
  current: AppStatus;
}) {
  const firstReached = new Map<AppStatus, string>();
  for (const event of events) {
    if (!firstReached.has(event.status)) firstReached.set(event.status, event.at);
  }

  const closed = current === "rejected" || current === "withdrawn";
  const steps: AppStatus[] = closed ? [...ACTIVE_STATUSES, current] : ACTIVE_STATUSES;

  return (
    <div className="timeline">
      {steps.map((status, i) => {
        const at = firstReached.get(status);
        // A connector is drawn only where both ends were actually reached, so
        // a stage that got skipped leaves a visible gap instead of looking as
        // though it happened.
        const linkIn = Boolean(at) && firstReached.has(steps[i - 1]);
        const linkOut = Boolean(at) && firstReached.has(steps[i + 1]);
        const classes = [
          "step",
          `stage-${status}`,
          at ? "done" : "",
          linkIn ? "link-in" : "",
          linkOut ? "link-out" : "",
          status === current ? "now" : "",
        ]
          .filter(Boolean)
          .join(" ");
        return (
          <div className={classes} key={status}>
            <span className="bead" />
            <div className="label">{status}</div>
            <div className="date">{at ? shortDate(at) : ""}</div>
          </div>
        );
      })}
    </div>
  );
}
