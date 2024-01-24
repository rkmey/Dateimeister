import xml.etree.ElementTree as ET
import re

# creates new in dir or updates an existing (usedate)
# if ftype is NOT empty (called for config-file) also create type / config-file
# else create indir only .
def new_indir(xmlfile, filename, ftype, config_file, usedate, num_images):
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_indir = ("indir[@name=" + '"' + "%s" + "\"]")
    fstr_indir = (fstr_indir % filename)
    result = mytree.findall(fstr_indir)
    if not result: # indir does not exist in xml
        print("new_indir try to create indir-entry for: " + filename)
        i = ET.SubElement(myroot, 'indir')
        i.set("name", filename)
        i.set("usedate", usedate)
        
        if ftype != "":
            j = ET.SubElement(i, 'type')
            j.set("name", ftype)
            j.set("num_images", str(num_images))

            k = ET.SubElement(j, 'config_file filename=' + '"' + config_file + '"' + ' usedate=' + '"' + usedate + '"' + ' num_images=' + '"' + str(num_images) + '"')
    else: # update usedate
        print("indir node alredy exists: " + filename)
        for i in result:
            i.set("usedate", usedate)
    indent(myroot)
    mytree.write(xmlfile)

# create new type-node. if indir not exists: create indir and type
#    else create type-node under existing indir 
def new_type(xmlfile, filename, ftype, config_file, usedate, num_images):
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_indir = ("indir[@name=" + '"' + "%s" + "\"]")
    fstr_indir = (fstr_indir % filename)
    fstr_type = ("type[@name=" + '"' + "%s" + "\"]")
    fstr_type = (fstr_type % ftype)
    result = mytree.findall(fstr_indir)
    if result: # if indir exists, check if type exists
        for i in result:
            result2 = i.findall(fstr_type)
            if not result2: # type does not exist in indir
                j = ET.SubElement(i, 'type')
                j.set("name", ftype)
                j.set("num_images", str(num_images))
                k = ET.SubElement(j, 'config_file filename=' + '"' + config_file + '"' + ' usedate=' + '"' + usedate + '"' + ' num_images=' + '"' + str(num_images) + '"')
            else:
                print("indir / type node alredy exists: " + filename + ' / ' + ftype)
        indent(myroot)
        mytree.write(xmlfile)
    else:
        new_indir(xmlfile, filename, ftype, config_file, usedate, num_images)

def new_cfgfile(xmlfile, filename, ftype, config_file, usedate, num_images):
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_indir = ("indir[@name=" + '"' + "%s" + "\"]")
    fstr_indir = (fstr_indir % filename)
    fstr_type = ("type[@name=" + '"' + "%s" + "\"]")
    fstr_type = (fstr_type % ftype)
    fstr_cfgf = ("config_file[@filename=" + '"' + "%s" + "\"]")
    fstr_cfgf = (fstr_cfgf % config_file)
    result = mytree.findall(fstr_indir)
    if result:
        for i in result:
            result2 = i.findall(fstr_type)
            if result2:
                for j in result2:
                    result3 = j.findall('.//config_file')
                    files   = j.findall(fstr_cfgf) 
                    if not files: # config_file not in indir / type
                        ET.SubElement(j, 'config_file filename=' + '"' + config_file + '"' + ' usedate=' + '"' + usedate + '"' + ' num_images=' + '"' + str(num_images) + '"')
                    else:
                        print("indir / type / config_file node alredy exists: " + filename + ' / ' + ftype + ' / ' + config_file)
                    j.set("num_images", str(num_images))
                indent(myroot)
                mytree.write(xmlfile)
            else:
                new_type(xmlfile, filename, ftype, config_file, usedate, num_images)
    else:
        new_indir(xmlfile, filename, ftype, config_file, usedate, num_images)

# create new outdir if not exists
def new_outdir(xmlfile, filename, usedate):
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_outdir = ("outdir[@name=" + '"' + "%s" + "\"]")
    fstr_outdir = (fstr_outdir % filename)
    result = mytree.findall(fstr_outdir)
    if not result: # outdir does not exist in xml
        #print("new_outdir try to create outdir-entry for: " + filename)
        i = ET.SubElement(myroot, 'outdir')
        i.set("name", filename)
        i.set("usedate", usedate)
    else:
        #print("outdir node alredy exists: " + filename + " will update usedate: " + usedate)
        for i in result:
            i.set("usedate", usedate)
    indent(myroot)
    mytree.write(xmlfile)


