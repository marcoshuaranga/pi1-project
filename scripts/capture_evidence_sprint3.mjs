// Genera las capturas de docs/evidence/sprint3/ contra el stack levantado (web :5173, api :8000).
//
// Requisitos: `playwright-core` (no es dependencia del repo: instálalo en un directorio temporal) y Chrome.
// Los tickets usados salen de `POST /tickets` reales; el único caso sembrado es "sin factores"
// (scripts/seed_evidence_sprint3.py). Ver docs/evidence/sprint3/README.md.
//
//   cd <dir con playwright-core instalado> && node <repo>/scripts/capture_evidence_sprint3.mjs <repo>/docs/evidence/sprint3
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(path.join(process.cwd(), "/"));
const { chromium } = require("playwright-core");

const WEB = process.env.WEB_URL ?? "http://localhost:5173";
const API = process.env.API_URL ?? "http://localhost:8000";
const OUT = path.resolve(process.argv[2] ?? "docs/evidence/sprint3");
const CHROME = process.env.CHROME_PATH ?? "C:/Program Files/Google/Chrome/Application/chrome.exe";

const post = async (url, body) => {
  const r = await fetch(API + url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  return r.json();
};

// Tickets reales vía API (texto → confianza observada: 0.45 / 0.99).
const bajo = await post("/tickets", { texto: "revisar cosas pendientes de la oficina" });
if (!bajo.confianza_baja) throw new Error(`se esperaba confianza baja, llegó ${bajo.confianza}`);
const normal = await post("/tickets", { texto: "Impresora Kyocera atascada con papel" });
const SIN_FACTORES = "T-EVID0001";

const articulos = await (await fetch(`${API}/kedb/articulos`)).json();
// Artículo con muchos tickets fuente (trazabilidad N:1); los borradores son los que lista la pantalla del Experto.
const kyocera = articulos.find((a) => a.estado === "borrador" && /Kyocera/i.test(a.titulo) && a.tickets_fuente.length > 100);
// La detección de duplicados compara contra artículos validados e indexados (umbral 0.85): su solución textual la dispara.
const correo = articulos.find((a) => a.estado === "validado" && /correo/i.test(a.titulo));
const ticketCorreo = await post("/tickets", { texto: "Mi correo institucional indica buzón lleno y no sincroniza" });
const categorias = await (await fetch(`${API}/tickets/categorias`)).json();
const categoriaNueva = categorias.find((c) => c !== bajo.categoria);

const browser = await chromium.launch({ executablePath: CHROME });
const page = await (await browser.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
page.on("dialog", (d) => d.accept()); // beforeunload de la app
const shot = (name) => page.screenshot({ path: path.join(OUT, name), fullPage: true });
const abrirTicket = async (id) => {
  await page.goto(`${WEB}/tickets/${id}`, { waitUntil: "domcontentloaded" });
  await page.getByText("Sugerencias del Agente IA").waitFor();
};

// 1. Confianza baja resaltada.
await abrirTicket(bajo.ticket_id);
await shot("01-confianza-baja-resaltada.png");

// 2. Corrección: inválida (se altera la petición para forzar una categoría fuera del catálogo; el rechazo es del backend) y válida.
await page.route("**/tickets/*/categoria", async (route) => {
  await route.continue({ postData: JSON.stringify({ categoria: "Categoría inventada > No existe" }) });
});
await page.getByLabel("Corregir categoría (HU03)").selectOption(categoriaNueva);
await page.getByRole("button", { name: "Corregir", exact: true }).click();
await page.getByText("Categoría no válida").waitFor();
await shot("02b-correccion-categoria-invalida-rechazada.png");
await page.unroute("**/tickets/*/categoria");
await page.getByRole("button", { name: "Corregir", exact: true }).click();
await page.getByText("Categoría corregida.").waitFor();
await shot("02a-correccion-categoria-valida.png");

// 3. Factores de prioridad y ausencia de factores.
await abrirTicket(normal.ticket_id);
await shot("03a-factores-de-prioridad.png");
await abrirTicket(SIN_FACTORES);
await page.getByText("No hay factores disponibles para esta prioridad").waitFor();
await shot("03b-sin-factores-de-prioridad.png");

// 4. Calificación de utilidad.
await abrirTicket(normal.ticket_id);
await page.getByRole("button", { name: "Útil (HU11)" }).first().click();
await page.getByText("Feedback registrado: solución marcada como útil.").waitFor();
await shot("04-calificacion-utilidad-articulo.png");

// 5. Nueva solución: validación (muy corta) y advertencia de duplicidad.
await abrirTicket(ticketCorreo.ticket_id);
const area = page.getByPlaceholder("Documentar solución no sugerida...");
await area.fill("corto");
await page.getByRole("button", { name: "Registrar" }).click();
await page.getByText("La solución es muy corta").waitFor();
await shot("05a-nueva-solucion-validacion.png");
await area.fill(correo.solucion);
await page.getByRole("button", { name: "Registrar" }).click();
await page.getByText("Posible duplicado").waitFor();
await shot("05b-nueva-solucion-advertencia-duplicado.png");

// 6. Detalle de artículo KEDB con tickets fuente.
await page.goto(`${WEB}/experto`, { waitUntil: "domcontentloaded" });
await page.getByText(kyocera.titulo.slice(0, 30)).first().click();
await page.getByText("Trazabilidad N:1 (HU09)").waitFor();
await shot("06-detalle-articulo-kedb-tickets-fuente.png");

await browser.close();
console.log("ok", { bajo: [bajo.ticket_id, bajo.confianza], normal: normal.ticket_id, kyocera: kyocera.articulo_id, categoriaNueva });
