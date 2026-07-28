import { useQuery } from "@tanstack/react-query";
import { NavLink, Route, Routes } from "react-router-dom";

import { api } from "./api/client";
import Applications from "./pages/Applications";
import Composer from "./pages/Composer";
import Library from "./pages/Library";
import ResumeEditor from "./pages/ResumeEditor";
import Resumes from "./pages/Resumes";

function NotFound() {
  return (
    <div className="page">
      <div className="empty">Nothing here.</div>
    </div>
  );
}

export default function App() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });

  return (
    <div className="app">
      <div className="topbar">
        <span className="brand">apply-track</span>
        {/* Ordered as the two flows actually run: parse a base resume once,
            then compose one tailored variant per application. */}
        <nav>
          <NavLink
            to="/resumes"
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            1 · Base resumes
          </NavLink>
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            2 · Applications &amp; JDs
          </NavLink>
          <NavLink
            to="/library"
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            Library
          </NavLink>
        </nav>
        <span className="spacer" />
        {health.data && !health.data.claude_cli && (
          <span className="pill" title={health.data.claude_cli_error}>
            CLI missing
          </span>
        )}
        {health.data && !health.data.pdf_export && (
          <span className="pill" title={health.data.pdf_export_error}>
            PDF export off
          </span>
        )}
      </div>

      <main>
        <Routes>
          <Route path="/" element={<Applications />} />
          <Route path="/resumes" element={<Resumes />} />
          <Route path="/library" element={<Library />} />
          <Route path="/resumes/review/:jobId" element={<ResumeEditor mode="review" />} />
          <Route path="/resumes/:resumeId/edit" element={<ResumeEditor mode="edit" />} />
          <Route path="/applications/:applicationId/compose" element={<Composer />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  );
}
