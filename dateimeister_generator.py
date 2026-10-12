#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

import sys
import os.path
import re
from datetime import datetime, timezone
import functools
import Dateimeister as DM

# Ordner, die beim rekursiven Scan nicht betreten werden (Namensvergleich ohne Gross/Kleinschreibung).
# Dort liegen keine Fotos, die man verwalten will, aber viele defekte/gesperrte Dateien.
#
# SKIP_DIRS_TOP: Systemordner, nur DIREKT unter dem gewaehlten Eingabeverzeichnis (indir) ausgeschlossen.
#                Scannt man C:\, sind C:\Windows usw. draussen; ein eigener Ordner 'Windows' oder
#                'Recovery' irgendwo tiefer in den Fotos wird dagegen normal gescannt.
# SKIP_DIRS_ANY: auf jeder Ebene ausgeschlossen. 'appdata' enthaelt viele Cache-Bilder.
#
# Die Listen stehen in Dateimeister.ini, Section [scan] (skip_dirs_top / skip_dirs_any) und werden beim
# Start mit configure_skip_dirs() gesetzt. Die Werte hier sind die Standardwerte, falls die ini sie nicht enthaelt.
DEFAULT_SKIP_DIRS_TOP = (
    '$recycle.bin', 'system volume information', 'windows',
    '$windows.~bt', '$windows.~ws', 'recovery', 'config.msi',
    'program files', 'program files (x86)', 'programdata',
)
DEFAULT_SKIP_DIRS_ANY = ('appdata',)
SKIP_DIRS_TOP = set(DEFAULT_SKIP_DIRS_TOP)
SKIP_DIRS_ANY = set(DEFAULT_SKIP_DIRS_ANY)

def parse_dir_list(text, default):
    """Wandelt einen ini-Wert (Eintraege durch Komma und/oder Zeilenumbruch getrennt) in ein Set kleingeschriebener
    Ordnernamen um. None oder leer -> default; 'none' -> leere Menge (nichts ausschliessen)."""
    if text is None or not str(text).strip():
        return set(default)
    if str(text).strip().lower() == "none":
        return set()
    items = re.split(r"[,\r\n]+", str(text))
    return {i.strip().strip('"').lower() for i in items if i.strip()}

def configure_skip_dirs(top_text, any_text, verbose = True):
    """Setzt SKIP_DIRS_TOP / SKIP_DIRS_ANY aus den ini-Werten (Strings oder None)."""
    global SKIP_DIRS_TOP, SKIP_DIRS_ANY
    SKIP_DIRS_TOP = parse_dir_list(top_text, DEFAULT_SKIP_DIRS_TOP)
    SKIP_DIRS_ANY = parse_dir_list(any_text, DEFAULT_SKIP_DIRS_ANY)
    if verbose:
        print("Scan: ausgeschlossen direkt unter indir:", ", ".join(sorted(SKIP_DIRS_TOP)) or "-")
        print("Scan: ausgeschlossen auf jeder Ebene:    ", ", ".join(sorted(SKIP_DIRS_ANY)) or "-")

def prune_dirs(root, dirs, indir):
    """Entfernt In-place (nur das beeinflusst os.walk) auszuschliessende Ordner aus dirs.
    root: aktuell besuchter Ordner, indir: Startverzeichnis des Scans.
    Junctions (z.B. 'Documents and Settings') werden auf jeder Ebene uebersprungen -> keine Doppelscans."""
    at_top = os.path.normcase(os.path.normpath(root)) == os.path.normcase(os.path.normpath(indir))
    dirs[:] = [d for d in dirs
               if d.lower() not in SKIP_DIRS_ANY
               and not (at_top and d.lower() in SKIP_DIRS_TOP)
               and not os.path.isjunction(os.path.join(root, d))]

