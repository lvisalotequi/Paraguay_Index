# Dashboard interno (web app de Apps Script)

Segundo enlace del US-PY Engagement Index, para uso interno de Equilibrium. Es **el mismo dashboard** que se publica en
GitHub Pages: no es una copia mantenida a mano, se genera a partir de los archivos de `dashboard/`, que no se tocan.

| | Enlace público | Enlace interno |
|---|---|---|
| Dónde vive | GitHub Pages (`publicar_dashboard.yml`) | Web app de Apps Script |
| Quién entra | Cualquiera con el enlace | Personas del dominio de Equilibrium |
| Diseño | `dashboard/` | El mismo (lo arma `construir_dashboard.py` desde `dashboard/`) |
| Datos | CSV que baja el workflow cada día | El Sheet `us_py_engagement_index`, leído en cada visita |

## Cómo funciona

```
dashboard/  (diseño; no se modifica)
   │  construir_dashboard.py   (a mano, o solo con el workflow publicar_dashboard_interno.yml)
   ▼
Drive: 04_final/dashboard_interno/dashboard.html     un solo HTML, sin datos, sin archivos hermanos
   │
   ▼  doGet() de apps_script/Codigo.gs, en cada visita
   +  Sheet us_py_engagement_index  (pestañas indice_ancho y diccionario)
   ▼
Enlace interno (termina en /exec)
```

Consecuencia práctica: **cuando el pipeline actualiza el Sheet no hay que hacer nada**; la siguiente persona que abra el enlace
ve los datos nuevos. El HTML solo se vuelve a subir cuando cambia el diseño de `dashboard/`.

## Instalación (una sola vez)

1. **Subir el HTML a Drive.** `python dashboard_interno/construir_dashboard.py` (con `.env` y la cuenta de servicio, como el resto del repo).
   La primera vez crea `04_final/dashboard_interno/`; siempre deja `dashboard.html` en esa carpeta (mismo archivo, se reemplaza el contenido)
   y al final imprime los dos IDs que pide el paso 3. Con `--sin-subir` solo arma `dashboard_interno/salida/dashboard.html` y no toca Drive.
2. **Proyecto de Apps Script.** En script.google.com, proyecto nuevo, con la cuenta que va a ser dueña del enlace
   (ver «Quién figura» abajo). Pegar `apps_script/Codigo.gs`. En Configuración del proyecto activar «Mostrar el archivo de manifiesto
   appsscript.json» y pegar `apps_script/appsscript.json`.
3. **Propiedades del script** (Configuración del proyecto > Propiedades del script):
   - `DASHBOARD_CARPETA_ID` = ID de la carpeta `dashboard_interno` (lo imprime el paso 1).
   - `INDICE_SHEET_ID` = ID del Sheet `us_py_engagement_index` (lo imprime el paso 1).
   - `CLAVE` = la contraseña de acceso (mínimo 8 caracteres).
   - `CODIGO_ACCESO` = el código de acceso (mínimo 4 caracteres, puede ser numérico). Distinto de la contraseña.
   - Opcional: `CORREOS_AUTORIZADOS` = correos separados por comas. Vacía, entra cualquier persona del dominio; llena, solo esas.
4. **Implementar** > Nueva implementación > Aplicación web: ejecutar como **yo**, acceso **cualquier persona de Equilibrium**. Autorizar los
   permisos que pida Google y copiar la URL que termina en `/exec`: ese es el enlace interno.

La cuenta que despliega es la que lee la carpeta y el Sheet (quien abre el enlace no necesita permiso sobre ellos), así que **esa cuenta debe
poder ver ambos**.

### Quién figura

El enlace no lleva el nombre de nadie: en Google Workspace tiene la forma `script.google.com/a/macros/<dominio>/s/<id>/exec`. Lo que sí tiene
dueño es el proyecto de Apps Script: si lo crea una cuenta personal y esa persona se va de la organización, el enlace deja de funcionar. Lo
conveniente es crearlo desde una cuenta institucional o compartida de Equilibrium, o transferir la propiedad después.

## Contraseña y código de acceso

Además de ser del dominio, quien abre el enlace ve una pantalla que pide una **contraseña** y un **código de acceso**. Solo si los dos
son correctos se carga el dashboard.

- Se configuran en las propiedades del script (`CLAVE` y `CODIGO_ACCESO`) y se pueden cambiar cuando se quiera: rige al instante, sin crear
  versión nueva. Los ve únicamente quien edita el proyecto de Apps Script.
- La validación es del servidor. `doGet()` solo entrega la pantalla de acceso (unos 3 KB, sin datos ni diseño); el dashboard y sus datos
  salen de `entrar()` y solo cuando las dos coinciden. Esa función repite todas las comprobaciones, así que no se puede saltar la pantalla
  llamándola a mano desde la consola del navegador.
- Cinco intentos fallidos bloquean a esa persona (por su cuenta) durante 15 minutos, aunque después escriba bien. El aviso no dice cuál
  de los dos estaba mal. El contador vive en la caché de Apps Script, que no garantiza conservar el dato hasta que venza: es un freno al
  ensayo y error, no una garantía absoluta.
- Si falta la contraseña o el código, o son más cortos que el mínimo, el enlace **no abre**: avisa que falta configurarlo en vez de quedar
  sin protección. Los espacios al inicio y al final se ignoran.
- Se pide en cada visita, también al recargar la página. El selector ES/EN del dashboard no recarga, así que no vuelve a pedirla.
  Con `?lang=en` la pantalla de acceso sale en inglés.

**Qué no cubre.** Protege el enlace, no los archivos: quien tenga permiso sobre el Sheet `us_py_engagement_index` o sobre la carpeta de Drive
puede leer los datos sin pasar por el enlace, y eso se controla con los permisos de Drive. Tampoco distingue personas: es un secreto
compartido, así que si alguien deja el equipo conviene cambiar los dos valores.

