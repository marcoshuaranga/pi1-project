import { Link, Route, Routes } from "react-router-dom";
import OperatorPage from "./pages/OperatorPage";
import ExpertPage from "./pages/ExpertPage";
import DashboardPage from "./pages/DashboardPage";
import DocsPage from "./pages/DocsPage";

export default function App() {
  return (
    <div className="min-h-screen bg-base-200">
      <div className="bg-base-100 shadow-sm px-4 py-2 flex gap-4">
        <Link to="/" className="btn btn-ghost btn-sm">Operador</Link>
        <Link to="/experto" className="btn btn-ghost btn-sm">Experto KEDB</Link>
        <Link to="/docs" className="btn btn-ghost btn-sm">Live Docs</Link>
        <Link to="/dashboard" className="btn btn-ghost btn-sm">Coordinador</Link>
      </div>
      <Routes>
        <Route path="/" element={<OperatorPage />} />
        <Route path="/experto" element={<ExpertPage />} />
        <Route path="/kedb" element={<ExpertPage />} />
        <Route path="/docs" element={<DocsPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Routes>
    </div>
  );
}
