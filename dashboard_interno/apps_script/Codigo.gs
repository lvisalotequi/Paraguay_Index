/**
 * Web app del dashboard interno «US-PY Engagement Index».
 *
 * Es el enlace interno del mismo dashboard que se publica en GitHub Pages. Junta dos cosas en cada visita:
 *   1. el diseño: el archivo dashboard.html que deja construir_dashboard.py en una carpeta de Drive
 *      (un solo HTML sin archivos hermanos, con un marcador donde van los datos), y
 *   2. los datos: las pestañas indice_ancho y diccionario del Google Sheet us_py_engagement_index, que se leen en el momento.
 * Por eso no hay que volver a publicar nada cuando el pipeline actualiza el Sheet: la siguiente persona que abra el enlace ve los
 * datos nuevos. El HTML solo se vuelve a subir cuando cambia el diseño del dashboard (lo hace el workflow publicar_dashboard_interno).
 *
 * Contraseña y código de acceso: además de ser del dominio, quien abre el enlace ve una pantalla donde debe escribir la contraseña y el
 * código de acceso. doGet() solo entrega esa pantalla; el dashboard y sus datos salen únicamente de entrar(), después de validar las dos
 * cosas en el servidor (la pantalla no decide nada). Con 5 intentos fallidos la persona queda bloqueada 15 minutos. Si falta la contraseña
 * o el código, o son demasiado cortos, el enlace no abre (nunca queda sin protección en silencio). Solo entrar() es pública para
 * google.script.run: las demás funciones terminan en «_», y esas no se pueden llamar desde el navegador.
 *
 * Proyecto de Apps Script aparte, propiedad de una cuenta de Equilibrium. Se despliega como «Ejecutar como: yo» y acceso
 * «Cualquier persona de la organización» (ver appsscript.json). Quien abre el enlace no necesita permiso sobre la carpeta ni sobre el Sheet:
 * los lee la cuenta que despliega, así que esa cuenta sí debe poder verlos.
 *
 * Propiedades del script (Configuración del proyecto > Propiedades del script):
 *   DASHBOARD_CARPETA_ID   (obligatoria) ID de la carpeta de Drive con dashboard.html (la parte de la URL tras /folders/)
 *   INDICE_SHEET_ID        (obligatoria) ID del Google Sheet us_py_engagement_index (la parte de la URL entre /d/ y /edit)
 *   CLAVE                  (obligatoria) contraseña de acceso, de al menos 8 caracteres
 *   CODIGO_ACCESO          (obligatoria) código de acceso, de al menos 4 caracteres (puede ser numérico)
 *   CORREOS_AUTORIZADOS    (opcional) correos separados por comas. Vacía = entra cualquier persona de la organización.
 * construir_dashboard.py imprime los dos primeros IDs al terminar. La contraseña y el código los ve solo quien edita este proyecto;
 * para cambiarlos basta editar la propiedad (no hace falta crear una versión nueva). Los espacios al inicio y al final se ignoran.
 *
 * No pongas en este archivo IDs, enlaces ni correos: van en las propiedades del script.
 * Parámetro opcional del enlace: ?lang=en abre el dashboard en inglés (?lang=es en español).
 * El nombre del archivo y el marcador deben coincidir con NOMBRE_ARCHIVO y MARCA_DATOS de dashboard_interno/construir_dashboard.py.
 * Las columnas obligatorias deben coincidir con COLUMNAS_OBLIGATORIAS de dashboard/exportar_datos.py.
 */

const NOMBRE_ARCHIVO = 'dashboard.html';
const MARCA_DATOS = '<!--USPY_DATOS-->';
const TITULO = 'US-PY Engagement Index';

/** Clave con la que el dashboard pide cada tabla -> pestaña del Sheet. */
const PESTANAS = { ancho: 'indice_ancho', diccionario: 'diccionario' };

/** Sin estas columnas el dashboard no puede dibujarse; si faltan, se avisa en vez de mostrar una página rota. */
const COLUMNAS_OBLIGATORIAS = [
  'trimestre',
  'indice_agregado_base_2015_2019',
  'banda_series_p05_base_2015_2019',
  'banda_series_p95_base_2015_2019'
];

/** Intentos fallidos que se toleran por persona antes de bloquearla, y cuánto dura el bloqueo (segundos). */
const MAX_INTENTOS = 5;
const BLOQUEO_SEGUNDOS = 900;

/** Largo mínimo de la contraseña y del código. Con menos, el enlace se niega a abrir en vez de quedar protegido solo en apariencia. */
const MIN_CLAVE = 8;
const MIN_CODIGO = 4;

