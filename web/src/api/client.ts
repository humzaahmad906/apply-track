// Mirrors api/apply_track/schemas.py. Keep the two in step.

export type SectionKind =
  | "experience"
  | "education"
  | "projects"
  | "skills"
  | "certifications"
  | "awards"
  | "publications"
  | "custom";

export const SECTION_KINDS: SectionKind[] = [
  "experience",
  "projects",
  "education",
  "skills",
  "certifications",
  "awards",
  "publications",
  "custom",
];

export interface Link {
  label: string;
  url: string;
}

export interface Basics {
  name: string;
  headline: string;
  email: string;
  phone: string;
  location: string;
  links: Link[];
  summary: string;
}

export interface Bullet {
  id: string;
  text: string;
  include: boolean;
}

export interface Item {
  id: string;
  include: boolean;
  title: string;
  subtitle: string;
  location: string;
  start: string;
  end: string;
  current: boolean;
  url: string;
  description: string;
  bullets: Bullet[];
  tags: string[];
}

export interface Section {
  id: string;
  kind: SectionKind;
  title: string;
  include: boolean;
  items: Item[];
}

export interface ResumeJSON {
  basics: Basics;
  sections: Section[];
}

export type AppStatus =
  | "wishlist"
  | "applied"
  | "screen"
  | "interview"
  | "offer"
  | "rejected"
  | "withdrawn";

export const APP_STATUSES: AppStatus[] = [
  "wishlist",
  "applied",
  "screen",
  "interview",
  "offer",
  "rejected",
  "withdrawn",
];

export interface ApplicationRow {
  id: number;
  company: string;
  role: string;
  job_url: string;
  job_description: string;
  status: AppStatus;
  notes: string;
  applied_at: string | null;
  created_at: string;
  updated_at: string;
  variant_id: number | null;
}

export interface ResumeSummary {
  id: number;
  name: string;
  source_filename: string;
  section_count: number;
  updated_at: string;
}

export interface ResumeDetail {
  id: number;
  name: string;
  source_filename: string;
  updated_at: string;
  data: ResumeJSON;
}

export interface VariantDetail {
  id: number;
  application_id: number;
  base_resume_id: number | null;
  title: string;
  data: ResumeJSON;
  last_export: string;
  updated_at: string;
}

export interface ParseJob {
  id: string;
  filename: string;
  status: "queued" | "running" | "done" | "error";
  error: string;
  result: ResumeJSON | null;
}

export interface LibraryRow {
  id: number;
  label: string;
  section_kind: string;
  data: Item;
  created_at: string;
}

export interface Reading {
  path: string;
  title: string;
  url: string;
  course: string;
}

export interface Gap {
  skill: string;
  why: string;
  lessons: Reading[];
}

export interface CoveredSkill {
  skill: string;
  evidence: string;
}

/** JD-versus-resume comparison. Study aid only — never rendered into the PDF. */
export interface ReadingList {
  application_id: number;
  created_at: string;
  lesson_count: number;
  stale: boolean;
  gaps: Gap[];
  covered: CoveredSkill[];
  basics: string[];
  note: string;
}

export interface CourseIndex {
  lesson_count: number;
  courses: Record<string, number>;
  indexed: boolean;
}

