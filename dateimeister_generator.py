#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

import sys
import os.path
import re
from datetime import datetime, timezone

# we have 3 procesing types: 1) list of full filenames (path/file), 2) directory not recursive, 3) directory recursive
def dateimeister(dateityp, endung, indir, outdir, addrelpath, recursive, newer, target_prefix, select_list):
    global dict_result, dict_result_all, dict_result_tooold, dict_relpath
    # List all files and directories in the specified path, returns list
    #print("Files and Directories in '{:_<10}' typ '{:}' endung '{:}':". format(dateityp, endung, indir))
    print("Dateimeister addrelpath is: ", addrelpath)
    dict_result = {}
    dict_result_all = {} # we need all JPEG-Files for process_type "use_jpeg". Ignore timestamp modified
    dict_result_tooold = {} # we want to keep the files which are not copied because a newer target exist
    dict_relpath = {}
    list_suffixes = endung.split(',')
    ii = 0
    while ii < len(list_suffixes):
        suffix = list_suffixes[ii].strip()
        list_suffixes[ii] = suffix
        ii += 1

    if select_list: # comes from Diatisch
        for fullname in select_list:
            if os.path.isfile(fullname):
                filename = os.path.basename(fullname)
                root  = os.path.dirname(fullname)
                #print("generating entry for : " + str(filename))
                filename = re.sub(r"\\", "/", filename) # replace single backslash by slash
                fullname = os.path.join(root, filename)
                sourcefile, targetfile, docopy, process = process_file(root, filename, fullname, dateityp, indir, outdir, list_suffixes, addrelpath, newer, target_prefix)
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
        for entry in direntries:
            if entry.is_file():
                filename = entry.name
                #print("generating entry for : " + str(filename))
                filename = re.sub(r"\\", "/", filename) # replace single backslash by slash
                fullname = os.path.join(root, filename)
                sourcefile, targetfile, docopy, process = process_file(root, filename, fullname, dateityp, indir, outdir, list_suffixes, addrelpath, newer, target_prefix)
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
        for root, dirs, files in os.walk(indir, topdown=True):
            for filename in files:
                filename = re.sub(r"\\", "/", filename) # replace single backslash by slash
                fullname = os.path.join(root, filename)
                sourcefile, targetfile, docopy, process = process_file(root, filename, fullname, dateityp, indir, outdir, list_suffixes, addrelpath, newer, target_prefix)
                if process == "j":
                    if dateityp.upper() == "JPEG":
                        dict_result_all[sourcefile] = targetfile # we need all jpeg-files regardless of copy-status
                if docopy == "j" or docopy == "o":
                    dict_result[sourcefile] = targetfile
                if docopy == "o": # too old
                    dict_result_tooold[sourcefile] = targetfile
    return dict_result, dict_result_all, dict_result_tooold, dict_relpath
    
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
                                