/** Textos de la pantalla de acceso y de sus avisos, por idioma (?lang=en). */
const TEXTOS = {
  es: {
    etiqueta: 'Acceso interno',
    ayuda: 'Ingresa la contraseña y el código de acceso que te dio el equipo.',
    clave: 'Contraseña',
    codigo: 'Código de acceso',
    entrar: 'Entrar',
    verificando: 'Verificando…',
    incorrecto: 'Contraseña o código incorrectos.',
    restantes: 'Intentos restantes: ',
    bloqueado: 'Demasiados intentos fallidos. Espera {min} minutos para volver a intentar.',
    ocupado: 'El sistema está ocupado. Vuelve a intentar en unos segundos.',
    red: 'No se pudo verificar el acceso. Vuelve a intentar.'
  },
  en: {
    etiqueta: 'Internal access',
    ayuda: 'Enter the password and the access code the team gave you.',
    clave: 'Password',
    codigo: 'Access code',
    entrar: 'Enter',
    verificando: 'Verifying…',
    incorrecto: 'Incorrect password or code.',
    restantes: 'Attempts left: ',
    bloqueado: 'Too many failed attempts. Wait {min} minutes before trying again.',
    ocupado: 'The system is busy. Please try again in a few seconds.',
    red: 'Access could not be verified. Please try again.'
  }
};

/** Solo entrega la pantalla de acceso. El dashboard nunca sale de aquí: sale de entrar(), después de validar. */
function doGet(e) {
  try {
    const config = configuracion_();
    const problema = problemaConfiguracion_(config);
    if (problema) return mensaje_('Falta configurar el dashboard', problema);

    const acceso = comprobarPersona_(config);
    if (acceso) return mensaje_(acceso.titulo, acceso.detalle);

    return paginaAcceso_(idiomaDe_((e && e.parameter && e.parameter.lang) || ''));
  } catch (err) {
    return mensaje_('No se pudo cargar el dashboard', String((err && err.message) || err));
  }
}

/**
 * Valida la contraseña y el código y, solo si son correctos, devuelve el dashboard completo (HTML con los datos del Sheet).
 * La pantalla de acceso la llama con google.script.run. Es pública a propósito: cualquier persona del dominio podría llamarla
 * directamente desde la consola del navegador, así que repite aquí todas las comprobaciones (configuración, lista de correos,
 * límite de intentos) y no confía en que doGet() ya las hizo.
 * Devuelve {ok: true, html} o {ok: false, mensaje}.
 */
function entrar(clave, codigo, idioma) {
  const lang = idiomaDe_(idioma);
  const t = TEXTOS[lang === 'en' ? 'en' : 'es'];
  try {
    const config = configuracion_();
    const problema = problemaConfiguracion_(config);
    if (problema) return { ok: false, mensaje: problema };

    const acceso = comprobarPersona_(config);
    if (acceso) return { ok: false, mensaje: acceso.titulo + '. ' + acceso.detalle };

    const veredicto = verificar_(config, String(clave || '').trim(), String(codigo || '').trim());
    if (!veredicto.ok) {
      if (veredicto.motivo === 'bloqueado') return { ok: false, mensaje: t.bloqueado.split('{min}').join(String(Math.round(BLOQUEO_SEGUNDOS / 60))) };
      if (veredicto.motivo === 'ocupado') return { ok: false, mensaje: t.ocupado };
      Utilities.sleep(900);   // frena a quien prueba contraseñas una tras otra
      return { ok: false, mensaje: t.incorrecto + ' ' + t.restantes + veredicto.restantes + '.' };
    }

    return { ok: true, html: armarDashboard_(config, lang) };
  } catch (err) {
    return { ok: false, mensaje: String((err && err.message) || err) };
  }
}

/** Propiedades del script ya limpias (sin espacios al inicio ni al final). */
function configuracion_() {
  const propiedades = PropertiesService.getScriptProperties();
  const leer = function (nombre) { return (propiedades.getProperty(nombre) || '').trim(); };
  return {
    carpetaId: leer('DASHBOARD_CARPETA_ID'),
    hojaId: leer('INDICE_SHEET_ID'),
    clave: leer('CLAVE'),
    codigo: leer('CODIGO_ACCESO'),
    autorizados: listaCorreos_(propiedades.getProperty('CORREOS_AUTORIZADOS'))
  };
}

