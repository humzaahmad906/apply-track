import { useEffect, useState } from "react";
import { Navigate, NavLink, Route, Routes, useParams } from "react-router-dom";

import { Board, Gear, Layers, Moon, Sun } from "./icons";
import Composer from "./pages/Composer";
import Dashboard from "./pages/Dashboard";
import JobPage from "./pages/JobPage";
import Material from "./pages/Material";
import ResumeEditor from "./pages/ResumeEditor";
import Settings from "./pages/Settings";

function NotFound() {
  return (
    <div className="page">
      <div className="empty">Nothing here.</div>
    </div>
  );
}

/** Links from the previous layout still land somewhere sensible. */
function ToJob({ suffix = "" }: { suffix?: string }) {
  const { applicationId } = useParams();
  return <Navigate to={`/jobs/${applicationId}${suffix}`} replace />;
}

const active = ({ isActive }: { isActive: boolean }) => (isActive ? "active" : "");

type Theme = "light" | "dark";

/** Remembers your choice; falls back to what the system already prefers. */
function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem("apply-track-theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("apply-track-theme", theme);
  }, [theme]);

  return [theme, () => setTheme((t) => (t === "dark" ? "light" : "dark"))];
}

export default function App() {
  const [theme, toggleTheme] = useTheme();

  return (
    <div className="app">
      <div className="topbar">
        <span className="brand">apply&#8209;track</span>
        <nav>
          <NavLink to="/" end className={active}>
            <Board size={15} />
            Dashboard
          </NavLink>
          <NavLink to="/material" className={active}>
            <Layers size={15} />
            Material
          </NavLink>
        </nav>
        <span className="spacer" />
        <button
          type="button"
          className="icon"
          onClick={toggleTheme}
          title={theme === "dark" ? "Switch to light" : "Switch to dark"}
          aria-label={theme === "dark" ? "Switch to light" : "Switch to dark"}
        >
          {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
        </button>
        {/* The machinery lives behind the gear. It should never be the first
            thing you notice. */}
        <NavLink to="/settings" className={active} title="Settings">
          <Gear size={17} />
        </NavLink>
      </div>

      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/jobs/:applicationId" element={<JobPage />} />
          <Route path="/jobs/:applicationId/resume" element={<Composer />} />

          <Route path="/material" element={<Material />} />
          <Route
            path="/material/review/:jobId"
            element={<ResumeEditor mode="review" />}
          />
          <Route
            path="/material/:resumeId/edit"
            element={<ResumeEditor mode="edit" />}
          />

          <Route path="/settings" element={<Settings />} />

          {/* The previous layout's routes. */}
          <Route path="/applications" element={<Navigate to="/" replace />} />
          <Route path="/applications/:applicationId" element={<ToJob />} />
          <Route
            path="/applications/:applicationId/compose"
            element={<ToJob suffix="/resume" />}
          />
          <Route path="/resumes" element={<Navigate to="/material" replace />} />
          <Route
            path="/resumes/review/:jobId"
            element={<ResumeEditor mode="review" />}
          />
          <Route
            path="/resumes/:resumeId/edit"
            element={<ResumeEditor mode="edit" />}
          />
          <Route path="/library" element={<Navigate to="/material" replace />} />

          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  );
}
