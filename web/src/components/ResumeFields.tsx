import {
  emptyItem,
  emptySection,
  newId,
  SECTION_KINDS,
  type Basics,
  type Item,
  type ResumeJSON,
  type Section,
  type SectionKind,
} from "../api/client";

/** Move an array element, returning a new array. */
function move<T>(list: T[], index: number, delta: number): T[] {
  const target = index + delta;
  if (target < 0 || target >= list.length) return list;
  const next = list.slice();
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

function replace<T>(list: T[], index: number, value: T): T[] {
  const next = list.slice();
  next[index] = value;
  return next;
}

// ---------------------------------------------------------------- basics

export function BasicsFields({
  value,
  onChange,
}: {
  value: Basics;
  onChange: (next: Basics) => void;
}) {
  const set = <K extends keyof Basics>(key: K, v: Basics[K]) =>
    onChange({ ...value, [key]: v });

  return (
    <div className="card">
      <h2 style={{ marginBottom: 10 }}>Details</h2>
      <div className="row">
        <label className="field">
          <span>Name</span>
          <input value={value.name} onChange={(e) => set("name", e.target.value)} />
        </label>
        <label className="field">
          <span>Headline</span>
          <input
            value={value.headline}
            placeholder="Senior ML Engineer"
            onChange={(e) => set("headline", e.target.value)}
          />
        </label>
      </div>
      <div className="row">
        <label className="field">
          <span>Email</span>
          <input value={value.email} onChange={(e) => set("email", e.target.value)} />
        </label>
        <label className="field">
          <span>Phone</span>
          <input value={value.phone} onChange={(e) => set("phone", e.target.value)} />
        </label>
        <label className="field">
          <span>Location</span>
          <input
            value={value.location}
            onChange={(e) => set("location", e.target.value)}
          />
        </label>
      </div>

      <label className="field">
        <span>Summary</span>
        <textarea
          value={value.summary}
          onChange={(e) => set("summary", e.target.value)}
        />
      </label>

      <span className="muted small">Links</span>
      {value.links.map((link, i) => (
        <div className="row" key={i} style={{ marginTop: 6 }}>
          <input
            value={link.label}
            placeholder="GitHub"
            onChange={(e) =>
              set("links", replace(value.links, i, { ...link, label: e.target.value }))
            }
          />
          <input
            value={link.url}
            placeholder="https://…"
            onChange={(e) =>
              set("links", replace(value.links, i, { ...link, url: e.target.value }))
            }
          />
          <button
            type="button"
            className="icon"
            title="Remove link"
            style={{ flex: "0 0 auto" }}
            onClick={() => set("links", value.links.filter((_, j) => j !== i))}
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        className="ghost small"
        style={{ marginTop: 8 }}
        onClick={() => set("links", [...value.links, { label: "", url: "" }])}
      >
        + Link
      </button>
    </div>
  );
}

// ---------------------------------------------------------------- one item

function ItemNode({
  item,
  kind,
  showToggles,
  onChange,
  onRemove,
  onMove,
  onSaveToLibrary,
}: {
  item: Item;
  kind: SectionKind;
  showToggles: boolean;
  onChange: (next: Item) => void;
  onRemove: () => void;
  onMove: (delta: number) => void;
  onSaveToLibrary?: (item: Item) => void;
}) {
  const set = <K extends keyof Item>(key: K, v: Item[K]) =>
    onChange({ ...item, [key]: v });

  const isSkills = kind === "skills";
  const off = showToggles && !item.include;

  return (
    <div className={`item-node${off ? " off" : ""}`}>
      <div className="node-head">
        {showToggles && (
          <input
            type="checkbox"
            checked={item.include}
            title="Include in this resume"
            onChange={(e) => set("include", e.target.checked)}
          />
        )}
        <input
          className="grow"
          value={item.title}
          placeholder={
            isSkills
              ? "Group (e.g. Languages)"
              : kind === "education"
                ? "Degree"
                : kind === "projects"
                  ? "Project name"
                  : "Job title"
          }
          onChange={(e) => set("title", e.target.value)}
        />
        <button type="button" className="icon" title="Move up" onClick={() => onMove(-1)}>
          ↑
        </button>
        <button
          type="button"
          className="icon"
          title="Move down"
          onClick={() => onMove(1)}
        >
          ↓
        </button>
        {onSaveToLibrary && (
          <button
            type="button"
            className="icon"
            title="Save to library for reuse"
            onClick={() => onSaveToLibrary(item)}
          >
            ★
          </button>
        )}
        <button type="button" className="icon" title="Delete" onClick={onRemove}>
          ✕
        </button>
      </div>

      <div className="node-body" style={{ paddingLeft: showToggles ? 26 : 9 }}>
        {isSkills ? (
          <label className="field">
            <span>Skills (comma separated)</span>
            <input
              value={item.tags.join(", ")}
              onChange={(e) =>
                set(
                  "tags",
                  e.target.value
                    .split(",")
                    .map((t) => t.trim())
                    .filter(Boolean),
                )
              }
            />
          </label>
        ) : (
          <>
            <div className="row">
              <label className="field">
                <span>{kind === "education" ? "Institution" : "Organisation"}</span>
                <input
                  value={item.subtitle}
                  onChange={(e) => set("subtitle", e.target.value)}
                />
              </label>
              <label className="field">
                <span>Location</span>
                <input
                  value={item.location}
                  onChange={(e) => set("location", e.target.value)}
                />
              </label>
            </div>

            <div className="row">
              <label className="field">
                <span>Start</span>
                <input
                  value={item.start}
                  placeholder="Jan 2022"
                  onChange={(e) => set("start", e.target.value)}
                />
              </label>
              <label className="field">
                <span>End</span>
                <input
                  value={item.end}
                  placeholder="Mar 2024"
                  disabled={item.current}
                  onChange={(e) => set("end", e.target.value)}
                />
              </label>
              <label
                className="field"
                style={{ flex: "0 0 auto", alignSelf: "end", paddingBottom: 7 }}
              >
                <span>Current</span>
                <input
                  type="checkbox"
                  checked={item.current}
                  onChange={(e) => set("current", e.target.checked)}
                />
              </label>
            </div>

            <label className="field">
              <span>{kind === "projects" ? "Tech / link" : "Link"}</span>
              <input
                value={item.url}
                placeholder="https://…"
                onChange={(e) => set("url", e.target.value)}
              />
            </label>

            <span className="muted small">Bullets</span>
            <div style={{ marginTop: 5 }}>
              {item.bullets.map((bullet, bi) => (
                <div className="bullet-row" key={bullet.id}>
                  {showToggles && (
                    <input
                      type="checkbox"
                      checked={bullet.include}
                      title="Include this bullet"
                      style={{ marginTop: 10 }}
                      onChange={(e) =>
                        set(
                          "bullets",
                          replace(item.bullets, bi, {
                            ...bullet,
                            include: e.target.checked,
                          }),
                        )
                      }
                    />
                  )}
                  <textarea
                    value={bullet.text}
                    style={{ opacity: showToggles && !bullet.include ? 0.5 : 1 }}
                    onChange={(e) =>
                      set(
                        "bullets",
                        replace(item.bullets, bi, { ...bullet, text: e.target.value }),
                      )
                    }
                  />
                  <div style={{ display: "flex", flexDirection: "column" }}>
                    <button
                      type="button"
                      className="icon"
                      title="Move up"
                      onClick={() => set("bullets", move(item.bullets, bi, -1))}
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      className="icon"
                      title="Move down"
                      onClick={() => set("bullets", move(item.bullets, bi, 1))}
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      className="icon"
                      title="Delete bullet"
                      onClick={() =>
                        set(
                          "bullets",
                          item.bullets.filter((_, j) => j !== bi),
                        )
                      }
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
              <button
                type="button"
                className="ghost small"
                onClick={() =>
                  set("bullets", [
                    ...item.bullets,
                    { id: newId(), text: "", include: true },
                  ])
                }
              >
                + Bullet
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- sections

export function SectionList({
  value,
  onChange,
  showToggles = false,
  onAddFromLibrary,
  onSaveToLibrary,
}: {
  value: ResumeJSON;
  onChange: (next: ResumeJSON) => void;
  showToggles?: boolean;
  onAddFromLibrary?: (sectionId: string) => void;
  onSaveToLibrary?: (item: Item, kind: SectionKind) => void;
}) {
  const setSections = (sections: Section[]) => onChange({ ...value, sections });

  const patchSection = (si: number, next: Section) =>
    setSections(replace(value.sections, si, next));

  return (
    <>
      {value.sections.map((section, si) => {
        const off = showToggles && !section.include;
        return (
          <div className={`node${off ? " off" : ""}`} key={section.id}>
            <div className="node-head">
              {showToggles && (
                <input
                  type="checkbox"
                  checked={section.include}
                  title="Include this section"
                  onChange={(e) =>
                    patchSection(si, { ...section, include: e.target.checked })
                  }
                />
              )}
              <input
                className="grow"
                value={section.title}
                placeholder="Section heading"
                onChange={(e) =>
                  patchSection(si, { ...section, title: e.target.value })
                }
              />
              <select
                value={section.kind}
                title="Section kind controls how it renders"
                style={{ width: 130, flex: "0 0 auto" }}
                onChange={(e) =>
                  patchSection(si, {
                    ...section,
                    kind: e.target.value as SectionKind,
                  })
                }
              >
                {SECTION_KINDS.map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="icon"
                title="Move section up"
                onClick={() => setSections(move(value.sections, si, -1))}
              >
                ↑
              </button>
              <button
                type="button"
                className="icon"
                title="Move section down"
                onClick={() => setSections(move(value.sections, si, 1))}
              >
                ↓
              </button>
              <button
                type="button"
                className="icon"
                title="Delete section"
                onClick={() =>
                  setSections(value.sections.filter((_, j) => j !== si))
                }
              >
                ✕
              </button>
            </div>

            <div className="node-body">
              {section.items.map((item, ii) => (
                <ItemNode
                  key={item.id}
                  item={item}
                  kind={section.kind}
                  showToggles={showToggles}
                  onChange={(next) =>
                    patchSection(si, {
                      ...section,
                      items: replace(section.items, ii, next),
                    })
                  }
                  onMove={(delta) =>
                    patchSection(si, {
                      ...section,
                      items: move(section.items, ii, delta),
                    })
                  }
                  onRemove={() =>
                    patchSection(si, {
                      ...section,
                      items: section.items.filter((_, j) => j !== ii),
                    })
                  }
                  onSaveToLibrary={
                    onSaveToLibrary
                      ? (it) => onSaveToLibrary(it, section.kind)
                      : undefined
                  }
                />
              ))}

              <div className="actions">
                <button
                  type="button"
                  className="ghost small"
                  onClick={() =>
                    patchSection(si, {
                      ...section,
                      items: [...section.items, emptyItem()],
                    })
                  }
                >
                  + Item
                </button>
                {onAddFromLibrary && (
                  <button
                    type="button"
                    className="ghost small"
                    onClick={() => onAddFromLibrary(section.id)}
                  >
                    + From library
                  </button>
                )}
              </div>
            </div>
          </div>
        );
      })}

      <div className="actions" style={{ marginTop: 10, flexWrap: "wrap" }}>
        <span className="muted small">Add section:</span>
        {SECTION_KINDS.map((kind) => (
          <button
            type="button"
            key={kind}
            className="ghost small"
            onClick={() => setSections([...value.sections, emptySection(kind)])}
          >
            + {kind}
          </button>
        ))}
      </div>
    </>
  );
}