/** Texto del problema si la configuración no alcanza para abrir el dashboard de forma segura; '' si está bien. */
function problemaConfiguracion_(config) {
  if (!config.carpetaId || !config.hojaId) return 'El administrador debe definir las propiedades DASHBOARD_CARPETA_ID e INDICE_SHEET_ID del script.';
  if (config.clave.length < MIN_CLAVE) return 'El administrador debe definir la propiedad CLAVE del script (la contraseña, de al menos ' + MIN_CLAVE + ' caracteres).';
  if (config.codigo.length < MIN_CODIGO) return 'El administrador debe definir la propiedad CODIGO_ACCESO del script (el código, de al menos ' + MIN_CODIGO + ' caracteres).';
  return '';
}

/** null si la persona puede seguir; si no, {titulo, detalle}. Solo actúa cuando hay lista CORREOS_AUTORIZADOS. */
function comprobarPersona_(config) {
  if (!config.autorizados.length) return null;
  const usuario = correoActual_();
  if (!usuario) return { titulo: 'No se pudo identificar tu cuenta', detalle: 'Abre el enlace con tu cuenta de Equilibrium.' };
  if (config.autorizados.indexOf(usuario) < 0) return { titulo: 'Sin acceso', detalle: 'Tu cuenta (' + usuario + ') no está en la lista de personas autorizadas. Pídele acceso al administrador.' };
  return null;
}

function correoActual_() {
  return (Session.getActiveUser().getEmail() || '').toLowerCase();
}

/** 'es', 'en' o '' (sin parámetro: el dashboard usa el idioma que la persona ya tenía guardado). */
function idiomaDe_(valor) {
  return (valor === 'en' || valor === 'es') ? valor : '';
}

/**
 * Compara contraseña y código con los configurados y cuenta los fallos por persona (en la caché del script, que vence sola).
 * Va dentro de un candado para que varios intentos a la vez no se salten el límite. Devuelve {ok} o {ok: false, motivo, restantes}.
 */
function verificar_(config, clave, codigo) {
  const cache = CacheService.getScriptCache();
  const llave = llaveFallos_(correoActual_());
  const candado = LockService.getScriptLock();
  if (!candado.tryLock(5000)) return { ok: false, motivo: 'ocupado' };
  try {
    const fallos = Number(cache.get(llave) || 0);
    if (fallos >= MAX_INTENTOS) return { ok: false, motivo: 'bloqueado' };

    // las dos comparaciones se hacen siempre, para que ni el tiempo ni el aviso delaten cuál de las dos estaba mal
    const claveOk = iguales_(clave, config.clave);
    const codigoOk = iguales_(codigo, config.codigo);
    if (claveOk && codigoOk) {
      cache.remove(llave);
      return { ok: true };
    }
    cache.put(llave, String(fallos + 1), BLOQUEO_SEGUNDOS);
    return { ok: false, motivo: 'incorrecto', restantes: MAX_INTENTOS - fallos - 1 };
  } finally {
    candado.releaseLock();
  }
}

/** Clave de caché de los fallos de una persona (hash del correo: no guarda correos en claro). Sin correo, todos comparten un solo cupo. */
function llaveFallos_(correo) {
  return 'fallos_' + hex_(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, correo || 'desconocido', Utilities.Charset.UTF_8));
}

function hex_(bytes) {
  return bytes.map(function (b) { return ('0' + (b & 255).toString(16)).slice(-2); }).join('');
}

/** Igualdad de textos sin cortar en la primera diferencia: se comparan los hash completos byte a byte. */
function iguales_(a, b) {
  const ha = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, String(a), Utilities.Charset.UTF_8);
  const hb = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, String(b), Utilities.Charset.UTF_8);
  let diferencia = ha.length ^ hb.length;
  for (let i = 0; i < ha.length && i < hb.length; i++) diferencia |= ha[i] ^ hb[i];
  return diferencia === 0;
}

/** El dashboard completo: el HTML de Drive con los datos del Sheet puestos en el marcador. */
function armarDashboard_(config, idioma) {
  const archivo = archivoMasReciente_(DriveApp.getFolderById(config.carpetaId), NOMBRE_ARCHIVO);
  if (!archivo) throw new Error('Aún no hay dashboard: no encuentro «' + NOMBRE_ARCHIVO + '» en la carpeta. Hay que correr construir_dashboard.py para subirlo.');
  return inyectarDatos_(archivo.getBlob().getDataAsString('UTF-8'), leerDatos_(config.hojaId), { lang: idioma });
}

