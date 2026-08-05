import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api, ApiError, type Action, type ApplicationRow } from "../api/client";
import { inDays } from "../format";

/**
 * What each kind of action offers as its one click.
 *
 * Every rule the backend can raise has a resolution here, because an item you
 * can only read is just another thing to worry about.
 */
function resolution(action: Action): {
  label: string;
  href?: string;
  patch?: Partial<ApplicationRow>;
} {
  const job = `/jobs/${action.application_id}`;
  switch (action.kind) {
    case "follow_up":
      return {
        label: "Mark contacted",
        patch: { last_contact_at: new Date().toISOString() },
      };
    case "not_marked_sent":
      return { label: "Mark applied", patch: { status: "applied" } };
    case "ready_to_send":
      return { label: "Open resume", href: `${job}/resume` };
    case "needs_resume":
      return { label: "Compose", href: job };
    case "needs_jd":
      return { label: "Add job description", href: job };
    case "no_next_step":
      return { label: "Set next step", href: job };
    default:
      return { label: "Open", href: job };
  }
}

export default function ActionQueue({ actions }: { actions: Action[] }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  const patch = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<ApplicationRow> }) =>
      api.patchApplication(id, body),
    onSuccess: () => {
      setError("");
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : String(err)),
  });

  if (actions.length === 0) {
    return (
      <div className="empty">
        Nothing needs you right now. Everything tracked is either waiting on
        somebody else or already done.
      </div>
    );
  }

  return (
    <>
      {error && <div className="banner bad">{error}</div>}
      <div className="card queue">
        {actions.map((action) => {
          const fix = resolution(action);
          const urgent = action.urgency <= 1 ? ` u${action.urgency}` : "";
          return (
            <div className={`action${urgent}`} key={action.application_id}>
              <span className="flag" />
              <div className="grow">
                <div className="flex wrap">
                  <Link to={`/jobs/${action.application_id}`} className="who">
                    {action.company}
                  </Link>
                  <span className="muted small">{action.role}</span>
                </div>
                <div className="what">
                  {action.title}
                  {action.detail ? ` — ${action.detail}` : ""}
                </div>
              </div>
              <div className="actions">
                <button
                  type="button"
                  className={action.urgency <= 1 ? "primary" : ""}
                  disabled={patch.isPending}
                  onClick={() => {
                    if (fix.href) navigate(fix.href);
                    else if (fix.patch)
                      patch.mutate({
                        id: action.application_id,
                        body: fix.patch,
                      });
                  }}
                >
                  {fix.label}
                </button>
                <button
                  type="button"
                  className="icon"
                  title="Hide this for three days"
                  disabled={patch.isPending}
                  onClick={() =>
                    patch.mutate({
                      id: action.application_id,
                      body: { snoozed_until: inDays(3) },
                    })
                  }
                >
                  snooze
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