def walk_files(indir):
    """os.walk mit den konfigurierten Ausschluessen (SKIP_DIRS_TOP / SKIP_DIRS_ANY, Junctions).
    Einzige Stelle, an der rekursiv gescannt wird: dateimeister() und count_files() nutzen sie beide,
    damit Zaehlung (Fortschrittsbalken) und Scan immer dieselben Ordner betreffen."""
    for root, dirs, files in os.walk(indir, topdown=True):
        prune_dirs(root, dirs, indir)
        yield root, dirs, files

def count_files(indir):
    """Anzahl der Dateien, die ein rekursiver Scan von indir verarbeiten wuerde (z.B. fuer files_total)."""
    return sum(len(files) for _root, _dirs, files in walk_files(indir))

# sort functions
def compare_name(a, b):
    if a.name < b.name:
        return -1
    elif a.name ==  b.name:
        return 0
    else:
        return 1

def compare_mts(a, b):
    am = os.stat(a).st_mtime
    bm = os.stat(b).st_mtime
    if am < bm:
        return -1
    elif am ==  bm:
        return 0
    else:
        return 1

def _sort_results(sort_method, dict_result, dict_result_all, dict_result_tooold):
    """Nur intern: sortiert die Ergebnis-Dicts fuer den Parameter sort_method von dateimeister(), den es
    fuer bestehende Aufrufer weiter gibt. Wer spaeter neu sortieren will, macht das selbst (der Generator
    scannt nur und liefert die Dicts).
    1 Name aufsteigend, 2 Name absteigend, 3 Aenderungsdatum aufsteigend, 4 Aenderungsdatum absteigend,
    sonst (z.B. 0) unveraendert, also in Scan-Reihenfolge.
    Der Zeitstempel jeder Datei wird nur einmal gelesen. Ist er nicht lesbar (Datei verschwunden, Zugriff
    verweigert), gilt 0.0, die Datei sortiert dann nach vorn, statt die ganze Sortierung abzubrechen."""
    mtime_cache = {}
    def mtime(path):
        if path not in mtime_cache:
            try:
                mtime_cache[path] = os.stat(path).st_mtime
            except OSError:
                mtime_cache[path] = 0.0
        return mtime_cache[path]

    if sort_method in (1, 2):
        key = lambda x: x[0]
    elif sort_method in (3, 4):
        key = lambda x: mtime(x[0])
    else: # no sort
        return dict_result, dict_result_all, dict_result_tooold
    reverse = sort_method in (2, 4)
    return (dict(sorted(dict_result.items(),       key = key, reverse = reverse)),
            dict(sorted(dict_result_all.items(),   key = key, reverse = reverse)),
            dict(sorted(dict_result_tooold.items(), key = key, reverse = reverse)))

