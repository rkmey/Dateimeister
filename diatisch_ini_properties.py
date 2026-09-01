
# ---------------------------------------------------------------------------
# Spezifikation für Dateimeister.ini
# Key:   (section, name)   -- Tupel, damit gleichnamige Keys in
#                              unterschiedlichen Sections kein Problem sind
# Value: dict mit
#   "var":       Name des Attributs, unter dem der Wert abgelegt wird
#                (z.B. "indir" -> spaeter self.indir bzw. cfg.indir)
#   "type":      "str" (default) / "int" / "bool"
#                steuert die Konvertierung des rohen String-Werts
#   "checkdir":  "yes"/"no"  -> Wert muss ein existierendes Verzeichnis sein
#   "checkfile": "yes"/"no"  -> Wert muss eine existierende Datei sein
#   "action":    "error"/"warn"
#                "error" -> Meldung ausgeben, Programm beendet sich am Ende
#                           mit rc = 1 (siehe load_and_validate_ini)
#                "warn"  -> Meldung ausgeben, Programm läuft weiter
# ---------------------------------------------------------------------------
dict_ini_spec = {
    ("dirs", "indir"):                     {"var": "default_indir",             "type": "str", "checkdir": "yes", "checkfile": "no",  "action": "error"},
    ("dirs", "datadir"):                   {"var": "datadir",                   "type": "str", "checkdir": "yes", "checkfile": "no",  "action": "error"},
    ("dirs", "config_files_subdir"):       {"var": "config_files_subdir",       "type": "str", "checkdir": "no",  "checkfile": "no",  "action": "error"},
    ("dirs", "cmd_files_subdir"):          {"var": "cmd_files_subdir",          "type": "str", "checkdir": "no",  "checkfile": "no",  "action": "error"},

    ("misc", "config_files_diatisch_xml"): {"var": "config_files_xml",          "type": "str", "checkdir": "no",  "checkfile": "yes", "action": "error"},
    ("misc", "templatefile_diatisch"):     {"var": "templatefile",              "type": "str", "checkdir": "no",  "checkfile": "yes", "action": "error"},
    ("misc", "max_configfiles_diatisch"):  {"var": "max_configfiles",           "type": "int", "action": "error"},
    ("misc", "max_indirs_diatisch"):       {"var": "max_indirs",                "type": "int", "action": "error"},
    ("misc", "max_outdirs_diatisch"):      {"var": "max_outdirs",               "type": "int", "action": "error"},
    ("misc", "uncomment"):                 {"var": "uncomment",                 "type": "str", "action": "error"},
    ("misc", "platform"):                  {"var": "platform",                  "type": "str", "action": "error"}
}

