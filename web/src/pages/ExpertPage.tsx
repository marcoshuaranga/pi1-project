import { useEffect, useState } from "react";
import { api, KedbArticulo } from "../api";
import { useJobRun } from "../useJobRun";

type EditDraft = {
  titulo: string;
  sintoma: string;
  causa: string;
  solucion: string;
  aplicable_a: string;
};

function draftFromArticulo(a: KedbArticulo): EditDraft {
  return {
    titulo: a.titulo,
    sintoma: a.sintoma,
    causa: a.causa,
    solucion: a.solucion,
    aplicable_a: a.aplicable_a ?? "",
  };
}

export default function ExpertPage() {
  const [pendientes, setPendientes] = useState<KedbArticulo[]>([]);
  const [selected, setSelected] = useState<KedbArticulo | null>(null);
  const [loading, setLoading] = useState(true);
  const [deciding, setDeciding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<EditDraft | null>(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const jobRun = useJobRun();

  const load = async (opts?: { preferId?: string | null }) => {
    setLoading(true);
    setError("");
    try {
      const list = await api.getPendientes();
      setPendientes(list);
      setSelected((prev) => {
        if (!list.length) return null;
        const prefer = opts?.preferId;
        if (prefer && list.some((a) => a.articulo_id === prefer)) {
          return list.find((a) => a.articulo_id === prefer) ?? list[0];
        }
        if (prev && list.some((a) => a.articulo_id === prev.articulo_id)) {
          return list.find((a) => a.articulo_id === prev.articulo_id) ?? list[0];
        }
        return list[0];
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    return () => jobRun.cancel();
  }, []);

  const selectArticulo = (a: KedbArticulo) => {
    setSelected(a);
    setEditing(false);
    setDraft(null);
    setMsg("");
  };

  const startEdit = () => {
    if (!selected) return;
    setDraft(draftFromArticulo(selected));
    setEditing(true);
    setMsg("");
    setError("");
  };

  const cancelEdit = () => {
    setEditing(false);
    setDraft(null);
  };

  const removeFromPendientes = (articuloId: string) => {
    setPendientes((list) => {
      const next = list.filter((a) => a.articulo_id !== articuloId);
      setSelected((prev) => {
        if (prev?.articulo_id !== articuloId) return prev;
        return next[0] ?? null;
      });
      return next;
    });
    setEditing(false);
    setDraft(null);
  };

  const syncPendiente = (updated: KedbArticulo) => {
    setPendientes((list) =>
      list.map((a) => (a.articulo_id === updated.articulo_id ? updated : a))
    );
    setSelected(updated);
  };

  const handleSaveEdit = async () => {
    if (!selected || !draft || saving) return;
    const titulo = draft.titulo.trim();
    const sintoma = draft.sintoma.trim();
    const causa = draft.causa.trim();
    const solucion = draft.solucion.trim();
    if (!titulo || !sintoma || !causa || !solucion) {
      setError("Título, síntoma, causa y solución son obligatorios.");
      return;
    }
    setError("");
    setSaving(true);
    try {
      const updated = await api.updateArticulo(selected.articulo_id, {
        titulo,
        sintoma,
        causa,
        solucion,
        aplicable_a: draft.aplicable_a.trim() || undefined,
      });
      syncPendiente(updated);
      setEditing(false);
      setDraft(null);
      setMsg(`Cambios guardados en «${updated.titulo}» (sigue en borrador).`);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleGenerate = async () => {
    setError("");
    setMsg("");
    try {
      const done = await jobRun.run(() => api.enqueueKedbGenerate(10), "Encolando generación KEDB…");
      if (!done) return; // cancelled by a newer run or unmount
      if (done.success === false) {
        throw new Error(done.error || "La generación falló en el worker");
      }
      const generated =
        done.result && typeof done.result === "object" && "generated" in done.result
          ? Number((done.result as { generated: number }).generated)
          : undefined;
      setMsg(
        generated != null
          ? `Generación lista: ${generated} artículo(s).`
          : "Generación KEDB completada."
      );
      await load();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleApprove = async () => {
    if (!selected || deciding || editing) return;
    const current = selected;
    setError("");
    setDeciding(true);
    try {
      const updated = await api.approveArticulo(current.articulo_id);
      removeFromPendientes(current.articulo_id);
      setMsg(
        `«${updated.titulo}» aprobado (estado: ${updated.estado}). Ya está indexado para RAG y disponible en Live Docs.`
      );
    } catch (e) {
      setError(String(e));
      await load({ preferId: current.articulo_id });
    } finally {
      setDeciding(false);
    }
  };

  const handleReject = async () => {
    if (!selected || deciding || editing) return;
    const current = selected;
    setError("");
    setDeciding(true);
    try {
      await api.rejectArticulo(current.articulo_id);
      removeFromPendientes(current.articulo_id);
      setMsg(`«${current.titulo}» rechazado (estado: obsoleto).`);
    } catch (e) {
      setError(String(e));
      await load({ preferId: current.articulo_id });
    } finally {
      setDeciding(false);
    }
  };

  const emptyPendientes = !loading && pendientes.length === 0 && !error;
  const busy = deciding || saving || jobRun.busy;

  return (
    <div className="max-w-5xl mx-auto p-4">
      <div className="navbar page-header bg-secondary text-secondary-content rounded-lg mb-4 px-4 shadow flex-wrap gap-2">
        <span className="text-lg font-bold">Validación KEDB — Experto Técnico</span>
        <span className="badge badge-warning">{pendientes.length} pendientes</span>
        <div className="ml-auto">
          <button
            type="button"
            className="btn btn-sm btn-primary"
            onClick={handleGenerate}
            disabled={busy}
          >
            {jobRun.busy ? (
              <>
                <span className="loading loading-spinner loading-xs" />
                Generando…
              </>
            ) : (
              "Generar borradores (worker)"
            )}
          </button>
        </div>
      </div>

      {jobRun.status && (
        <div className="alert alert-info mb-4 text-sm">
          <span>{jobRun.status}</span>
        </div>
      )}

      {msg && (
        <div className="alert alert-success mb-4 text-sm">
          <span>{msg}</span>
          <button type="button" className="btn btn-sm btn-ghost" onClick={() => setMsg("")}>
            Cerrar
          </button>
        </div>
      )}

      {error && (
        <div className="alert alert-error mb-4 text-sm">
          <span>{error}</span>
          <button type="button" className="btn btn-sm" onClick={() => load()}>
            Reintentar
          </button>
        </div>
      )}

      {loading && pendientes.length === 0 ? (
        <div className="flex items-center gap-2 text-sm">
          <span className="loading loading-spinner" />
          Cargando pendientes desde la API…
        </div>
      ) : emptyPendientes ? (
        <div className="alert alert-info">
          <div>
            <p className="font-medium">No hay artículos pendientes de validación.</p>
            <p className="text-sm opacity-80 mt-1">
              Si acabas de aprobar uno, ya salió de esta bandeja. Puedes continuar en{" "}
              <strong>Operador</strong> (Escena 3) o en <strong>Live Docs</strong>.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
          <div className="col-span-1 self-start w-full">
            <div className="card bg-base-100 shadow">
              <div className="card-body gap-2 p-4 !flex-none">
                <h3 className="font-semibold text-sm">Pendientes (HU14)</h3>
                <ul className="menu menu-sm w-full">
                  {pendientes.map((a) => (
                    <li key={a.articulo_id}>
                      <button
                        type="button"
                        className={selected?.articulo_id === a.articulo_id ? "active" : ""}
                        onClick={() => selectArticulo(a)}
                        disabled={busy}
                      >
                        <span className="text-left whitespace-normal leading-snug">
                          {a.titulo.length > 60 ? `${a.titulo.slice(0, 60)}…` : a.titulo}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {selected ? (
            <div className="col-span-1 lg:col-span-2 card bg-base-100 shadow self-start w-full">
              <div className="card-body gap-3 p-4 !flex-none">
                <div className="flex flex-wrap items-start gap-2">
                  {editing && draft ? (
                    <input
                      className="input input-bordered input-sm flex-1 min-w-0"
                      value={draft.titulo}
                      onChange={(e) => setDraft({ ...draft, titulo: e.target.value })}
                      disabled={saving}
                      aria-label="Título"
                    />
                  ) : (
                    <h2 className="card-title text-base leading-snug flex-1 min-w-0">
                      {selected.titulo}
                    </h2>
                  )}
                  <span className="badge badge-warning badge-sm shrink-0">{selected.estado}</span>
                </div>
                <div className="divider my-0" />

                <section>
                  <h4 className="font-semibold text-sm">Síntoma</h4>
                  {editing && draft ? (
                    <textarea
                      className="textarea textarea-bordered textarea-sm w-full mt-1 min-h-20"
                      value={draft.sintoma}
                      onChange={(e) => setDraft({ ...draft, sintoma: e.target.value })}
                      disabled={saving}
                    />
                  ) : (
                    <p className="text-sm mt-1">{selected.sintoma}</p>
                  )}
                </section>
                <section>
                  <h4 className="font-semibold text-sm">Causa probable</h4>
                  {editing && draft ? (
                    <textarea
                      className="textarea textarea-bordered textarea-sm w-full mt-1 min-h-20"
                      value={draft.causa}
                      onChange={(e) => setDraft({ ...draft, causa: e.target.value })}
                      disabled={saving}
                    />
                  ) : (
                    <p className="text-sm mt-1">{selected.causa}</p>
                  )}
                </section>
                <section>
                  <h4 className="font-semibold text-sm">Solución</h4>
                  {editing && draft ? (
                    <textarea
                      className="textarea textarea-bordered textarea-sm w-full mt-1 min-h-28"
                      value={draft.solucion}
                      onChange={(e) => setDraft({ ...draft, solucion: e.target.value })}
                      disabled={saving}
                    />
                  ) : (
                    <p className="text-sm whitespace-pre-line mt-1">{selected.solucion}</p>
                  )}
                </section>
                <section>
                  <h4 className="font-semibold text-sm">Aplicable a</h4>
                  {editing && draft ? (
                    <input
                      className="input input-bordered input-sm w-full mt-1"
                      value={draft.aplicable_a}
                      onChange={(e) => setDraft({ ...draft, aplicable_a: e.target.value })}
                      disabled={saving}
                      placeholder="Opcional"
                    />
                  ) : (
                    <p className="text-sm mt-1 text-base-content/80">
                      {selected.aplicable_a || "—"}
                    </p>
                  )}
                </section>
                <section>
                  <h4 className="font-semibold text-sm">Trazabilidad N:1 (HU09)</h4>
                  <p className="text-sm mt-1">
                    <span className="badge badge-primary">
                      {selected.tickets_fuente.length} tickets fuente
                    </span>
                  </p>
                  <p className="text-xs font-mono text-base-content/70 mt-2 break-all">
                    {selected.tickets_fuente.slice(0, 20).join(", ")}
                    {selected.tickets_fuente.length > 20 &&
                      ` … (+${selected.tickets_fuente.length - 20} más)`}
                  </p>
                </section>

                <div className="flex flex-wrap justify-end gap-2 mt-2">
                  {editing ? (
                    <>
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={cancelEdit}
                        disabled={saving}
                      >
                        Cancelar
                      </button>
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        onClick={handleSaveEdit}
                        disabled={saving}
                      >
                        {saving ? (
                          <>
                            <span className="loading loading-spinner loading-xs" />
                            Guardando…
                          </>
                        ) : (
                          "Guardar cambios"
                        )}
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        className="btn btn-outline btn-sm"
                        onClick={startEdit}
                        disabled={busy}
                      >
                        Editar (HU10)
                      </button>
                      <button
                        type="button"
                        className="btn btn-error btn-sm"
                        onClick={handleReject}
                        disabled={busy}
                      >
                        {deciding ? (
                          <span className="loading loading-spinner loading-xs" />
                        ) : (
                          "Rechazar"
                        )}
                      </button>
                      <button
                        type="button"
                        className="btn btn-success btn-sm"
                        onClick={handleApprove}
                        disabled={busy}
                      >
                        {deciding ? (
                          <>
                            <span className="loading loading-spinner loading-xs" />
                            Aprobando…
                          </>
                        ) : (
                          "Aprobar (HU10)"
                        )}
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="col-span-1 lg:col-span-2 alert self-start">
              Selecciona un artículo de la lista para revisarlo.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
