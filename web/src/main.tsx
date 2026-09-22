import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import App from "./App";
import OperatorPage from "./pages/OperatorPage";
import ExpertPage from "./pages/ExpertPage";
import DashboardPage from "./pages/DashboardPage";
import DocsPage from "./pages/DocsPage";
import WhatsAppPage from "./pages/WhatsAppPage";
import "./index.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <OperatorPage /> },
      { path: "whatsapp", element: <WhatsAppPage /> },
      { path: "experto", element: <ExpertPage /> },
      { path: "kedb", element: <ExpertPage /> },
      { path: "docs", element: <DocsPage /> },
      { path: "dashboard", element: <DashboardPage /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
