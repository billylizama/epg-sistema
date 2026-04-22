"""
Unifica un nombre de mencion: reemplaza VIEJO por NUEVO en programas y
registros_gastos. Maneja el caso UNIQUE: si NUEVO ya existe en programas
(porque hay duplicado), fusiona borrando la fila VIEJO y pasando los
registros al NUEVO.

Uso (desde la carpeta del proyecto):
    python unificar_mencion.py "VIEJO" "NUEVO"

Ejemplo:
    python unificar_mencion.py \\
      "PROGRAMA DE MAESTRIA EN GEOMECANICA Y MINERIA" \\
      "MAESTRIA EN GEOMECANICA MINERA"

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
        print('Uso: python unificar_mencion.py "VIEJO" "NUEVO"')
        sys.exit(1)

    viejo = sys.argv[1]
    nuevo = sys.argv[2]

    if viejo == nuevo:
        print('VIEJO y NUEVO son iguales. Nada que hacer.')
        sys.exit(0)

    if not os.path.exists(DB_PATH):
        print(f'ERROR: no existe {DB_PATH}')
        sys.exit(1)

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = os.path.join(BACKUP_DIR, f'epg_pre_unificar_mencion_{slug(nuevo)}_{ts}.db')
    shutil.copy2(DB_PATH, backup)
    print(f'Backup creado: {backup}')
    print(f'\nMergeando mencion:\n  "{viejo}"\n  -> "{nuevo}"')

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Palabra clave: tomo la palabra mas larga para buscar variantes relacionadas
    palabras = sorted(viejo.split(), key=len, reverse=True)
    palabra = palabras[0] if palabras else viejo
    print('\nANTES (coincidencias parciales con "%s"):' % palabra)
    for t in ('programas', 'registros_gastos'):
        cur.execute(
            f"SELECT mencion, COUNT(*) FROM {t} "
            "WHERE mencion LIKE ? GROUP BY mencion",
            (f'%{palabra}%',)
        )
        for row in cur.fetchall():
            print(f'  {t}: {row}')

    cur.execute('BEGIN')
    try:
        # 1) Renombrar registros_gastos (no tiene UNIQUE)
        r2 = cur.execute(
            "UPDATE registros_gastos SET mencion=? WHERE mencion=?",
            (nuevo, viejo)
        ).rowcount

        # 2) Programas: manejar UNIQUE
        cur.execute("SELECT id, ingresos FROM programas WHERE mencion=?", (viejo,))
        prog_viejo = cur.fetchone()
        cur.execute("SELECT id, ingresos FROM programas WHERE mencion=?", (nuevo,))
        prog_nuevo = cur.fetchone()

        r1 = 0
        if prog_viejo and prog_nuevo:
            # Ambos existen: fusion. Sumar ingresos al nuevo, borrar viejo.
            nuevo_ingresos = (prog_viejo[1] or 0) + (prog_nuevo[1] or 0)
            cur.execute("UPDATE programas SET ingresos=? WHERE id=?",
                        (nuevo_ingresos, prog_nuevo[0]))
            cur.execute("DELETE FROM programas WHERE id=?", (prog_viejo[0],))
            print('Fusion: programa VIEJO borrado, ingresos sumados al NUEVO.')
            r1 = 1
        elif prog_viejo and not prog_nuevo:
            # Solo existe VIEJO: renombrar
            cur.execute("UPDATE programas SET mencion=? WHERE id=?",
                        (nuevo, prog_viejo[0]))
            r1 = 1
        # si solo NUEVO existe, no hay nada que tocar en programas

        con.commit()
    except Exception as e:
        con.rollback()
        print(f'ERROR: {e}')
        sys.exit(1)

    print(f'\nUPDATE programas: {r1} fila(s)')
    print(f'UPDATE registros_gastos: {r2} fila(s)')

    print('\nDESPUES:')
    for t in ('programas', 'registros_gastos'):
        cur.execute(
            f"SELECT mencion, COUNT(*) FROM {t} "
            "WHERE mencion LIKE ? GROUP BY mencion",
            (f'%{palabra}%',)
        )
        for row in cur.fetchall():
            print(f'  {t}: {row}')

    con.close()
    print('\nListo.')


if __name__ == '__main__':
    main()
