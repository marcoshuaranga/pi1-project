import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useBlocker, useLocation } from "react-router-dom";

type PipelineNavContextValue = {
  pipelineBusy: boolean;
  setPipelineBusy: (busy: boolean) => void;
};

const PipelineNavContext = createContext<PipelineNavContextValue | null>(null);

export function usePipelineNavGuard() {
  const ctx = useContext(PipelineNavContext);
  if (!ctx) {
    throw new Error("usePipelineNavGuard must be used within App");
  }
  return ctx;
}

const LEAVE_MSG =
  "El pipeline sigue ejecutándose. Si sales, puedes volver después para ver el resultado. ¿Cambiar de página?";

function navClass(isActive: boolean) {
  return `app-nav-link ${isActive ? "app-nav-link-active" : ""}`;
}

type Theme = "light" | "dark";
const THEME_KEY = "oitsi-theme";

export default function App() {
  const [pipelineBusy, setPipelineBusy] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => localStorage.getItem("oitsi-sidebar-collapsed") === "true"
  );
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem(THEME_KEY);
    return saved === "dark" ? "dark" : "light";
  });
  const location = useLocation();
  const value = useMemo(
    () => ({ pipelineBusy, setPipelineBusy }),
    [pipelineBusy]
  );

  const blocker = useBlocker(
    useCallback(
      ({
        currentLocation,
        nextLocation,
      }: {
        currentLocation: { pathname: string };
        nextLocation: { pathname: string };
      }) => {
        if (!pipelineBusy) return false;
        if (currentLocation.pathname === nextLocation.pathname) return false;
        // Moving between the new-ticket form and any /tickets/:id page is how
        // multiple tickets get tracked at once — each keeps running server-side
        // regardless of which one is currently in view, so don't warn for this.
        const isOperatorPath = (p: string) => p === "/" || p.startsWith("/tickets/");
        if (isOperatorPath(currentLocation.pathname) && isOperatorPath(nextLocation.pathname)) {
          return false;
        }
        return true;
      },
      [pipelineBusy]
    )
  );

  // Una sola confirmación para navegación interna (no repetir con beforeunload).
  useEffect(() => {
    if (blocker.state !== "blocked") return;
    const ok = window.confirm(LEAVE_MSG);
    if (ok) blocker.proceed();
    else blocker.reset();
  }, [blocker]);

  // Cierre/recarga de pestaña: el navegador muestra su propio diálogo (una vez).
  useEffect(() => {
    if (!pipelineBusy) return;
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [pipelineBusy]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  const toggleTheme = () => setTheme((current) => (current === "light" ? "dark" : "light"));
  const toggleSidebar = () => {
    setSidebarCollapsed((current) => {
      const next = !current;
      localStorage.setItem("oitsi-sidebar-collapsed", String(next));
      return next;
    });
  };

  return (
    <PipelineNavContext.Provider value={value}>
      <div className={`app-shell ${sidebarCollapsed ? "app-shell-collapsed" : ""}`}>
        <button
          type="button"
          className={`app-nav-backdrop ${mobileNavOpen ? "app-nav-backdrop-visible" : ""}`}
          onClick={() => setMobileNavOpen(false)}
          aria-label="Cerrar navegación"
        />
        <aside className={`app-sidebar ${mobileNavOpen ? "app-sidebar-mobile-open" : ""}`}>
          <div className="app-brand">
            <div className="app-brand-mark">O</div>
            <div>
              <p className="app-brand-name">OITSI</p>
              <p className="app-brand-subtitle">Mesa de ayuda inteligente</p>
            </div>
          </div>

          <div className="app-sidebar-heading">
            <div className="app-sidebar-label">Espacios de trabajo</div>
            <button
              type="button"
              className="sidebar-collapse-button"
              onClick={toggleSidebar}
              aria-label={sidebarCollapsed ? "Expandir barra lateral" : "Contraer barra lateral"}
              title={sidebarCollapsed ? "Expandir barra lateral" : "Contraer barra lateral"}
            >
              <span className={`sidebar-collapse-icon ${sidebarCollapsed ? "is-collapsed" : ""}`} />
            </button>
          </div>
          <nav className="app-nav" aria-label="Navegación principal">
            <NavLink
              to="/whatsapp"
              className={({ isActive }) => navClass(isActive)}
              onClick={() => setMobileNavOpen(false)}
            >
              <span className="app-nav-icon">◉</span>
              <span>WhatsApp</span>
              <span className="app-nav-arrow">›</span>
            </NavLink>
            <NavLink
              to="/"
              className={() =>
                navClass(location.pathname === "/" || location.pathname.startsWith("/tickets/"))
              }
              onClick={() => setMobileNavOpen(false)}
            >
              <span className="app-nav-icon">⌁</span>
              <span>Operador</span>
              <span className="app-nav-arrow">›</span>
            </NavLink>
            <NavLink
              to="/experto"
              className={() =>
                navClass(location.pathname === "/experto" || location.pathname === "/kedb")
              }
              onClick={() => setMobileNavOpen(false)}
            >
              <span className="app-nav-icon">✦</span>
              <span>Experto KEDB</span>
              <span className="app-nav-arrow">›</span>
            </NavLink>
            <NavLink to="/docs" className={({ isActive }) => navClass(isActive)} onClick={() => setMobileNavOpen(false)}>
              <span className="app-nav-icon">▤</span>
              <span>Live Docs</span>
              <span className="app-nav-arrow">›</span>
            </NavLink>
            <NavLink to="/dashboard" className={({ isActive }) => navClass(isActive)} onClick={() => setMobileNavOpen(false)}>
              <span className="app-nav-icon">◒</span>
              <span>Coordinador</span>
              <span className="app-nav-arrow">›</span>
            </NavLink>
          </nav>

          <div className="app-sidebar-footer">
            <button type="button" className="theme-toggle" onClick={toggleTheme}>
              <span className="theme-toggle-icon">{theme === "light" ? "☾" : "☀"}</span>
              <span>{theme === "light" ? "Modo oscuro" : "Modo claro"}</span>
              <span className="theme-toggle-state">{theme === "light" ? "OFF" : "ON"}</span>
            </button>
            <div className="app-system-status">
              <span className="app-status-dot" />
              <div>
                <p>Sistema operativo</p>
                <span>Todos los servicios activos</span>
              </div>
            </div>
            <p className="app-version">RAG + KEDB · v0.1</p>
          </div>
        </aside>

        <main className="app-main">
          <header className="app-mobile-header">
            <button
              type="button"
              className="mobile-menu-toggle"
              onClick={() => setMobileNavOpen(true)}
              aria-label="Abrir navegación"
            >
              ☰
            </button>
            <div className="app-brand">
              <div className="app-brand-mark">O</div>
              <div>
                <p className="app-brand-name">OITSI</p>
                <p className="app-brand-subtitle">Mesa de ayuda</p>
              </div>
            </div>
            <div className="app-mobile-actions">
              <button type="button" className="mobile-theme-toggle" onClick={toggleTheme} aria-label="Cambiar tema">
                {theme === "light" ? "☾" : "☀"}
              </button>
              <span className="app-status-pill"><span className="app-status-dot" /> En línea</span>
            </div>
          </header>
          <div className="app-content">
            <Outlet />
          </div>
        </main>
      </div>
    </PipelineNavContext.Provider>
  );
}