## Mantenimiento

| Qué cambia | Qué hacer |
|---|---|
| Datos (el pipeline actualizó el Sheet) | Nada. |
| Contraseña o código de acceso | Editar las propiedades `CLAVE` y `CODIGO_ACCESO` del script. Rige al instante. |
| Diseño (`dashboard/`) | Nada si se sube a `main`: lo dispara `publicar_dashboard_interno.yml`. A mano: `python dashboard_interno/construir_dashboard.py`. |
| `apps_script/Codigo.gs` | Pegar el código nuevo en el proyecto y Implementar > Administrar implementaciones > editar > «Nueva versión». La URL no cambia. |

Parámetro opcional del enlace: `?lang=en` lo abre en inglés (`?lang=es`, en español).

**Si `construir_dashboard.py` se corta con «Parche '…': se esperaban N coincidencias»**: el diseño cambió en un punto donde este script lo ajusta
(la lectura de datos, la dirección de la página, las rutas de archivos). Se corta a propósito antes de subir, para que el enlace interno
no pase a mostrar una página rota. Hay que actualizar ese parche en el script.

## Qué se verificó y qué no

Verificado (local, con los datos reales del Sheet y el `Codigo.gs` ejecutado con simulaciones de `DriveApp`, `SpreadsheetApp` y `HtmlService`):

- El dashboard se dibuja dentro de un marco aislado **sin ningún archivo hermano** y sin pedir nada local; solo Google Fonts y React/iconos desde unpkg, igual que el sitio de GitHub Pages.
- El texto renderizado es idéntico al del sitio original en los cuatro estados probados (inicio, EN, ES y nota técnica); el HTML solo difiere en un nombre interno del runtime.
- El CSV que arma `Codigo.gs` desde el Sheet coincide celda por celda (5.623 celdas) con el que baja el workflow para GitHub Pages.
- Los datos se inyectan de forma segura (un dato con `</script>`, `$&` o `<!--` vuelve intacto) y un marcador ausente da un error claro.
- Las descargas de `indice_ancho.csv` y `diccionario.csv` (vista avanzada) entregan el mismo CSV con el nombre correcto; `?lang=en` abre en inglés.
- Contraseña y código (con `google.script.run`, `CacheService`, `LockService` y SHA-256 simulados): la pantalla de acceso no contiene nada del dashboard ni lee Drive o el Sheet; con 5 fallos queda bloqueada incluso con las credenciales correctas (y a los 899 s sigue, a los 901 entra); el bloqueo es por persona; la lista de correos se aplica aunque se llame a `entrar()` a mano; sin contraseña, código o IDs configurados todo se niega; con las credenciales correctas el dashboard se dibuja idéntico al original, en español y en inglés.

**No se puede comprobar fuera de Google; revisar en la primera prueba del enlace real:**

- Que el marco de Apps Script ejecute el dashboard completo. El runtime compila su lógica con `new Function`, y la página (~510 KB con datos) carga React desde unpkg y Barlow desde Google Fonts: si la red de la oficina bloquea esos dominios, no cargará (el enlace público tiene el mismo riesgo).
- Que el botón de descarga de los CSV funcione: depende de que el marco de Apps Script permita descargas. Si no, el botón no hará nada visible.
- Que el idioma se recuerde al recargar (usa `localStorage`; si el marco no lo permite, vuelve a español, y `?lang=en` lo fuerza).
- Con `CORREOS_AUTORIZADOS` lleno: que entre una cuenta autorizada y que otra vea «Sin acceso».
- Que la pantalla de acceso funcione en el marco real: llama a `entrar()` con `google.script.run` y, si sale bien, reemplaza su contenido por el dashboard con `document.write`. Se probó contra un `google.script.run` simulado, no el de Google.
- Que `Session.getActiveUser().getEmail()` devuelva el correo de quien abre el enlace: el límite de intentos es por persona. Si viniera vacío, todas las personas comparten un solo cupo de 5 intentos.
- `CacheService` y `LockService` no piden permisos adicionales según la documentación de Google, por eso el manifiesto no cambió y no hace falta reautorizar. Si Google pidiera uno, el mensaje de error lo nombra.
- Los permisos que muestra Google al autorizar: `drive.readonly`, `spreadsheets` y `userinfo.email` (ver `appsscript.json`). `SpreadsheetApp` exige el permiso completo `spreadsheets`, no existe una versión de solo lectura para esa clase; el código solo lee (una prueba comprueba que `Codigo.gs` no use ningún método de escritura). Con `spreadsheets.readonly` falla con «Los permisos especificados no son suficientes para llamar a SpreadsheetApp.openById»: ese error apareció en la primera prueba real y es el motivo del cambio.

## Archivos

| Archivo | Para qué |
|---|---|
| `construir_dashboard.py` | Arma `dashboard.html` autosuficiente desde `dashboard/` y lo sube a Drive. |
| `apps_script/Codigo.gs` | Web app: pide contraseña y código y, si son correctos, junta el HTML de Drive con los datos del Sheet y lo sirve. |
| `apps_script/appsscript.json` | Manifiesto: permisos (Drive de solo lectura y `spreadsheets`, que `SpreadsheetApp` exige completo), «ejecutar como yo», acceso por dominio. |
| `salida/` | HTML armado en local (no se versiona). |
| `../.github/workflows/publicar_dashboard_interno.yml` | Sube el HTML a Drive cuando cambia `dashboard/`. |
| `../tests/test_dashboard_interno.py` | Pruebas del HTML armado y de que `Codigo.gs` y el constructor se mantengan de acuerdo. |
