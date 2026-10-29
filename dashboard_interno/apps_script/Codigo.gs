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
 * Proyecto de Apps Script aparte, propiedad de una cuenta de Equilibrium. Se despliega como «Ejecutar como: yo» y acceso
 * «Cualquier persona de la organización» (ver appsscript.json). Quien abre el enlace no necesita permiso sobre la carpeta ni sobre el Sheet:
 * los lee la cuenta que despliega, así que esa cuenta sí debe poder verlos.
 *
 * Propiedades del script (Configuración del proyecto > Propiedades del script):
 *   DASHBOARD_CARPETA_ID   (obligatoria) ID de la carpeta de Drive con dashboard.html (la parte de la URL tras /folders/)
 *   INDICE_SHEET_ID        (obligatoria) ID del Google Sheet us_py_engagement_index (la parte de la URL entre /d/ y /edit)
 *   CORREOS_AUTORIZADOS    (opcional) correos separados por comas. Vacía = entra cualquier persona de la organización.
 * construir_dashboard.py imprime los dos primeros IDs al terminar.
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

function doGet(e) {
  try {
    const propiedades = PropertiesService.getScriptProperties();
    const carpetaId = (propiedades.getProperty('DASHBOARD_CARPETA_ID') || '').trim();
    const hojaId = (propiedades.getProperty('INDICE_SHEET_ID') || '').trim();
    if (!carpetaId || !hojaId) {
      return mensaje_('Falta configurar el dashboard', 'El administrador debe definir las propiedades DASHBOARD_CARPETA_ID e INDICE_SHEET_ID del script.');
    }

    const autorizados = listaCorreos_(propiedades.getProperty('CORREOS_AUTORIZADOS'));
    if (autorizados.length) {
      const usuario = (Session.getActiveUser().getEmail() || '').toLowerCase();
      if (!usuario) return mensaje_('No se pudo identificar tu cuenta', 'Abre el enlace con tu cuenta de Equilibrium.');
      if (autorizados.indexOf(usuario) < 0) return mensaje_('Sin acceso', 'Tu cuenta (' + usuario + ') no está en la lista de personas autorizadas. Pídele acceso al administrador.');
    }

    const archivo = archivoMasReciente_(DriveApp.getFolderById(carpetaId), NOMBRE_ARCHIVO);
    if (!archivo) return mensaje_('Aún no hay dashboard', 'No encuentro «' + NOMBRE_ARCHIVO + '» en la carpeta. Hay que correr construir_dashboard.py para subirlo.');

    const html = inyectarDatos_(archivo.getBlob().getDataAsString('UTF-8'), leerDatos_(hojaId), (e && e.parameter) || {});

    return HtmlService.createHtmlOutput(html)
      .setTitle(TITULO)
      .addMetaTag('viewport', 'width=device-width, initial-scale=1')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
  } catch (err) {
    return mensaje_('No se pudo cargar el dashboard', String((err && err.message) || err));
  }
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
