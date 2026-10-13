#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
remove_rendertype_from_xml.py - Einmaliges Aufraeumen der config_xml.

Entfernt alle <rendertype>-Knoten, die als Kind von <type> unter einer
<camera> liegen. Die flachen <rendertype type_name=...>-Knoten auf
oberster Ebene werden ebenfalls entfernt, falls vorhanden.

Vor der Aenderung wird eine Sicherungskopie angelegt:
    <xmlfile>.bak

Verwendung:
    python remove_rendertype_from_xml.py
    python remove_rendertype_from_xml.py "C:/Pfad/zur/dateimeister_configfiles.xml"

Ohne Argument wird der Pfad aus der ini-Datei gelesen. Dazu wird
configparser benutzt, damit dieselbe Quelldatei wie das Programm
verwendet wird.
"""

import configparser
import os
import shutil
import sys
import xml.etree.ElementTree as ET


def find_xml_from_ini(inifile="Dateimeister.ini"):
    """Liest Globals.config_files_xml aus der ini-Datei."""
    if not os.path.isfile(inifile):
        raise FileNotFoundError(
            f"Ini-Datei nicht gefunden: {inifile}\n"
            f"Bitte die XML-Datei als Argument uebergeben."
        )
    cp = configparser.ConfigParser()
    cp.read(inifile, encoding="utf-8")
    xmlfile = cp.get("misc", "config_files_xml", fallback=None)
    if not xmlfile:
        raise ValueError(
            f"In der Ini-Datei {inifile} fehlt der Eintrag "
            f"[misc] config_files_xml."
        )
    return xmlfile


def remove_rendertype(xmlfile):
    """Entfernt alle rendertype-Knoten aus der XML und schreibt sie neu."""
    if not os.path.isfile(xmlfile):
        print(f"XML-Datei nicht gefunden: {xmlfile}")
        return 1

    # Backup anlegen, aber eine eventuell schon vorhandene Sicherung
    # nicht ueberschreiben (falls das Skript versehentlich zweimal laeuft).
    backup = xmlfile + ".bak"
    if os.path.exists(backup):
        print(f"Sicherung existiert schon, wird nicht ueberschrieben: {backup}")
    else:
        shutil.copy2(xmlfile, backup)
        print(f"Sicherung angelegt: {backup}")

    tree = ET.parse(xmlfile)
    root = tree.getroot()

    removed = 0

    # 1) rendertype als Kind von <type> unter <camera>
    for camera in root.findall("camera"):
        for ctype in camera.findall("type"):
            for rt in ctype.findall("rendertype"):
                ctype.remove(rt)
                removed += 1

    # 2) flache rendertype-Knoten auf oberster Ebene (Legacy)
    for rt in root.findall("rendertype"):
        root.remove(rt)
        removed += 1

    # Einrueckung von ET uebernehmen, damit die Datei lesbar bleibt
    try:
        ET.indent(root)
    except AttributeError:
        # ET.indent gibt es erst ab Python 3.9 - hier sollte es vorhanden
        # sein, aber falls nicht, schreiben wir ohne Einrueckung.
        pass

    tree.write(xmlfile, encoding="iso-8859-1", xml_declaration=True)
    print(f"{removed} rendertype-Knoten entfernt.")
    print(f"XML neu geschrieben: {xmlfile}")
    return 0


def main():
    if len(sys.argv) > 1:
        xmlfile = sys.argv[1]
    else:
        try:
            xmlfile = find_xml_from_ini()
        except (FileNotFoundError, ValueError) as e:
            print(e)
            return 1
    print(f"Verwende XML-Datei: {xmlfile}")
    return remove_rendertype(xmlfile)


if __name__ == "__main__":
    sys.exit(main())