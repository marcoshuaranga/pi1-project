import { useState } from "react";
import { api, processTicketViaWs, TicketResponse } from "../api";

const STEPS = [
  "C1 Anonimización",
  "C3 Clasificación",
  "C4 Priorización",
  "C5 Recuperación RAG",
];

/** Map orchestrator agent names to step index (inicio/fin). */
function stepIndexForAgent(agente?: string): number {
  switch (agente) {
    case "Orquestador":
      return 0; // C1 runs under orquestador start / anonymize
    case "Clasificador":
      return 1;
    case "Priorizador":
      return 2;
    case "RAG":
      return 3;
    default:
      return -1;
  }
}

export default function OperatorPage() {
  const [texto, setTexto] = useState(
    "Impresora Kyocera 7003 no imprime, necesito que la configuren de nuevo"
  );
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TicketResponse | null>(null);
  const [activeStep, setActiveStep] = useState(-1);
  const [error, setError] = useState("");
  const [correccion, setCorreccion] = useState("");
  const [feedbackMsg, setFeedbackMsg] = useState("");
  const [nuevaSolucion, setNuevaSolucion] = useState("");
  const [viaWs, setViaWs] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    setResult(null);
    setActiveStep(0);
    setViaWs(false);
    setFeedbackMsg("");
    try {
      const res = await processTicketViaWs(texto, {
        onEvent: (evento) => {
          if (evento.tipo === "inicio" || evento.tipo === "fin") {
            const idx = stepIndexForAgent(evento.agente);
            if (idx >= 0) {
              setActiveStep((prev) => Math.max(prev, idx));
            }
          }
        },
      });
      setViaWs(true);
      setResult(res);
      setActiveStep(STEPS.length);
    } catch {
      try {
        // Fallback REST so the demo does not fail if WS is unavailable
        setActiveStep(0);
        const res = await api.submitTicket(texto);
        setResult(res);
        setActiveStep(STEPS.length);
        setViaWs(false);
      } catch (e) {
        setError(String(e));
        setActiveStep(-1);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCorreccion = async () => {
    if (!result || !correccion) return;
    await api.correctCategoria(result.ticket_id, correccion);
    setResult({ ...result, categoria: correccion });
    setCorreccion("");
  };

  const handleFeedback = async (articuloId: string, util: boolean) => {
    if (!result) return;
    await api.feedback(result.ticket_id, { articulo_id: articuloId, util });
    setFeedbackMsg(util ? "¡Gracias por tu retroalimentación!" : "Registrado.");
  };

  const handleNuevaSolucion = async () => {
    if (!result || !nuevaSolucion) return;
    await api.feedback(result.ticket_id, { nueva_solucion: nuevaSolucion });
    setFeedbackMsg("Nueva solución registrada como candidata KEDB (HU12).");
    setNuevaSolucion("");
  };

  return (
    <div className="max-w-5xl mx-auto p-4">
      <div className="navbar bg-primary text-primary-content rounded-lg mb-4 px-4 shadow">
        <span className="text-lg font-bold">Mesa de Ayuda OITSI-MTC</span>
        <span className="ml-4 badge badge-accent">Asistente IA activo</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card bg-base-100 shadow">
          <div className="card-body">
            <h2 className="card-title text-sm">Nuevo ticket</h2>
            <textarea
              className="textarea textarea-bordered w-full h-32"
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              placeholder="Describe el problema del usuario..."
            />
            <button
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={loading || texto.length < 5}
            >
              {loading ? "Procesando..." : "Enviar ticket"}
            </button>
            {error && <p className="text-error text-sm">{error}</p>}
          </div>
        </div>

        <div className="card bg-base-100 shadow border-l-4 border-primary">
          <div className="card-body">
            <h2 className="card-title text-sm text-primary">Estado del pipeline (C7)</h2>
            <ul className="steps steps-vertical text-xs">
              {STEPS.map((step, i) => (
                <li
                  key={step}
                  className={`step ${i <= activeStep ? "step-primary" : ""}`}
                >
                  {step}
                </li>
              ))}
            </ul>
            {result && (
              <p className="text-xs text-base-content/50 mt-2">
                {viaWs ? "Eventos en vivo vía WebSocket" : "Procesado vía REST (fallback)"}
              </p>
            )}
          </div>
        </div>
      </div>

      {result && (
        <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="card bg-base-100 shadow border-l-4 border-info">
            <div className="card-body">
              <h2 className="card-title text-sm text-info">Sugerencias del Agente IA</h2>
              <p className="text-xs text-base-content/60">Ticket: {result.ticket_id}</p>

              <div className="mt-2">
                <p className="text-xs font-semibold uppercase text-base-content/60">Clasificación (C3)</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="badge badge-info">{result.categoria}</span>
                  <span className="text-xs">confianza {(result.confianza * 100).toFixed(0)}%</span>
                </div>
              </div>

              <div className="mt-3">
                <p className="text-xs font-semibold uppercase text-base-content/60">Prioridad (C4)</p>
                <span className="badge badge-warning mt-1">{result.prioridad}</span>
                {result.justificacion_prioridad && (
                  <div className="text-xs mt-2 text-base-content/70">
                    {Object.entries(result.justificacion_prioridad).map(([k, v]) => (
                      <div key={k}>{k}: {(v * 100).toFixed(0)}%</div>
                    ))}
                  </div>
                )}
              </div>

              <div className="mt-3 flex gap-2">
                <input
                  className="input input-bordered input-sm flex-1"
                  placeholder="Corregir categoría (HU03)"
                  value={correccion}
                  onChange={(e) => setCorreccion(e.target.value)}
                />
                <button className="btn btn-sm btn-outline" onClick={handleCorreccion}>
                  Corregir
                </button>
              </div>
            </div>
          </div>

          <div className="card bg-base-100 shadow border-l-4 border-success">
            <div className="card-body">
              <h2 className="card-title text-sm text-success">Top-5 Soluciones (C5 RAG)</h2>
              {result.soluciones.length === 0 ? (
                <p className="text-sm text-base-content/60">Sin soluciones similares encontradas.</p>
              ) : (
                <div className="space-y-3">
                  {result.soluciones.map((s) => (
                    <div key={s.articulo_o_ticket_id} className="border rounded-lg p-3 text-sm">
                      <div className="flex justify-between items-center">
                        <span className="badge badge-ghost badge-sm">{s.tipo}</span>
                        <span className="text-xs font-mono">similitud {(s.score * 100).toFixed(0)}%</span>
                      </div>
                      <p className="font-medium mt-1">{s.titulo || s.articulo_o_ticket_id}</p>
                      <p className="text-base-content/70 mt-1 text-xs">{s.solucion}</p>
                      <div className="flex gap-2 mt-2">
                        <button
                          className="btn btn-xs btn-success"
                          onClick={() => handleFeedback(s.articulo_o_ticket_id, true)}
                        >
                          Útil (HU11)
                        </button>
                        <button
                          className="btn btn-xs btn-ghost"
                          onClick={() => handleFeedback(s.articulo_o_ticket_id, false)}
                        >
                          No útil
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {feedbackMsg && <p className="text-success text-xs mt-2">{feedbackMsg}</p>}
              <div className="mt-4 border-t pt-3">
                <p className="text-xs font-semibold">Nueva solución (HU12)</p>
                <textarea
                  className="textarea textarea-bordered textarea-sm w-full mt-1"
                  placeholder="Documentar solución no sugerida..."
                  value={nuevaSolucion}
                  onChange={(e) => setNuevaSolucion(e.target.value)}
                />
                <button className="btn btn-xs btn-outline mt-1" onClick={handleNuevaSolucion}>
                  Registrar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
