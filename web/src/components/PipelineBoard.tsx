import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  ACTIVE_STATUSES,
  api,
  ApiError,
  APP_STATUSES,
  type AppStatus,
  type BoardCard,
  type DashboardPayload,
} from "../api/client";
import { relative, shortDate } from "../format";
import { Book, Calendar, Clock, Dots, FileCheck, FileText, Send } from "../icons";

/** Relocate a card locally so a dropped card lands before the server answers. */
function moveCard(
  data: DashboardPayload,
  id: number,
  status: AppStatus,
): DashboardPayload {
  let moving: BoardCard | undefined;

  const board: Record<string, BoardCard[]> = {};
  for (const [column, cards] of Object.entries(data.board)) {
    board[column] = cards.filter((card) => {
      if (card.id !== id) return true;
      moving = card;
      return false;
    });
  }
  let archive = data.archive.filter((card) => {
    if (card.id !== id) return true;
    moving = card;
    return false;
  });

  if (!moving) return data;
  const moved: BoardCard = { ...moving, status, days_in_stage: 0 };
  if (status === "rejected" || status === "withdrawn") {
    archive = [moved, ...archive];
  } else {
    board[status] = [...(board[status] ?? []), moved];
  }
  return { ...data, board, archive };
}

function Card({
  card,
  onMove,
  onDragState,
  dragging,
}: {
  card: BoardCard;
  onMove: (id: number, status: AppStatus) => void;
  onDragState: (id: number | null) => void;
  dragging: boolean;
}) {
  const navigate = useNavigate();
  const [menu, setMenu] = useState(false);
  const urgent = card.urgency !== null && card.urgency <= 1 ? ` u${card.urgency}` : "";

  return (
    <div
      className={`board-card stage-${card.status}${urgent}${dragging ? " dragging" : ""}`}
      role="button"
      tabIndex={0}
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", String(card.id));
        e.dataTransfer.effectAllowed = "move";
        onDragState(card.id);
      }}
      onDragEnd={() => onDragState(null)}
      onClick={() => navigate(`/jobs/${card.id}`)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          navigate(`/jobs/${card.id}`);
        }
      }}
    >
      <div className="flex">
        <span className="avatar" aria-hidden>
          {card.company.trim().charAt(0).toUpperCase() || "?"}
        </span>
        <span className="grow" style={{ minWidth: 0 }}>
          <span className="co truncate">{card.company}</span>
          <span className="role truncate">{card.role}</span>
        </span>
        <button
          type="button"
          className="icon"
          title="Move to another stage"
          aria-label="Move to another stage"
          onClick={(e) => {
            e.stopPropagation();
            setMenu((v) => !v);
          }}
        >
          <Dots size={15} />
        </button>
      </div>

      {/* How far along the five stages, at a glance. */}
      <div className="track" aria-hidden>
        {ACTIVE_STATUSES.map((_, i) => (
          <span key={i} className={i <= card.stage_index ? "on" : ""} />
        ))}
      </div>

      {/* What exists for this job already. Filled means done. */}
      <div className="chips">
        <span className={card.has_jd ? "on" : ""} title="Job description saved">
          <FileText size={13} />
        </span>
        <span
          className={card.variant_id !== null ? "on" : ""}
          title="Tailored resume composed"
        >
          <FileCheck size={13} />
        </span>
        <span className={card.exported ? "on" : ""} title="Resume exported">
          <Send size={13} />
        </span>
        {card.prep_gaps !== null && (
          <span className="on" title={`${card.prep_gaps} things worth reading`}>
            <Book size={13} />
            {card.prep_gaps}
          </span>
        )}
        {(card.analysis === "running" || card.analysis === "pending") && (
          <span className="working" title="Prep is being written" />
        )}
      </div>

      {card.action_title && (
        <div className="todo truncate" title={card.action_detail}>
          {card.action_title}
        </div>
      )}

      <div className="meta">
        {card.due ? (
          <>
            <Calendar size={12} />
            <span>{relative(card.due)}</span>
            <span className="faint">· {shortDate(card.due)}</span>
          </>
        ) : (
          <>
            <Clock size={12} />
            <span>{card.days_in_stage}d in {card.status}</span>
          </>
        )}
      </div>

      {menu && (
        <div className="card-menu" onClick={(e) => e.stopPropagation()}>
          {APP_STATUSES.filter((s) => s !== card.status).map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => {
                setMenu(false);
                onMove(card.id, status);
              }}
            >
              {status}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function PipelineBoard({
  data,
  filter,
}: {
  data: DashboardPayload;
  filter: AppStatus | null;
}) {
  const queryClient = useQueryClient();
  const [over, setOver] = useState<AppStatus | null>(null);
  const [dragging, setDragging] = useState<number | null>(null);
  const [error, setError] = useState("");

  const move = useMutation({
    mutationFn: ({ id, status }: { id: number; status: AppStatus }) =>
      api.patchApplication(id, { status }),
    // Land the card immediately; the server is only confirming.
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: ["dashboard"] });
      const previous = queryClient.getQueryData<DashboardPayload>(["dashboard"]);
      if (previous) {
        queryClient.setQueryData(["dashboard"], moveCard(previous, id, status));
      }
      return { previous };
    },
    onError: (err, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["dashboard"], context.previous);
      }
      setError(err instanceof ApiError ? err.message : String(err));
    },
    onSuccess: () => setError(""),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
  });

  const columns = filter ? [filter] : ACTIVE_STATUSES;
  const onMove = (id: number, status: AppStatus) => move.mutate({ id, status });

  return (
    <>
      {error && <div className="banner bad">{error}</div>}
      <div className="board">
        {columns.map((status) => {
          const cards = data.board[status] ?? [];
          return (
            <div
              key={status}
              className={`board-col stage-${status}${over === status ? " over" : ""}`}
              onDragOver={(e) => {
                // Without preventDefault the browser refuses the drop.
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";
                setOver(status);
              }}
              onDragLeave={(e) => {
                // Moving onto a child fires dragleave on the parent too.
                if (!e.currentTarget.contains(e.relatedTarget as Node)) {
                  setOver(null);
                }
              }}
              onDrop={(e) => {
                e.preventDefault();
                setOver(null);
                const id = Number(e.dataTransfer.getData("text/plain"));
                if (Number.isFinite(id) && id > 0) onMove(id, status);
              }}
            >
              <header>
                <span className="dot" />
                <span>{status}</span>
                <span className="n">{cards.length}</span>
              </header>
              {cards.length === 0 && <div className="none">—</div>}
              {cards.map((card) => (
                <Card
                  key={card.id}
                  card={card}
                  onMove={onMove}
                  onDragState={setDragging}
                  dragging={dragging === card.id}
                />
              ))}
            </div>
          );
        })}
      </div>
    </>
  );
}
