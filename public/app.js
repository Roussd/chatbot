// Estado en memoria. No se guarda historial: al recargar o pulsar "Nueva consulta" se empieza de cero.
let temas = [];
let temaActual = "todos";
let ocupado = false;

const $ = (id) => document.getElementById(id);
const esPantallaGrande = () => window.matchMedia("(min-width: 820px)").matches;

const ICONO_DOCUMENTO = '<svg viewBox="0 0 24 24"><path d="M7 3h7l5 5v13H7zM14 3v5h5"/></svg>';

// ---------- Utilidades ----------

function nombreBonito(id) {
  return id.split("_").map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join(" ");
}

async function api(ruta, datos) {
  const respuesta = await fetch(ruta, {
    method: datos ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: datos ? JSON.stringify(datos) : undefined,
  });
  if (!respuesta.ok) throw new Error(`Error ${respuesta.status}`);
  return respuesta.json();
}

function crear(etiqueta, clase, texto) {
  const el = document.createElement(etiqueta);
  if (clase) el.className = clase;
  if (texto) el.textContent = texto;
  return el;
}

function bloquear(estado) {
  ocupado = estado;
  $("btn-enviar").disabled = estado;
  $("btn-resumir").disabled = estado;
}

// ---------- Modo claro / oscuro ----------

function cambiarModo() {
  const raiz = document.documentElement;
  raiz.dataset.tema = raiz.dataset.tema === "oscuro" ? "claro" : "oscuro";
  try { localStorage.setItem("tema", raiz.dataset.tema); } catch {}
  actualizarColorDelNavegador();
}

function actualizarColorDelNavegador() {
  const oscuro = document.documentElement.dataset.tema === "oscuro";
  document.querySelector('meta[name="theme-color"]').content = oscuro ? "#06162B" : "#F4FBFF";
}

// ---------- Menú lateral ----------

function fijarMenu(abierto) {
  document.body.dataset.menu = abierto ? "abierto" : "cerrado";
  $("menu").inert = !abierto;  // un menú oculto no debe recibir foco con el teclado
}

function dibujarTemas() {
  $("temas").replaceChildren(
    ...temas.map((tema) => {
      const boton = crear("button", "tema" + (tema.id === temaActual ? " activo" : ""), nombreBonito(tema.id));
      boton.type = "button";
      boton.onclick = () => cambiarTema(tema.id);
      return boton;
    })
  );
}

function cambiarTema(id) {
  if (!esPantallaGrande()) fijarMenu(false);
  if (id === temaActual) return;
  temaActual = id;
  $("texto").placeholder =
    id === "todos"
      ? "Pregunta sobre todos los documentos o escribe una consulta..."
      : `Pregunta sobre ${nombreBonito(id)} o escribe una consulta...`;
  dibujarTemas();
  dibujarSugerencias();
  if (modo() === "chat") agregarNota(`Ahora consultando: ${nombreBonito(id)}`);
}

// ---------- Pantalla ----------

function dibujarSugerencias() {
  const preguntas = (temas.find((t) => t.id === temaActual)?.faq ?? []).slice(0, 3);
  $("sugerencias").replaceChildren(
    ...preguntas.map((pregunta) => {
      const boton = crear("button", "sugerencia", pregunta);
      boton.type = "button";
      boton.onclick = () => preguntar(pregunta);
      return boton;
    })
  );
}

function modo() {
  return document.body.dataset.modo;
}

function pasarAChat() {
  document.body.dataset.modo = "chat";
  $("inicio").hidden = true;
  $("conversacion").hidden = false;
  $("btn-nueva").hidden = false;
}

async function nuevaConsulta() {
  document.body.dataset.modo = "inicio";
  $("conversacion").replaceChildren();
  $("conversacion").hidden = true;
  $("inicio").hidden = false;
  $("btn-nueva").hidden = true;
  await cargarTemas();  // por si se agregaron documentos
}

// ---------- Mensajes ----------

function irAlFinal() {
  $("vista").scrollTop = $("vista").scrollHeight;
}

function agregarUsuario(texto) {
  $("conversacion").appendChild(crear("div", "usuario", texto));
  irAlFinal();
}

function agregarNota(texto) {
  $("conversacion").appendChild(crear("div", "nota", texto));
  irAlFinal();
}

function agregarAsistente(texto, fuentes = [], entendida = null) {
  const respuesta = crear("div", "asistente");
  if (entendida) respuesta.appendChild(crear("div", "entendida", `Entendí: «${entendida}»`));
  respuesta.appendChild(crear("div", "texto", texto));
  if (fuentes.length) {
    const lista = crear("div", "fuentes");
    lista.insertAdjacentHTML("beforeend", ICONO_DOCUMENTO);
    lista.appendChild(crear("span", "", fuentes.join(" · ")));
    respuesta.appendChild(lista);
  }
  $("conversacion").appendChild(respuesta);
  irAlFinal();
}

function agregarEspera(mensaje) {
  const espera = crear("div", "espera", mensaje);
  $("conversacion").appendChild(espera);
  irAlFinal();
  return espera;
}

// ---------- Acciones ----------

async function preguntar(texto) {
  if (ocupado) return;
  pasarAChat();
  agregarUsuario(texto);
  const espera = agregarEspera("Buscando en los documentos…");
  bloquear(true);
  try {
    const datos = await api("/api/chat", { tema: temaActual, texto });
    espera.remove();
    agregarAsistente(datos.respuesta, datos.fuentes, datos.entendida);
  } catch {
    espera.remove();
    agregarAsistente("No pude conectar con el servidor. Intenta nuevamente.");
  }
  bloquear(false);
}

async function resumir() {
  if (ocupado) return;
  pasarAChat();
  agregarUsuario(`Resumir: ${nombreBonito(temaActual)}`);
  const espera = agregarEspera("Resumiendo, puede tardar un poco…");
  bloquear(true);
  try {
    const datos = await api("/api/resumir", { tema: temaActual, documento: null });
    espera.remove();
    agregarAsistente(datos.resumen);
  } catch {
    espera.remove();
    agregarAsistente("No se pudo resumir. Intenta nuevamente.");
  }
  bloquear(false);
}

async function cargarTemas() {
  temas = await api("/api/temas");
  if (!temas.some((t) => t.id === temaActual)) temaActual = "todos";
  dibujarTemas();
  dibujarSugerencias();
}

// ---------- Eventos ----------

function enviarFormulario() {
  const texto = $("texto").value.trim();
  if (!texto) return;
  $("texto").value = "";
  ajustarAltura();
  preguntar(texto);
}

function ajustarAltura() {
  $("texto").style.height = "auto";
  $("texto").style.height = $("texto").scrollHeight + "px";
}

$("formulario").addEventListener("submit", (e) => {
  e.preventDefault();
  enviarFormulario();
});
$("texto").addEventListener("input", ajustarAltura);
$("texto").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    enviarFormulario();
  }
});
$("btn-resumir").onclick = resumir;
$("btn-nueva").onclick = nuevaConsulta;
$("btn-modo").onclick = cambiarModo;
$("btn-colapsar").onclick = () => fijarMenu(false);
$("btn-abrir").onclick = () => fijarMenu(true);
$("velo").onclick = () => fijarMenu(false);

actualizarColorDelNavegador();
fijarMenu(esPantallaGrande());  // abierto en escritorio, cerrado en celular
cargarTemas();