# we have 3 procesing types: 1) list of full filenames (path/file), 2) directory not recursive, 3) directory recursive
def dateimeister(dateityp, endung, indir, outdir, addrelpath, recursive, newer, target_prefix, select_list, sort_method, busy_dialog, files_total, 
    top_text = None, any_text = None, debug = 'n'):
    global dict_result, dict_result_all, dict_result_tooold, dict_relpath
    # List all files and directories in the specified path, returns list
    #print("Files and Directories in '{:_<10}' typ '{:}' endung '{:}':". format(dateityp, endung, indir))
    print("Dateimeister addrelpath is: ", addrelpath)
    dict_result = {}
    dict_result_all = {} # we need all JPEG-Files for process_type "use_jpeg". Ignore timestamp modified
    dict_result_tooold = {} # we want to keep the files which are not copied because a newer target exist
    dict_relpath = {}
    list_suffixes = endung.split(',')
    configure_skip_dirs(top_text, any_text, verbose = True)
    
    ii = 0
    while ii < len(list_suffixes):
        suffix = list_suffixes[ii].strip()
        list_suffixes[ii] = suffix
        ii += 1

    if select_list: # comes from Diatisch
        fctr = 0
        files_total = len(select_list)
        for fullname in select_list:
            if os.path.isfile(fullname):
                filename = os.path.basename(fullname)
                root  = os.path.dirname(fullname)
                #print("generating entry for : " + str(filename))
                filename = re.sub(r"\\", "/", filename) # replace single backslash by slash
                fullname = os.path.join(root, filename)
                if not busy_dialog.cancelled:
                    sourcefile, targetfile, docopy, process = process_file(root, filename, fullname, dateityp, indir, outdir, list_suffixes, addrelpath, newer, target_prefix)
                else: 
                    return False
                targetroot = os.path.dirname(targetfile)
                targetfilename = os.path.basename(targetfile)
                fctr += 1
                busy_dialog.update_progress(fctr, files_total)
                targetfilename = '{:04d}_'.format(fctr) + targetfilename
                targetfile = os.path.join(targetroot, targetfilename)
                targetfile = re.sub(r"\\", "/", targetfile) # replace single backslash by slash
                
                if process == "j":
                    if dateityp.upper() == "JPEG":
                        dict_result_all[sourcefile] = targetfile # we need all jpeg-files regardless of copy-status
                if docopy == "j" or docopy == "o":
                    dict_result[sourcefile] = targetfile
                if docopy == "o": # too old
                    dict_result_tooold[sourcefile] = targetfile
    elif recursive == "n":
        # das hier ist für nicht rekursive Aufrufe. Man verarbeitet einfach nur Files
        # os.walk scheint immer rekursiv zu funktionieren
        with os.scandir(indir) as it:
            direntries = list(it)  # reads all of the directory entries
            direntries.sort(key=lambda x: x.name)
        root = indir
        fctr = 0
        for entry in direntries:
            if entry.is_file():
                filename = entry.name
                #print("generating entry for : " + str(filename))
                filename = re.sub(r"\\", "/", filename) # replace single backslash by slash
                fullname = os.path.join(root, filename)
                if not busy_dialog.cancelled:
                    sourcefile, targetfile, docopy, process = process_file(root, filename, fullname, dateityp, indir, outdir, list_suffixes, addrelpath, newer, target_prefix)
                else:
                    return False
                fctr += 1
                busy_dialog.update_progress(fctr, files_total)
                if process == "j":
                    if dateityp.upper() == "JPEG":
                        dict_result_all[sourcefile] = targetfile # we need all jpeg-files regardless of copy-status
                if docopy == "j" or docopy == "o":
                    dict_result[sourcefile] = targetfile
                if docopy == "o": # too old
                    dict_result_tooold[sourcefile] = targetfile
    else: # no list, recursive
        # für rekursive Aufrufe scheint os.walk besser geeignet, schneller und nimmt einem die Arbeit ab, selbst zu navigieren
        print("Files and Directories in '{:_<10}' typ '{:}' endung '{:}':". format(dateityp, endung, indir))
        fctr = 0
        for root, dirs, files in walk_files(indir):
            print("Dateimeister_generator DIRS {:s}".format(str(dirs))) if debug else True
            for filename in files:
                filename = re.sub(r"\\", "/", filename) # replace single backslash by slash
                fullname = os.path.join(root, filename)
                if not busy_dialog.cancelled:
                    sourcefile, targetfile, docopy, process = process_file(root, filename, fullname, dateityp, indir, outdir, list_suffixes, addrelpath, newer, target_prefix)
                else:
                    return False
                fctr += 1
                busy_dialog.update_progress(fctr, files_total)
                if process == "j":
                    if dateityp.upper() == "JPEG":
                        dict_result_all[sourcefile] = targetfile # we need all jpeg-files regardless of copy-status
                if docopy == "j" or docopy == "o":
                    dict_result[sourcefile] = targetfile
                if docopy == "o": # too old
                    dict_result_tooold[sourcefile] = targetfile
    # now sort results according to sort param
    dict_1, dict_2, dict_3 = _sort_results(sort_method, dict_result, dict_result_all, dict_result_tooold)
    if debug:
        for i in dict_1:
            print("E: {:32s} - {:32s} - {:s}".format(i, dict_1[i], str(datetime.fromtimestamp(os.stat(i).st_mtime))))
        
  
    return dict_1, dict_2, dict_3, dict_relpath
    
