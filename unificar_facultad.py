"""
Unifica un nombre de facultad: reemplaza VIEJO por NUEVO en las tablas
programas y registros_gastos.

Uso (desde la carpeta del proyecto):
    python unificar_facultad.py "FACULTAD DE INGENIERIA DE MINAS" "FAC INGENIERIA DE MINAS"

Hace backup automatico de epg.db antes de modificar.
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database', 'epg.db')
BACKUP_DIR = os.path.join(BASE_DIR, 'database', 'backups')


def slug(texto):
    return ''.join(c if c.isalnum() else '_' for c in texto.lower())[:40]


def main():
    if len(sys.argv) != 3:
        print('Uso: python unificar_facultad.py "VIEJO" "NUEVO"')
        print('Ej:  python unificar_facultad.py '
              '"FACULTAD DE INGENIERIA DE MINAS" "FAC INGENIERIA DE MINAS"')
        sys.exit(1)

    viejo = sys.argv[1]
    nuevo = sys.argv[2]

    if not os.path.exists(DB_PATH):
        print(f'ERROR: no existe {DB_PATH}')
        sys.exit(1)

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = os.path.join(BACKUP_DIR, f'epg_pre_unificar_{slug(nuevo)}_{ts}.db')
    shutil.copy2(DB_PATH, backup)
    print(f'Backup creado: {backup}')
    print(f'\nReemplazando:\n  "{viejo}"\n  -> "{nuevo}"')

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    print('\nANTES (coincidencias parciales para contexto):')
    palabra = viejo.split()[-1] if viejo.split() else viejo
    for t in ('programas', 'registros_gastos'):
        cur.execute(
            f"SELECT facultad, COUNT(*) FROM {t} "
            "WHERE facultad LIKE ? GROUP BY facultad",
            (f'%{palabra}%',)
        )
        for row in cur.fetchall():
            print(f'  {t}: {row}')

    r1 = cur.execute(
        "UPDATE programas SET facultad=? WHERE facultad=?",
        (nuevo, viejo)
    ).rowcount
    r2 = cur.execute(
        "UPDATE registros_gastos SET facultad=? WHERE facultad=?",
        (nuevo, viejo)
    ).rowcount
    con.commit()

    print(f'\nUPDATE programas: {r1} fila(s)')
    print(f'UPDATE registros_gastos: {r2} fila(s)')

    print('\nDESPUES:')
    for t in ('programas', 'registros_gastos'):
        cur.execute(
            f"SELECT facultad, COUNT(*) FROM {t} "
            "WHERE facultad LIKE ? GROUP BY facultad",
            (f'%{palabra}%',)
        )
        for row in cur.fetchall():
            print(f'  {t}: {row}')

    con.close()
    print('\nListo.')


if __name__ == '__main__':
    main()