/** Estilo de la pantalla de acceso: la misma paleta de la portada del dashboard. */
const ESTILO_ACCESO =
  '*{box-sizing:border-box}html,body{height:100%}' +
  'body{margin:0;padding:24px;display:flex;align-items:center;justify-content:center;font:16px/1.5 Barlow,system-ui,sans-serif;color:#190e35;' +
  'background:linear-gradient(140deg,#190e35 0%,#2b1563 55%,#431c85 100%)}' +
  'main{width:100%;max-width:400px;padding:32px 28px;background:#fff;border-radius:14px;box-shadow:0 18px 50px rgba(16,8,35,.45)}' +
  '.etiqueta{margin:0 0 6px;font-size:13px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#431c85}' +
  'h1{margin:0 0 8px;font:800 30px/1 "Barlow Condensed",Barlow,system-ui,sans-serif;text-transform:uppercase}' +
  '.ayuda{margin:0 0 20px;color:#4d4760}' +
  'label{display:block;margin:0 0 4px;font-size:14px;font-weight:600}' +
  'input{width:100%;padding:11px 12px;margin:0 0 16px;font:inherit;color:#190e35;background:#fff;border:1px solid #cfc7dc;border-radius:8px}' +
  'input:focus{outline:3px solid #00fdff;border-color:#431c85}' +
  'button{width:100%;padding:12px;font:inherit;font-weight:700;color:#eeebe0;background:#190e35;border:0;border-radius:8px;cursor:pointer}' +
  'button:hover{background:#431c85}button:disabled{opacity:.6;cursor:default}' +
  '#mensaje{min-height:24px;margin:12px 0 0;font-size:14px;color:#b3261e}';

/**
 * Pantalla de contraseña y código. No lleva datos del dashboard. El formulario no se envía nunca por la vía normal del navegador
 * (onsubmit="return false" y sin atributo name en los campos), para que una contraseña jamás viaje en la dirección de la página.
 * Si la validación sale bien, la página se reemplaza por el HTML que devuelve entrar().
 */
