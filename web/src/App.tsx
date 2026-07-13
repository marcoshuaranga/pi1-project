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

function navClass(isActive: boolean, activeTone: string) {
  return `btn btn-sm ${isActive ? activeTone : "btn-ghost"}`;
}

export default function App() {
  const [pipelineBusy, setPipelineBusy] = useState(false);
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
      }) => pipelineBusy && currentLocation.pathname !== nextLocation.pathname,
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

  return (
    <PipelineNavContext.Provider value={value}>
      <div className="min-h-screen bg-base-200">
        <div className="bg-base-100 shadow-sm px-4 py-2 flex flex-wrap justify-center gap-2 sm:gap-4">
          <NavLink to="/" end className={({ isActive }) => navClass(isActive, "btn-primary")}>
            Operador
          </NavLink>
          <NavLink
            to="/experto"
            className={() =>
              navClass(
                location.pathname === "/experto" || location.pathname === "/kedb",
                "btn-secondary"
              )
            }
          >
            Experto KEDB
          </NavLink>
          <NavLink to="/docs" className={({ isActive }) => navClass(isActive, "btn-accent")}>
            Live Docs
          </NavLink>
          <NavLink
            to="/dashboard"
            className={({ isActive }) => navClass(isActive, "btn-neutral")}
          >
            Coordinador
          </NavLink>
        </div>
        <Outlet />
      </div>
    </PipelineNavContext.Provider>
  );
}
