"""
ini_validator.py

Deklarative Validierung von .ini-Konfigurationsdateien UND Zuweisung der
Werte auf Attribute (z.B. self.indir), gesteuert über eine Spezifikation.

Idee: Statt für jeden Ini-Eintrag manuell try/except UND eine manuelle
Zuweisung "self.xyz = config.get(...)" zu schreiben, wird eine
Spezifikation (dict_ini_spec) gepflegt, die pro Eintrag beschreibt:
    - "var":      unter welchem Attributnamen der Wert verfügbar sein soll
    - "type":     wie der String-Wert konvertiert werden soll (str/int/bool/dict) if dict convert by using ast.literal_eval
    - "checkdir": ob der Wert ein existierendes Verzeichnis sein muss
    - "checkfile":ob der Wert eine existierende Datei sein muss
    - "action":   was bei einem Verstoss passieren soll ("warn"/"error")

Wichtig zu "var": Dort steht NUR der nackte Attributname (z.B. "indir"),
nicht "self.indir" - denn die Funktion schreibt die Werte per setattr()
auf ein beliebiges Zielobjekt. Ob daraus dann self.indir oder cfg.indir
wird, entscheidest du beim Aufruf über den Parameter `target`:

    - Kein target angegeben:
          cfg = load_and_validate_ini("Dateimeister.ini")
          -> Zugriff über cfg.indir, cfg.mpv_path, ...
    - target=self (innerhalb einer Klassenmethode, z.B. __init__):
          load_and_validate_ini("Dateimeister.ini", target=self)
          -> Zugriff über self.indir, self.mpv_path, ...
          (das zurückgegebene cfg-Objekt bekommst du trotzdem, falls
           du es zusätzlich brauchst)

check_ini_config() prüft alle Einträge und sammelt Meldungen.
load_and_validate_ini() lädt die Ini-Datei, prüft sie, weist die Werte
zu und beendet das Programm bei Bedarf geordnet mit rc = 1 (erst NACHDEM
alle Fehler ausgegeben wurden, damit man alle Probleme auf einen Blick sieht).
"""

import configparser
import os
import sys
import types
import ast
import inspect
import tools # damit stehen die in tools definierten Klassen als Target zur Verfügung

def _report(msg):
    """Zentrale Ausgabestelle - später ggf. gegen logging.warning/error austauschen."""
    print(msg)


def _convert_value(raw_value, type_name, section, name, action, problems):
    """
    Konvertiert den rohen String-Wert gemäss `type_name`.
    Bei Konvertierungsfehler (z.B. "abc" als int) wird das wie ein
    Validierungsfehler behandelt und None zurückgegeben.
    """
    try:
        if type_name == "str":
            return raw_value
        elif type_name == "dict":
            return ast.literal_eval(raw_value)
        elif type_name == "int":
            return int(raw_value)
        elif type_name == "bool":
            return raw_value.strip().lower() in ("1", "true", "yes", "ja", "on")
        else:
            detail = f"Nicht unterstützter Datentyp in Spec: [{section}] {name} type='{type_name}'"
            _report(f"[SPEC-ERROR] {detail}")
            problems.append({
                "section": section, "name": name, "kind": "unsupported_type",
                "action": "error", "message": detail,
            })
            sys.exit(1)  # sofortiger Abbruch, das ist ein Bug in dict_ini_spec, kein Laufzeitproblem    
    except ValueError:
        detail = f"Ini-Wert kann nicht nach '{type_name}' konvertiert werden: [{section}] {name} = {raw_value}"
        _report(f"[{action.upper()}] {detail}")
        problems.append({
            "section": section, "name": name, "kind": "type_error",
            "action": action, "message": detail,
        })
        return None


def check_ini_config(config, spec, target=None, target_registry=None):
    """
    Prüft eine bereits geladene configparser.ConfigParser-Instanz gegen `spec`
    UND weist bei Erfolg die (typkonvertierten) Werte den in `spec` unter
    "var" angegebenen Attributnamen zu.

    Für jeden Eintrag wird geprüft:
      1. Existiert Section + Key?
      2. Ist der Wert nicht leer?
      3. Lässt sich der Wert gemäss "type" konvertieren?
      4. Falls checkdir=yes:  ist der Wert ein existierendes Verzeichnis?
      5. Falls checkfile=yes: ist der Wert eine existierende Datei?

    Die Werte werden immer auf einem neu erzeugten `types.SimpleNamespace`
    (cfg) abgelegt. Falls zusätzlich `target` übergeben wird (z.B. self),
    werden die Attribute PARALLEL auch dort per setattr() gesetzt.

    Rückgabe:
        (cfg, has_errors, has_warnings, problems)
    """
    target_registry = target_registry or {}
    has_errors = False
    has_warnings = False
    problems = []
    cfg = types.SimpleNamespace()

    for (section, name), rules in spec.items():
        action = rules.get("action", "warn")
        varname = rules.get("var", name)  # Fallback: Ini-Name, falls "var" mal vergessen wurde
        type_name = rules.get("type", "str")
        check_dir = rules.get("checkdir", "no") == "yes"
        check_file = rules.get("checkfile", "no") == "yes"
        thistarget = rules.get("target")

        def _flag(kind, detail):
            nonlocal has_errors, has_warnings
            _report(f"[{action.upper()}] {detail}")
            problems.append({
                "section": section, "name": name, "kind": kind,
                "action": action, "message": detail,
            })
            if action == "error":
                has_errors = True
            else:
                has_warnings = True

        # 1. Section/Key vorhanden?
        if not config.has_section(section) or not config.has_option(section, name):
            _flag("missing", f"Ini-Eintrag fehlt: [{section}] {name}")
            continue  # ohne Wert keine weitere Prüfung, kein setattr

        raw_value = config.get(section, name).strip()

        # 2. Leerer Wert?
        if raw_value == "":
            _flag("empty", f"Ini-Eintrag ist leer: [{section}] {name}")
            continue

        # 3. Verzeichnis-Prüfung (auf dem ROHEN String, unabhängig vom Zieltyp)
        if check_dir and not os.path.isdir(raw_value):
            _flag("dir_missing", f"Verzeichnis existiert nicht: [{section}] {name} = {raw_value}")

        # 4. Datei-Prüfung
        if check_file and not os.path.isfile(raw_value):
            _flag("file_missing", f"Datei existiert nicht: [{section}] {name} = {raw_value}")

        # 5. Typkonvertierung + Zuweisung
        value = _convert_value(raw_value, type_name, section, name, action, problems)
        if value is None and type_name != "str":
            has_errors |= (action == "error")
            has_warnings |= (action == "warn")
            continue  # Konvertierung fehlgeschlagen -> kein setattr

        setattr(cfg, varname, value)
        if thistarget is not None:
            resolved = target_registry.get(thistarget)
            if resolved is None:
                print(f"[SPEC-ERROR] Unbekanntes target '{thistarget}' - nicht in target_registry")
                sys.exit(1)
            setattr(resolved, varname, value)
        elif target is not None: # global target given by caller
            setattr(target, varname, value)

    return cfg, has_errors, has_warnings, problems