def process_file(root, filename, fullname, dateityp, indir, outdir, list_suffixes, addrelpath, newer, target_prefix):
    global dict_result, dict_result_all, dict_result_tooold, dict_relpath
    relpath = ""
    process = "n"
    docopy  = "n"
    sourcefile = ""
    targetfile = ""
    for suffix in list_suffixes:
        match = re.search(rf".*?\.{suffix}$", filename, re.IGNORECASE)
        if match:
            process = "j"
            #print("File " + filename + " matches: " + suffix)
            break
    if process == "j":
        if addrelpath == 'j':
            relpath  = re.sub(re.escape(indir), '', root)
            relpath  = re.sub(r'^[\\\/]', '', relpath)
            target_dir = outdir + '/' + relpath
        else: 
            target_dir = outdir
        if newer: # copy only if source file is newer
            statinfo = os.stat(fullname)
            st_mtime = statinfo.st_mtime
            strdatetime = datetime.fromtimestamp(st_mtime)
            # check if file exists in target-dir
            #print("F: " + fullname + " mstime " + str(strdatetime) + " relpath is: " + relpath)
            targetfilename = os.path.join(target_dir, target_prefix + filename)
            if os.path.isfile(targetfilename):
                st_mtime_target = os.stat(targetfilename).st_mtime
                strdatetime_target = datetime.fromtimestamp(st_mtime_target)
                #print("Targetfile " + filename + " exists in " + target_dir + " mstime " + str(st_mtime_target))
                if st_mtime > st_mtime_target:
                    docopy = "j"
                else: 
                    docopy = "o"
            else: # target does not exist
                a = 1
                docopy = "j"
                #print("Targetfile " + filename + " does not exists in " + target_dir)
        else: # copy anyway
            docopy = "j"
        sourcefile = os.path.join(root,       filename)
        #20260421 replace // at the beginning by \\ as windows interprets a slash in position 1 as "paramater follows"...
        if sourcefile.startswith("//"):        
            sourcefile = re.sub(r"/", r"\\", sourcefile) # replace single backslash by slash
        targetfile = os.path.join(target_dir, target_prefix + filename)
        targetfile = re.sub(r"\\", "/", targetfile) # replace single backslash by slash
        if dateityp.upper() == "JPEG":
            dict_result_all[sourcefile] = targetfile # we need all jpeg-files regardless of copy-status
    if docopy == "j" or docopy == "o":
        dict_result[sourcefile] = targetfile
        # we have to store relpath in dict_relpath for the delete script which deletes those relpaths if they are empty
        # after the files have been deleted  (undo copy). From the rightmst subdir to the left we check if relpath already exists if
        # yes we appen the rightmost portion (can be empty)
        right = ""
        thispath = relpath
        thispath = re.sub(r'\\', '/', thispath)
        if thispath != "":
            do_process = True
        else:
            do_process = False
        while do_process:
            #print("> thispath: " + thispath)
            if thispath in dict_relpath:
                if right == "": # only incr +ement count of files for this dir
                    dict_relpath[thispath] += 1
                    #print("> ex. direntry: " + thispath)
                else: # make new entry
                    newkey = thispath + '/' + right
                    dict_relpath[newkey] = 1
                    #print("> new direntry: " + newkey)
                do_process = False # done
            else: # remove rightmost subdir
                #print("> dir not in dict: " + thispath)
                match = re.search(r'([\\\/]+)(^[\\\/]+)$', thispath) # find slash followed by not slash till end
                if match:
                    slash = match.group(1)
                    right = match.group(2)
                    to_remove = escape(ext)
                    thispath = re.sub(rf'[\\\/]{to_remove}$', '', thispath)
                    #print("> Anfang: " + thispath + " Ende: " + right)
                else: # string without slash, 1 more try if not empty
                    if thispath != "":
                        # was not in dir, so make an entry
                        dict_relpath[thispath] = 1
                        do_process = False
                    else:
                        do_process = False
    return sourcefile, targetfile, docopy, process
                                