# return list of outdirentries
def get_outdirs(xmlfile):
    outdirs = {}
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_outdir = ("outdir")
    result = mytree.findall(fstr_outdir)
    for i in result:
        #print(i.attrib , i.text)
        outdirs[i.attrib['name']] = {}
        outdirs[i.attrib['name']]['usedate'] = i.attrib['usedate']
    return outdirs

# return list of indirentries
def get_indirs(xmlfile):
    indirs = {}
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_indir = ("indir")
    result = mytree.findall(fstr_indir)
    for i in result:
        #print(i.attrib , i.text)
        indirs[i.attrib['name']] = {}
        indirs[i.attrib['name']]['usedate'] = i.attrib['usedate']
    return indirs

def get_cfgfiles(xmlfile, filename, ftype):
    cfg_files = {}
    #print("*** searching in "  + xmlfile + ' for ' + filename + ' ' + ftype)
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_indir = ("indir[@name=" + '"' + "%s" + "\"]")
    fstr_indir = (fstr_indir % filename)
    fstr_type = ("type[@name=" + '"' + "%s" + "\"]")
    fstr_type = (fstr_type % ftype)
    result = mytree.findall(fstr_indir)
    for i in result:
        #print(i.attrib , i.text)
        result2 = i.findall(fstr_type)
        for j in result2:
            #print(str(j.attrib) + " " + str(j.text))
            files = j.findall('.//config_file')
            #print("Files: " + str(files))
            for r in files:
                #print(r.attrib['filename'] + " used: " + r.attrib['usedate'])
                cfg_files[r.attrib['filename']] = {}
                cfg_files[r.attrib['filename']]['usedate'] = r.attrib['usedate']
                cfg_files[r.attrib['filename']]['num_images'] = r.attrib['num_images']
    return cfg_files
    
def update_cfgfile(xmlfile, filename, ftype, config_file, usedate, num_images):
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_indir = ("indir[@name=" + '"' + "%s" + "\"]")
    fstr_indir = (fstr_indir % filename)
    fstr_type = ("type[@name=" + '"' + "%s" + "\"]")
    fstr_type = (fstr_type % ftype)
    fstr_cfgf = ("config_file[@filename=" + '"' + "%s" + "\"]")
    fstr_cfgf = (fstr_cfgf % config_file)
    result = mytree.findall(fstr_indir)
    if result:
        for i in result:
            result2 = i.findall(fstr_type)
            if result2:
                for j in result2:
                    result3 = j.findall('.//config_file')
                    files   = j.findall(fstr_cfgf)
                    for k in files:
                        k.set("usedate", usedate)
                        k.set("num_images", str(num_images))
    indent(myroot)
    mytree.write(xmlfile)

# delete cfg-file
def delete_cfgfile(xmlfile, filename, ftype, cfg_file):
    #print("*** searching in "  + xmlfile + ' for ' + filename + ' ' + ftype)
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_indir = ("indir[@name=" + '"' + "%s" + "\"]")
    fstr_indir = (fstr_indir % filename)
    fstr_type = ("type[@name=" + '"' + "%s" + "\"]")
    fstr_type = (fstr_type % ftype)
    fstr_cfgfile = ("config_file[@filename=" + '"' + "%s" + "\"]")
    fstr_cfgfile = (fstr_cfgfile % cfg_file)
    result = mytree.findall(fstr_indir)
    for i in result:
        #print(i.attrib , i.text)
        result2 = i.findall(fstr_type)
        for j in result2:
            #print(str(j.attrib) + " " + str(j.text))
            files = j.findall(fstr_cfgfile)
            #print("Files: " + str(files))
            for r in files:
                #print(r.attrib['filename'] + " used: " + r.attrib['usedate'])
                j.remove(r)
    indent(myroot)
    mytree.write(xmlfile)

# delete indir and all children
def delete_indir(xmlfile, filename):
    #print("*** searching in "  + xmlfile + ' for ' + filename + ' ' + ftype)
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_indir = ("indir[@name=" + '"' + "%s" + "\"]")
    fstr_indir = (fstr_indir % filename)
    result = mytree.findall(fstr_indir)
    for i in result:
        myroot.remove(i)
    indent(myroot)
    mytree.write(xmlfile)

