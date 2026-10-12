import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import { useDashboardEnabled } from "./featureFlags";
import App from "./App";
import OperatorPage from "./pages/OperatorPage";
import ExpertPage from "./pages/ExpertPage";
import DashboardPage from "./pages/DashboardPage";
import DocsPage from "./pages/DocsPage";
import WhatsAppPage from "./pages/WhatsAppPage";
import "./index.css";

// ADR-0011: la ruta del tablero se oculta solo si HU15, HU16 y HU17 están apagadas.
function DashboardRoute() {
  return useDashboardEnabled() ? <DashboardPage /> : <Navigate to="/" replace />;
}

const router =createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <OperatorPage /> },
      { path: "tickets/:ticketId", element: <OperatorPage /> },
      { path: "whatsapp", element: <WhatsAppPage /> },
      { path: "experto", element: <ExpertPage /> },
      { path: "kedb", element: <ExpertPage /> },
      { path: "docs", element: <DocsPage /> },
      { path: "dashboard", element: <DashboardRoute /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
