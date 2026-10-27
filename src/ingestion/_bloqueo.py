#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 26/10/2026                                                #
# NOMBRE: _bloqueo                                                             #
# DETALLE: ayudante para sitios que bloquean los runners de Actions (403, 429  #
#   o un desafio de Cloudflare): arma un diagnostico con la URL y los          #
#   encabezados, marca el bloqueo con SitioBloqueado y arma el valor omitido   #
#   que run_pipeline.py reintenta en otro job. NO es un modulo de ingestion:   #
#   run_pipeline.py lo ignora por el guion bajo.                               #
#                                                                              #
# CORRE DESPUES DE: nada; lo importan _bcp_common, fa_gov_asistencia_oficial,  #
#   mre_menciones_eeuu y run_pipeline.py                                       #
# SALIDA: funciones (diagnostico, comprobar, omitido_por_bloqueo) y            #
#   SitioBloqueado; no escribe nada                                            #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import re



# Parametros -------------------------------------------------------------------

# bcp.gov.py, mre.gov.py y foreignassistance.gov (Cloudflare) responden 403 a las IP
# de los runners de GitHub Actions, a veces siempre y a veces solo en algunas
# corridas. Un "HTTP Error 403:" pelado no dice si la causa es la huella TLS, la IP o
# la frecuencia, ni en que URL paso. Este ayudante hace dos cosas:
#
#   - diagnostico(resp) arma una linea con la URL, el estado y los encabezados que
#     distinguen un desafio de Cloudflare (cf-mitigated, server, cf-ray).
#   - SitioBloqueado marca el caso "el sitio no nos deja pasar" (403, 429 o un
#     desafio de Cloudflare), distinto de un error de red o de formato. Los modulos
#     que no pueden traer nada nuevo por eso devuelven omitido_por_bloqueo(...): la
#     corrida no queda en rojo, el ultimo archivo subido a Drive sigue vigente y
#     run_pipeline.py lo vuelve a intentar en otro job (otro runner, otra IP).
#
# NO usar comprobar() donde la URL lleve una clave de API (Congreso, BEA): el
# diagnostico imprime la URL tal cual.
ESTADOS_BLOQUEO = (403, 429)

# run_pipeline.py reintenta en otro job todo modulo que devuelva "omitido" con este
# prefijo (ademas de los que terminan en error).
PREFIJO_OMITIDO_REINTENTABLE = "omitido: sitio no accesible"



# Funciones auxiliares ---------------------------------------------------------


class SitioBloqueado(RuntimeError):
    """El sitio respondio 403/429 o un desafio de Cloudflare."""


def diagnostico(resp):
    """Linea de texto con lo necesario para saber por que bloquearon la peticion."""
    headers = getattr(resp, "headers", None) or {}
    partes = [f"HTTP {resp.status_code}", str(getattr(resp, "url", "") or "")]
    for campo in ("server", "cf-mitigated", "cf-ray", "content-type"):
        valor = headers.get(campo)
        if valor:
            partes.append(f"{campo}={valor}")

    # si la respuesta es HTML, suma los primeros 100 caracteres del texto: un desafio
    # de Cloudflare dice "Just a moment..." ahi
    if "html" in str(headers.get("content-type", "")).lower():
        try:
            texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", resp.text)).strip()
        except Exception:  # noqa: BLE001
            texto = ""
        if texto:
            partes.append(f"cuerpo={texto[:100]!r}")
    return " | ".join(p for p in partes if p)


def esta_bloqueada(resp):
    headers = getattr(resp, "headers", None) or {}
    return resp.status_code in ESTADOS_BLOQUEO or bool(headers.get("cf-mitigated"))


def comprobar(resp):
    """Como `resp.raise_for_status()`, pero un bloqueo lanza `SitioBloqueado`
    con el diagnostico completo y el resto de los errores HTTP siguen igual."""
    if esta_bloqueada(resp):
        raise SitioBloqueado(diagnostico(resp))
    resp.raise_for_status()


def omitido_por_bloqueo(fuente, sitio, exc):
    """Valor de retorno de run() cuando el sitio bloquea: imprime el detalle y
    devuelve el "omitido: ..." que run_pipeline registra como OMITIDO."""
    print(f"[{fuente}] [!] {sitio} bloqueo la peticion: {exc}")
    return (
        f"{PREFIJO_OMITIDO_REINTENTABLE} ({sitio}): {exc}. "
        "El ultimo archivo subido a Drive sigue vigente."
    )