function paginaAcceso_(parametroIdioma) {
  const lang = parametroIdioma === 'en' ? 'en' : 'es';
  const t = TEXTOS[lang];
  const cliente = { entrar: t.entrar, verificando: t.verificando, red: t.red };
  const script = '(function(){' +
    'var IDIOMA=' + enLinea_(parametroIdioma) + ',T=' + enLinea_(cliente) + ';' +
    'var form=document.getElementById("acceso"),boton=document.getElementById("entrar"),aviso=document.getElementById("mensaje"),' +
    'clave=document.getElementById("clave"),codigo=document.getElementById("codigo");' +
    'function fallo(texto){aviso.textContent=texto;boton.disabled=false;boton.textContent=T.entrar;clave.value="";codigo.value="";clave.focus();}' +
    'form.addEventListener("submit",function(ev){ev.preventDefault();aviso.textContent="";boton.disabled=true;boton.textContent=T.verificando;' +
    'google.script.run' +
    '.withSuccessHandler(function(r){if(r&&r.ok&&r.html){document.open();document.write(r.html);document.close();}else{fallo((r&&r.mensaje)||T.red);}})' +
    '.withFailureHandler(function(){fallo(T.red);})' +
    '.entrar(clave.value,codigo.value,IDIOMA);});' +
    '})();';
  const html = '<!doctype html><html lang="' + lang + '"><head><meta charset="utf-8">' +
    '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>' +
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@800&family=Barlow:wght@400;600;700&display=swap">' +
    '<style>' + ESTILO_ACCESO + '</style></head><body><main>' +
    '<p class="etiqueta">' + escapar_(t.etiqueta) + '</p><h1>' + escapar_(TITULO) + '</h1><p class="ayuda">' + escapar_(t.ayuda) + '</p>' +
    '<form id="acceso" onsubmit="return false">' +
    '<label for="clave">' + escapar_(t.clave) + '</label><input id="clave" type="password" autocomplete="current-password" required autofocus>' +
    '<label for="codigo">' + escapar_(t.codigo) + '</label><input id="codigo" type="password" autocomplete="off" required>' +
    '<button id="entrar" type="submit">' + escapar_(t.entrar) + '</button><p id="mensaje" role="alert" aria-live="polite"></p>' +
    '</form></main><script>' + script + '</script></body></html>';
  return HtmlService.createHtmlOutput(html)
    .setTitle(TITULO)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/** Lee las dos pestañas del Sheet y las devuelve como texto CSV (lo que el dashboard espera), ya validadas. */
function leerDatos_(hojaId) {
  const libro = SpreadsheetApp.openById(hojaId);
  const datos = {};
  Object.keys(PESTANAS).forEach(function (clave) {
    const hoja = libro.getSheetByName(PESTANAS[clave]);
    if (!hoja) throw new Error('El Sheet no tiene la pestaña «' + PESTANAS[clave] + '».');
    const filas = hoja.getDataRange().getValues();   // valores sin formato regional: 1234.5, no «1.234,50»
    if (filas.length < 2) throw new Error('La pestaña «' + PESTANAS[clave] + '» no tiene datos.');
    if (clave === 'ancho') {
      const encabezado = filas[0].map(function (c) { return String(c).trim(); });
      const faltantes = COLUMNAS_OBLIGATORIAS.filter(function (c) { return encabezado.indexOf(c) < 0; });
      if (faltantes.length) throw new Error('Faltan columnas en «' + PESTANAS[clave] + '»: ' + faltantes.join(', ') + '. Hay que correr construccion_indice.py para que el Sheet las publique.');
    }
    datos[clave] = aCsv_(filas);
  });
  return datos;
}

/** Tabla -> texto CSV (UTF-8, saltos \n, comillas dobles solo donde hacen falta), como el que arma dashboard/exportar_datos.py. */
function aCsv_(filas) {
  return filas.map(function (fila) { return fila.map(celda_).join(','); }).join('\n') + '\n';
}

function celda_(valor) {
  if (valor === null || valor === undefined) return '';
  const texto = (valor instanceof Date) ? Utilities.formatDate(valor, Session.getScriptTimeZone(), 'yyyy-MM-dd') : String(valor);
  return /[",\r\n]/.test(texto) ? '"' + texto.replace(/"/g, '""') + '"' : texto;
}

/**
 * Pone los datos en el marcador del HTML. Se corta el texto y se vuelve a unir en vez de usar replace(): replace() leería los «$»
 * de los datos como instrucciones. Los datos van como JSON dentro de un <script>, con «<» escapado para que ningún texto cierre la etiqueta.
 */
function inyectarDatos_(base, datos, parametros) {
  const partes = base.split(MARCA_DATOS);
  if (partes.length !== 2) {
    throw new Error('El archivo ' + NOMBRE_ARCHIVO + ' no trae el marcador de datos (o lo trae más de una vez). Hay que volver a correr construir_dashboard.py.');
  }
  // dentro del marco de Apps Script la dirección de la página no lleva los parámetros del enlace: se entregan desde aquí
  const idioma = (parametros.lang === 'en' || parametros.lang === 'es') ? parametros.lang : '';
  const script = '<script>window.__USPY_DATOS=' + enLinea_(datos) + ';window.__USPY_BUSQUEDA=' + enLinea_(idioma ? '?lang=' + idioma : '') + ';</script>';
  return partes[0] + script + partes[1];
}

function enLinea_(valor) {
  // «<» y los separadores de linea U+2028/U+2029 se escriben como escapes unicode, para que ningun texto cierre el <script>
  // ni parta el literal. La barra invertida se arma con fromCharCode para no depender de como se copie este archivo.
  const barra = String.fromCharCode(92);
  return JSON.stringify(valor)
    .replace(/</g, barra + 'u003c')
    .replace(new RegExp(String.fromCharCode(0x2028), 'g'), barra + 'u2028')
    .replace(new RegExp(String.fromCharCode(0x2029), 'g'), barra + 'u2029');
}

/** Correos en minúsculas, sin espacios ni vacíos. */
function listaCorreos_(texto) {
  return String(texto || '').split(',').map(function (c) { return c.trim().toLowerCase(); }).filter(String);
}

/** De varios archivos con el mismo nombre, el último que se modificó (construir_dashboard.py reemplaza el contenido, así que debería haber uno solo). */
function archivoMasReciente_(carpeta, nombre) {
  const archivos = carpeta.getFilesByName(nombre);
  let elegido = null;
  while (archivos.hasNext()) {
    const a = archivos.next();
    if (!elegido || a.getLastUpdated() > elegido.getLastUpdated()) elegido = a;
  }
  return elegido;
}

function escapar_(texto) {
  return String(texto).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/** Página simple para avisos y errores (el texto siempre va escapado). */
function mensaje_(titulo, detalle) {
  const html = '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">' +
    '<style>body{font:16px/1.5 system-ui,sans-serif;background:#f4f1f8;color:#190e35;margin:0;padding:48px 24px}' +
    'main{max-width:560px;margin:0 auto}h1{font-size:22px;margin:0 0 8px}p{margin:0;color:#4d4760}</style></head>' +
    '<body><main><h1>' + escapar_(titulo) + '</h1><p>' + escapar_(detalle) + '</p></main></body></html>';
  return HtmlService.createHtmlOutput(html).setTitle(TITULO);
}