# delete outdir and all children
def delete_outdir(xmlfile, filename):
    #print("*** searching in "  + xmlfile + ' for ' + filename + ' ' + ftype)
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_outdir = ("outdir[@name=" + '"' + "%s" + "\"]")
    fstr_outdir = (fstr_outdir % filename)
    result = mytree.findall(fstr_outdir)
    for i in result:
        myroot.remove(i)
    indent(myroot)
    mytree.write(xmlfile)

# return dict of subdirs: subdir.name -> subdir
def get_subdirs(xmlfile):
    dirs = {}
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_outdir = ("subdir")
    result = mytree.findall(fstr_outdir)
    for i in result:
        #print(i.attrib , i.text)
        dirs[i.attrib['type_name'].upper()] = i.attrib['subdir']
    return dirs

# return dict of process_image: process_image.name -> process
def get_process_image(xmlfile):
    dirs = {}
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_outdir = ("process_image")
    result = mytree.findall(fstr_outdir)
    for i in result:
        #print(i.attrib , i.text)
        dirs[i.attrib['suffix_name'].upper()] = i.attrib['process'].upper()
    return dirs

# return list of cameras
def get_cameras(xmlfile):
    cameras = {}
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr = ("camera")
    result = mytree.findall(fstr)
    for i in result:
        #print(i.attrib , i.text)
        cameras[i.attrib['name']] = {}
        cameras[i.attrib['name']]['usedate'] = i.attrib['usedate']
    return cameras

# return usedate for cameras, camera should be unique
def get_cameras_usedate(xmlfile):
    dict_result = {}
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr = ("camera")
    result = mytree.findall(fstr)
    for i in result:
        dict_result[i.attrib['name'].upper()] = i.attrib['usedate']
    return dict_result


# returns camera->typs->list_of_suffixes
def get_cameras_types_suffixes(xmlfile):
    dict_result = {}
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr = ('camera')
    cameras = mytree.findall(fstr)
    for camera in cameras:
        dict_result[camera.attrib['name'].upper()] = {}
        types = camera.findall('type')
        for type in types:
            dict_result[camera.attrib['name'].upper()][type.attrib['name'].upper()] = []
            suffixes = type.findall('suffix')
            if suffixes:
                for suffix in suffixes:
                    dict_result[camera.attrib['name'].upper()][type.attrib['name'].upper()].append(suffix.attrib['name'].upper())
    return dict_result

# create new camera if not exists
def new_camera(xmlfile, cameraname, usedate):
    rc = 0
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_obj = ("camera[@name=" + '"' + "%s" + "\"]")
    fstr_obj = (fstr_obj % cameraname)
    result = mytree.findall(fstr_obj)
    if not result: # camera does not exist in xml
        #print("new_camera try to create camera-entry for: " + cameraname)
        i = ET.SubElement(myroot, 'camera')
        i.set("name", cameraname)
        i.set("usedate", usedate)
        rc = 0
    else:
        #print("camera node alredy exists: " + cameraname + " will update usedate: " + usedate)
        for i in result:
            i.set("usedate", usedate)
        rc = 1
    indent(myroot)
    mytree.write(xmlfile)
    return rc

# create new camera-type-suffix-node. 
# if camera not exists: create camera, camera-type and suffix
# if camera exists:
# if type not exists create type / suffix
#    else (type exists):
#    if suffix exists do nothing 
#    else create suffix under existing type
def new_camera_type_suffix(xmlfile, cameraname, ctype, suffix, usedate):
    rc = 0
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_camera = ("camera[@name=" + '"' + "%s" + "\"]")
    fstr_camera = (fstr_camera % cameraname)
    fstr_type = ("type[@name=" + '"' + "%s" + "\"]")
    fstr_type = (fstr_type % ctype)
    fstr_suffix = ("suffix[@name=" + '"' + "%s" + "\"]")
    fstr_suffix = (fstr_suffix % suffix)
    result = mytree.findall(fstr_camera)
    if result: # if camera exists, check if type exists
        for i in result:
            # update usedate
            i.set("usedate", usedate)
            result2 = i.findall(fstr_type)
            if not result2: # type does not exist in indir
                j = ET.SubElement(i, 'type')
                j.set("name", ctype)
                k = ET.SubElement(j, 'suffix name=' + '"' + suffix + '"')
            else: # type already exists, make new suffix
                print("camera / type node alredy exists: " + cameraname + ' / ' + ctype)
                for j in result2:
                    result3 = j.findall(fstr_suffix)
                    if not result3: # new suffix only if it does nor exist
                        k = ET.SubElement(j, 'suffix name=' + '"' + suffix + '"')
        indent(myroot)
        mytree.write(xmlfile)
    else:
        new_camera(xmlfile, cameraname, usedate)
        new_camera_type_suffix(xmlfile, cameraname, ctype, suffix, usedate)
        rc = 1
   
