"""
Unifica la facultad de Contables: reemplaza
'FACULTAD DE CIENCIAS CONTABLES Y FINANCIERAS' -> 'FAC CIENCIAS CONTABLES'
en las tablas programas y registros_gastos.

Uso (desde la carpeta del proyecto):
    python unificar_facultad_contables.py

Hace backup automatico de epg.db antes de modificar.
"""
import os
import shutil
import sqlite3
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database', 'epg.db')
BACKUP_DIR = os.path.join(BASE_DIR, 'database', 'backups')

VIEJO = 'FACULTAD DE CIENCIAS CONTABLES Y FINANCIERAS'
NUEVO = 'FAC CIENCIAS CONTABLES'


def main():
    if not os.path.exists(DB_PATH):
        print(f'ERROR: no existe {DB_PATH}')
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = os.path.join(BACKUP_DIR, f'epg_pre_unificar_contables_{ts}.db')
    shutil.copy2(DB_PATH, backup)
    print(f'Backup creado: {backup}')

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    print('\nANTES:')
    for t in ('programas', 'registros_gastos'):
        cur.execute(f"SELECT facultad, COUNT(*) FROM {t} "
                    "WHERE facultad LIKE '%CONTABLES%' GROUP BY facultad")
        for row in cur.fetchall():
            print(f'  {t}: {row}')

    r1 = cur.execute(
        "UPDATE programas SET facultad=? WHERE facultad=?",
        (NUEVO, VIEJO)
    ).rowcount
    r2 = cur.execute(
        "UPDATE registros_gastos SET facultad=? WHERE facultad=?",
        (NUEVO, VIEJO)
    ).rowcount
    con.commit()

    print(f'\nUPDATE programas: {r1} fila(s)')
    print(f'UPDATE registros_gastos: {r2} fila(s)')

    print('\nDESPUES:')
    for t in ('programas', 'registros_gastos'):
        cur.execute(f"SELECT facultad, COUNT(*) FROM {t} "
                    "WHERE facultad LIKE '%CONTABLES%' GROUP BY facultad")
        for row in cur.fetchall():
            print(f'  {t}: {row}')

    con.close()
    print('\nListo.')


if __name__ == '__main__':
    main()
