#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

import sys
import os.path
import re
from datetime import datetime, timezone


def dateimeister(dateityp, endung, indir, thisoutdir, addrelpath, recursive, newer, target_prefix, dict_relpath, select_list):
    # List all files and directories in the specified path, returns list
    #print("Files and Directories in '{:_<10}' typ '{:}' endung '{:}':". format(dateityp, endung, indir))
    print("Dateimeister addrelpath is: ", addrelpath)
    dict_result = {}
    dict_result_all = {} # we need all JPEG-Files for process_type "use_jpeg". Ignore timestamp modified
    dict_result_tooold = {} # we want to keep the files which are not copied because a newer target exist
    list_suffixes = endung.split(',')
    ii = 0
    while ii < len(list_suffixes):
        suffix = list_suffixes[ii].strip()
        list_suffixes[ii] = suffix
        ii += 1
    if recursive == "n":
        # das hier ist für nicht rekursive Aufrufe. Man verarbeitet einfach nur Files
        # os.walk scheint immer rekursiv zu funktionieren
        with os.scandir(indir) as it:
            direntries = list(it)  # reads all of the directory entries
            direntries.sort(key=lambda x: x.name)
        for entry in direntries:
            if entry.is_file():
                process = "n"
                docopy  = "n"
                filename = entry.name
                #print ("*** Entry: " + filename)
                for suffix in list_suffixes:
                    match = re.search(rf".*?\.{suffix}$", filename, re.IGNORECASE)
                    if match:
                        process = "j"
                        #print("File " + filename + " matches: " + suffix)
                        break
                if process == "j":
                    if newer: # copy only if source file is newer
                        st_mtime = entry.stat(follow_symlinks=False).st_mtime
                        strdatetime = datetime.fromtimestamp(st_mtime)
                        # check if file exists in target-dir
                        targetfilename = os.path.join(thisoutdir, target_prefix + filename)
                        #print ("F: " + filename + " mstime " + str(strdatetime) + " targetfile: " + targetfilename)
                        if os.path.isfile(targetfilename):
                            st_mtime_target = os.stat(targetfilename).st_mtime
                            strdatetime_target = datetime.fromtimestamp(st_mtime_target)
                            #print("Targetfile " + filename + " exists in " + thisoutdir + " mstime " + str(st_mtime_target))
                            if st_mtime > st_mtime_target:
                                docopy = "j"
                            else: # don't copy because targetfile has newer timestamp, but keep it in dict_result_tooold
                                docopy = "o"
                        else: # target does not exist
                            a = 1
                            docopy = "j"
                            #print("Targetfile " + filename + " does not exists in " + thisoutdir)
                    else: # copy anyway
                        docopy = "j"
                    sourcefile = os.path.join(indir,      filename)
                    targetfile = os.path.join(thisoutdir, target_prefix + filename)
                    targetfile = re.sub(r"\\", "/", targetfile) # replace single backslash by slash
                    if dateityp.upper() == "JPEG":
                        dict_result_all[sourcefile] = targetfile # we need all jpeg-files regardless of copy-status
                if docopy == "j" or docopy == "o":
                    dict_result[sourcefile] = targetfile
                if docopy == "o": # too old
                    dict_result_tooold[sourcefile] = targetfile
            if entry.is_dir():
                a = 1
                #print ("D: " + entry.name)
    else:
        # für rekursive Aufrufe scheint os.walk besser geeignet, schneller und nimmt einem die Arbeit ab, selbst zu navigieren
        print("Files and Directories in '{:_<10}' typ '{:}' endung '{:}':". format(dateityp, endung, indir))
        for root, dirs, files in os.walk(indir, topdown=True):
            for filename in files:
                filename = re.sub(r"\\", "/", filename) # replace single backslash by slash
                fullname = os.path.join(root, filename)
                relpath = ""
                process = "n"
                docopy  = "n"
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
                        target_dir = thisoutdir + '/' + relpath
                    else: 
                        target_dir = thisoutdir
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
                if docopy == "o": # too old
                    dict_result_tooold[sourcefile] = targetfile
                                
                        
            for dir in dirs:
                a = 1
                #print("D: " + os.path.join(root, dir))
        # 20241022 only return entries from select_list if not None
        #print(str(dict_result))
        if select_list:
            backslash = "\\"
            for i in select_list:
                i = re.sub(re.escape(backslash), r'\\', i) # replace single backslash by double backslash
                if i in dict_result:
                    print("select file: " + i)
                else:
                    print("select file not found: ", i)
    return dict_result, dict_result_all, dict_result_tooold