export interface Health {
  ok: boolean;
  claude_cli: string | null;
  claude_cli_error: string;
  parse_model: string;
  pdf_export: boolean;
  pdf_export_error: string;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers:
      init?.body instanceof FormData
        ? init?.headers
        : { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
      else if (body?.detail) detail = JSON.stringify(body.detail);
    } catch {
      // Non-JSON error body; statusText is the best we have.
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => request<Health>("/api/health"),

  // --- flow one: parse a base resume -------------------------------------
  uploadResume(file: File) {
    const form = new FormData();
    form.append("file", file);
    return request<{ job_id: string }>("/api/resumes/upload", {
      method: "POST",
      body: form,
    });
  },
  job: (id: string) => request<ParseJob>(`/api/resumes/jobs/${id}`),

  listResumes: () => request<ResumeSummary[]>("/api/resumes"),
  resume: (id: number) => request<ResumeDetail>(`/api/resumes/${id}`),
  saveResume: (body: { name: string; source_filename?: string; data: ResumeJSON }) =>
    request<ResumeSummary>("/api/resumes", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateResume: (id: number, body: { name: string; data: ResumeJSON }) =>
    request<ResumeSummary>(`/api/resumes/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  deleteResume: (id: number) =>
    request<void>(`/api/resumes/${id}`, { method: "DELETE" }),

  // --- applications -------------------------------------------------------
  listApplications: () => request<ApplicationRow[]>("/api/applications"),
  application: (id: number) => request<ApplicationRow>(`/api/applications/${id}`),
  createApplication: (body: Partial<ApplicationRow>) =>
    request<ApplicationRow>("/api/applications", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  patchApplication: (id: number, body: Partial<ApplicationRow>) =>
    request<ApplicationRow>(`/api/applications/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteApplication: (id: number) =>
    request<void>(`/api/applications/${id}`, { method: "DELETE" }),

  // --- flow two: the composer --------------------------------------------
  forkVariant: (applicationId: number, body: { base_resume_id: number; title?: string }) =>
    request<VariantDetail>(`/api/applications/${applicationId}/variant`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  variant: (id: number) => request<VariantDetail>(`/api/variants/${id}`),
  saveVariant: (id: number, body: { title?: string; data: ResumeJSON }) =>
    request<VariantDetail>(`/api/variants/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  async exportVariant(id: number): Promise<{ blob: Blob; filename: string }> {
    const res = await fetch(`/api/variants/${id}/export`, { method: "POST" });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        detail = (await res.json())?.detail ?? detail;
      } catch {
        // keep statusText
      }
      throw new ApiError(res.status, detail);
    }
    const disposition = res.headers.get("Content-Disposition") ?? "";
    const match = /filename="?([^"]+)"?/.exec(disposition);
    return { blob: await res.blob(), filename: match?.[1] ?? "resume.pdf" };
  },

  // --- recommended reading ------------------------------------------------
  courseIndex: () => request<CourseIndex>("/api/courses"),
  refreshCourses: () =>
    request<CourseIndex>("/api/courses/refresh", { method: "POST" }),
  reading: (applicationId: number) =>
    request<ReadingList>(`/api/applications/${applicationId}/reading`),
  runReading: (applicationId: number) =>
    request<ReadingList>(`/api/applications/${applicationId}/reading`, {
      method: "POST",
    }),

  // --- reusable items -----------------------------------------------------
  listLibrary: () => request<LibraryRow[]>("/api/library"),
  addLibraryItem: (body: { label: string; section_kind: string; data: Item }) =>
    request<LibraryRow>("/api/library", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  libraryInstance: (id: number) => request<Item>(`/api/library/${id}/instance`),
  deleteLibraryItem: (id: number) =>
    request<void>(`/api/library/${id}`, { method: "DELETE" }),
};

/** Client-side ids for nodes the user adds; the server keeps whatever it gets. */
export function newId(): string {
  return Math.random().toString(16).slice(2, 10) + Date.now().toString(16).slice(-4);
}

export function emptyItem(): Item {
  return {
    id: newId(),
    include: true,
    title: "",
    subtitle: "",
    location: "",
    start: "",
    end: "",
    current: false,
    url: "",
    description: "",
    bullets: [],
    tags: [],
  };
}

export function emptySection(kind: SectionKind = "custom"): Section {
  const titles: Record<SectionKind, string> = {
    experience: "Experience",
    projects: "Projects",
    education: "Education",
    skills: "Skills",
    certifications: "Certifications",
    awards: "Awards",
    publications: "Publications",
    custom: "Section",
  };
  return { id: newId(), kind, title: titles[kind], include: true, items: [] };
}
