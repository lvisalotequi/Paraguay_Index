"""Execute the reconciled historical plan in safe, resumable blocks."""
import argparse
import json
from datetime import datetime
from pathlib import Path

from bilateral_media_extractor import GIB, require_unbilled_project
from extraction_workflow import execute_plan, make_plan
from usage_ledger import refresh

ROOT = Path(__file__).resolve().parent
DEFAULT_ESTIMATE = ROOT / 'output/historical_estimates/estimate_2015-02_2025-12_reconciled.json'
DEFAULT_CONFIG = ROOT / 'historical_workflow_config.json'
STATE = ROOT / 'output/historical_campaign/state.json'
REPORT = ROOT / 'output/historical_campaign/CONTINUIDAD.md'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def pending_units(estimate, completed_hashes=()):
    """Return contiguous pending ranges while preserving <=100 GiB batches."""
    by_month = {row['month']: row for row in estimate['months']}
    units = []
    for number, batch in enumerate(estimate['batches'], 1):
        current = []
        for month in batch['months']:
            if (by_month[month]['status'] == 'completed'
                    or by_month[month]['sql_sha256'] in completed_hashes):
                if current:
                    units.append((number, current)); current = []
            else:
                current.append(month)
        if current:
            units.append((number, current))
    return units


def write_checkpoint(config, estimate, events, reason):
    ledger = refresh()
    now_month = datetime.now().astimezone().strftime('%Y-%m')
    used = ledger['totals_by_calendar_month'].get(now_month, 0)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        'schema_version': 1, 'updated_at': datetime.now().astimezone().isoformat(),
        'stop_reason': reason, 'project': config['project'], 'profile': config['profile'],
        'monthly_cap_gib': config['monthly_ledger_gib'], 'ledger_month': now_month,
        'ledger_bytes': used, 'ledger_gib': used / GIB, 'events': events,
        'estimate': str(Path(estimate).resolve()),
    }
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = [
        '# Continuidad de extracción histórica', '',
        f'- Actualizado: {state["updated_at"]}', f'- Motivo de detención: {reason}',
        f'- Proyecto usado: `{config["project"]}`', f'- Perfil: `{config["profile"]}`',
        f'- Mes de cuota local: `{now_month}`', f'- Uso registrado este mes: {used/GIB:.3f} GiB',
        f'- Techo preventivo: {config["monthly_ledger_gib"]:.3f} GiB', '',
        '## Operaciones de esta sesión', ''
    ]
    lines += [f'- {event}' for event in events] or ['- No se ejecutaron bloques.']
    lines += ['', '## Cómo continuar en otra computadora', '',
              '1. Copiar todo el repositorio, incluida la carpeta `output`.',
              '2. Usar Python 3.11 o posterior, crear un entorno virtual y ejecutar `pip install -r requirements.txt`.',
              '3. Ejecutar `gcloud auth application-default login` con el usuario autorizado.',
              '4. Cambiar solamente `project` en `historical_workflow_config.json` si corresponde.',
              '5. Confirmar que la facturación esté inhabilitada.',
              '6. Ejecutar primero `python historical_campaign.py --prepare`.',
              '7. Para continuar realmente, ejecutar `python historical_campaign.py --execute`.', '',
              'El programa vuelve a estimar cada unidad, reconoce recibos existentes, comprueba el techo mensual y se detiene antes de excederlo. '
              'Cambiar de proyecto o equipo no debe utilizarse para evadir cuotas; conserve los recibos para evitar consultas repetidas.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    return state


def campaign(config_path, estimate_path, execute=False):
    config = load(config_path)
    estimate = load(estimate_path)
    require_unbilled_project(config['project'])
    ledger = refresh()
    month = datetime.now().astimezone().strftime('%Y-%m')
    cap = int(config['monthly_ledger_gib'] * GIB)
    used = ledger['totals_by_calendar_month'].get(month, 0)
    events = []
    completed_hashes = {entry['sql_sha256'] for entry in ledger['entries'] if entry.get('sql_sha256')}
    for batch_number, months in pending_units(estimate, completed_hashes):
        estimates = [row['estimated_bytes'] for row in estimate['months'] if row['month'] in months]
        reserved = sum(estimates)
        if used + reserved > cap:
            reason = f'stop preventivo antes del bloque {batch_number}: el estimado superaría el techo mensual'
            write_checkpoint(config, estimate_path, events, reason)
            print(reason); return
        start, end = months[0], months[-1]
        plan = make_plan(start, end, config_path)
        events.append(f'Bloque {batch_number} ({start} a {end}) planificado: {reserved/GIB:.3f} GiB estimados.')
        if not execute:
            reason = 'preparación finalizada; ninguna consulta real fue ejecutada'
            write_checkpoint(config, estimate_path, events, reason)
            print(f'READY: {plan}'); return
        execute_plan(plan)
        ledger = refresh(); used = ledger['totals_by_calendar_month'].get(month, 0)
        events.append(f'Bloque {batch_number} completado; registro mensual acumulado: {used/GIB:.3f} GiB.')
        write_checkpoint(config, estimate_path, events, 'ejecución en curso; punto de recuperación actualizado')
    write_checkpoint(config, estimate_path, events, 'todos los bloques pendientes fueron procesados')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true', help='Validate and freeze only the next block')
    mode.add_argument('--execute', action='store_true', help='Execute blocks until the preventive cap')
    parser.add_argument('--config', default=str(DEFAULT_CONFIG))
    parser.add_argument('--estimate', default=str(DEFAULT_ESTIMATE))
    args = parser.parse_args()
    campaign(args.config, args.estimate, execute=args.execute)
