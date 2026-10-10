#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnose: Wo liegen die Dateien eines Verzeichnisses?

Zaehlt pro Ordner direkt unter <pfad> zwei Werte:
  roh     : alles, was ein einfaches os.walk findet (so zaehlte der alte Fortschrittsbalken)
  gescannt: nur die Ordner, die der Dateimeister tatsaechlich betritt
            (gleiche Regeln wie dateimeister_generator.prune_dirs)
Zusaetzlich: wie viele Junctions dabei gefunden wurden (moegliche Doppelzaehlung).

Aufruf:  python zaehle_dateien.py C:\\
Wichtig: im Dateimeister-Ordner starten, damit dateimeister_generator importiert werden kann.
"""
import os
import sys
import time

try:
    import dateimeister_generator as DG
    prune = DG.prune_dirs  # prune(root, dirs, indir)
    print("Regeln aus dateimeister_generator.py (SKIP_DIRS_TOP / SKIP_DIRS_ANY) uebernommen.")
except Exception as e:
    print(f"Hinweis: dateimeister_generator nicht importierbar ({type(e).__name__}: {e}), nutze lokale Kopie der Regeln.")
    SKIP_DIRS_TOP = {
        '$recycle.bin', 'system volume information', 'windows',
        '$windows.~bt', '$windows.~ws', 'recovery', 'config.msi',
        'program files', 'program files (x86)', 'programdata',
    }
    SKIP_DIRS_ANY = {'appdata'}
    def prune(root, dirs, indir):
        at_top = os.path.normcase(os.path.normpath(root)) == os.path.normcase(os.path.normpath(indir))
        dirs[:] = [d for d in dirs
                   if d.lower() not in SKIP_DIRS_ANY
                   and not (at_top and d.lower() in SKIP_DIRS_TOP)
                   and not os.path.isjunction(os.path.join(root, d))]


def count(path, use_prune, base):
    """Gibt (Dateianzahl, Junction-Anzahl) fuer path zurueck."""
    files_n = 0
    junctions = 0
    for root, dirs, files in os.walk(path):
        junctions += sum(1 for d in dirs if os.path.isjunction(os.path.join(root, d)))
        if use_prune:
            prune(root, dirs, base)
        files_n += len(files)
    return files_n, junctions


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "C:\\"
    if not os.path.isdir(base):
        print(f"Kein Verzeichnis: {base}")
        return 1

    rows = []
    loose_files = 0   # Dateien direkt in base, gehoeren zu keinem Unterordner
    t0 = time.time()
    with os.scandir(base) as it:
        entries = sorted(it, key=lambda e: e.name.lower())
    for entry in entries:
        if entry.is_file(follow_symlinks=False):
            loose_files += 1
            continue
        if not entry.is_dir(follow_symlinks=False):
            continue
        # Der Ordner selbst zaehlt nur dann zum Scan, wenn prune ihn nicht aussortiert
        probe = [entry.name]
        prune(base, probe, base)
        in_scan = bool(probe)
        raw, jn = count(entry.path, use_prune=False, base=base)
        scanned = count(entry.path, use_prune=True, base=base)[0] if in_scan else 0
        rows.append((entry.name, raw, scanned, jn))
        print(f"  {entry.name:<40s} roh {raw:>9d}   gescannt {scanned:>9d}   Junctions {jn:>4d}", flush=True)

    tot_raw = sum(r[1] for r in rows) + loose_files
    tot_scan = sum(r[2] for r in rows) + loose_files
    print()
    print(f"Dateien direkt in {base}: {loose_files}")
    print(f"Summe roh      : {tot_raw}")
    print(f"Summe gescannt : {tot_scan}")
    if tot_raw:
        print(f"Anteil gescannt: {tot_scan / tot_raw * 100:.1f} %  (Rest = ausgeschlossen oder ueber Junctions mehrfach gezaehlt)")
    print()
    print("Groesste Ordner (roh):")
    for name, raw, scanned, jn in sorted(rows, key=lambda r: r[1], reverse=True)[:10]:
        print(f"  {name:<40s} {raw:>9d}  davon gescannt {scanned:>9d}")
    print(f"\nDauer: {time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