def load_and_validate_ini(ini_path, spec=None, target=None, target_registry=None, exit_on_error=True):
    """
    Lädt die Ini-Datei per configparser, validiert sie gegen `spec`
    (Default: dict_ini_spec oben) und weist die Werte den konfigurierten
    Attributnamen zu (siehe check_ini_config).

    Falls Einträge mit action="error" verletzt sind, werden ZUERST alle
    Fehlermeldungen ausgegeben (nicht beim ersten Fehler abbrechen) und
    danach - falls exit_on_error=True - das Programm mit sys.exit(1) beendet.

    Parameter:
        ini_path:       Pfad zur .ini-Datei
        spec:           Spezifikation, Default dict_ini_spec
        target:         optionales Objekt (z.B. self), auf das die Werte
                         zusaetzlich per setattr() geschrieben werden
        exit_on_error:  bei True -> sys.exit(1) bei Fehlern

    Rückgabe: (cfg, has_errors, has_warnings, problems)
        cfg ist ein types.SimpleNamespace mit allen erfolgreich gelesenen
        Werten, z.B. cfg.indir, cfg.mpv_path, cfg.max_configfiles (als int).
    """
    if spec is None:
        spec = dict_ini_spec

    #print(f"spec = {spec}")
    config = configparser.ConfigParser()
    read_files = config.read(ini_path, encoding="utf-8")

    if not read_files:
        print(f"[ERROR] Ini-Datei konnte nicht gelesen werden oder existiert nicht: {ini_path}")
        if exit_on_error:
            sys.exit(1)
        return types.SimpleNamespace(), True, False, []

    cfg, has_errors, has_warnings, problems = check_ini_config(config, spec, target=target, target_registry=target_registry)

    if has_errors:
        anzahl = sum(1 for p in problems if p["action"] == "error")
        print(f"--- {anzahl} Fehler in der Konfigurationsdatei '{ini_path}' gefunden. ---")
        print("Programm wird beendet (rc=1).")
        if exit_on_error:
            sys.exit(1)
    elif has_warnings:
        anzahl = sum(1 for p in problems if p["action"] == "warn")
        print(f"--- {anzahl} Warnung(en) in der Konfigurationsdatei '{ini_path}'. Programm läuft weiter. ---")

    return cfg, has_errors, has_warnings, problems


# ---------------------------------------------------------------------------
# Beispiel-Nutzung 1: Werte über eigenständiges cfg-Objekt
#
#   from ini_validator import load_and_validate_ini
#
#   def main():
#       cfg, has_errors, has_warnings, problems = load_and_validate_ini(
#           "Dateimeister.ini"
#       )
#       print(cfg.indir, cfg.mpv_path, cfg.max_configfiles)  # max_configfiles ist int!
#
# Beispiel-Nutzung 2: Werte direkt als self.xyz innerhalb einer Klasse
#
#   class Dateimeister:
#       def __init__(self, ini_path):
#           cfg, has_errors, has_warnings, problems = load_and_validate_ini(
#               ini_path, target=self
#           )
#           # ab hier direkt verfuegbar:
#           print(self.indir, self.mpv_path, self.max_configfiles)
#
# Wenn du testweise nur prüfen, aber NICHT beenden willst:
#   cfg, has_errors, has_warnings, problems = load_and_validate_ini(
#       "Dateimeister.ini", exit_on_error=False
#   )
#   if has_errors:
#       # eigene Fehlerbehandlung, z.B. Dialog in der GUI anzeigen
#       ...
# ---------------------------------------------------------------------------

from dateimeister_ini_properties import dict_ini_spec
if __name__ == "__main__":
    # Kleiner Selbsttest: python ini_validator.py Dateimeister.ini
    pfad = sys.argv[1] if len(sys.argv) > 1 else "Dateimeister.ini"
    import tools
    cfg, has_errors, has_warnings, problems = load_and_validate_ini(pfad, spec = dict_ini_spec, target_registry={"Globals": tools.Globals})
    print("Ini-Datei ist vollständig und gültig.")
    print("Beispiel: cfg.max_configfiles =", cfg.max_configfiles, type(cfg.max_configfiles), cfg.templatefile_diatisch, cfg.dict_proctypes, tools.Globals.uncomment)