# update suffix-node. 
# if camera not exists: error
# if camera exists:
# if type not exists error
#    else (type exists):
#    if suffix not exists: error 
#    else rename suffix under existing type
# if newname = "" delete suffix
def update_camera_type_suffix(xmlfile, cameraname, ctype, suffix, newname, usedate):
    rc = 0
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_camera = ("camera[@name=" + '"' + "%s" + "\"]")
    fstr_camera = (fstr_camera % cameraname)
    fstr_type = ("type[@name=" + '"' + "%s" + "\"]")
    fstr_type = (fstr_type % ctype)
    fstr_suffix = ("suffix[@name=" + '"' + "%s" + "\"]")
    fstr_suffix = (fstr_suffix % suffix)
    result = mytree.findall(fstr_camera)
    if result: # if camera exists, check if type exists
        for i in result:
            result2 = i.findall(fstr_type)
            if not result2: # type does not exist in indir
                rc = 2 # type does not exist
                break
            else: # type already exists, rename
                #print("camera / type node alredy exists: " + cameraname + ' / ' + ctype)
                for j in result2:
                    result3 = j.findall(fstr_suffix)
                    if not result3: # new suffix only if it does nor exist
                        rc = 3 # suffix does not exist
                        print("update_camera_type_suffix - suffix not found: " + suffix)
                        break
                    else: #rename suffix
                        for ii in result3:
                            if newname == "":
                                j.remove(ii)
                            else:
                                ii.set("name", newname)
        indent(myroot)
        mytree.write(xmlfile)
    else:
        rc = 1
        pass # camera does not exist
    return rc

# create new camera-type-node. 
# if camera not exists: create camera, camera-type and suffix
# if camera exists:
# if type not exists create type
#    else (type exists): error
def new_camera_type(xmlfile, cameraname, ctype, usedate):
    rc = 0
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_camera = ("camera[@name=" + '"' + "%s" + "\"]")
    fstr_camera = (fstr_camera % cameraname)
    fstr_type = ("type[@name=" + '"' + "%s" + "\"]")
    fstr_type = (fstr_type % ctype)
    result = mytree.findall(fstr_camera)
    if result: # if camera exists, check if type exists
        for i in result:
            # update usedate
            i.set("usedate", usedate)
            result2 = i.findall(fstr_type)
            if not result2: # type does not exist in indir
                j = ET.SubElement(i, 'type')
                j.set("name", ctype)
            else: # type already exists
                rc = 2 # error type already exists
                print("new_camera_type type already exists: " + cameraname + '.' + ctype)
                break
        indent(myroot)
        mytree.write(xmlfile)
    else:
        rc = 1 # error camera does not exist
        print("new_camera_type camera not found: " + cameraname)
    return rc
   
# update type-node. 
# if camera not exists: error
# if camera exists:
# if type not exists error
#    else (type exists):
#    set type.name = newname
# if newname = "" delete suffix
def update_camera_type(xmlfile, cameraname, ctype, newname, usedate):
    rc = 0
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_camera = ("camera[@name=" + '"' + "%s" + "\"]")
    fstr_camera = (fstr_camera % cameraname)
    fstr_type = ("type[@name=" + '"' + "%s" + "\"]")
    fstr_type = (fstr_type % ctype)
    result = mytree.findall(fstr_camera)
    if result: # if camera exists, check if type exists
        for i in result:
            result2 = i.findall(fstr_type)
            if not result2: # type does not exist in indir
                rc = 2 # type does not exist
                break
            else: # type already exists, rename
                #print("camera / type node alredy exists: " + cameraname + ' / ' + ctype)
                for j in result2:
                    if newname == "":
                        i.remove(j)
                    else:
                        j.set("name", newname)
        indent(myroot)
        mytree.write(xmlfile)
    else:
        rc = 1
        pass # camera does not exist
    return rc
# beautify

def indent(elem, level=0):
    # Add indentation
    indent_size = "  "
    i = "\n" + level * indent_size
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + indent_size
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

 
