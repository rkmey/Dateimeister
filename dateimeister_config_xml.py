import xml.etree.ElementTree as ET
import re


# =============================================================================
# General note about the model
# -----------------------------------------------------------------------------
# The xml file has two conceptually different parts:
#
#   1) The camera tree:
#          <camera name="...">
#            <type name="...">
#              <suffix name="...">
#                <process_image process="..."/>
#              </suffix>
#              <rendertype rendertype="..."/>
#              <subdir subdir="..."/>
#            </type>
#          </camera>
#      This is the "modern" model used by MyCameraTreeview. subdir, rendertype
#      and process_image all belong to a specific camera's type (and for
#      process_image: to a specific suffix of that type).
#
#   2) The legacy flat nodes:
#          <process_image suffix_name="..." process="..."/>
#          <subdir type_name="..." subdir="..."/>
#          <rendertype type_name="..." rendertype="..."/>
#      These are kept for backward compatibility with Dateimeister_support,
#      which still reads them via get_subdirs(), get_rendertypes() and
#      get_process_image(). They are not written by MyCameraTreeview.
#
# Both parts live side by side in the same xml file.
# =============================================================================


# -----------------------------------------------------------------------------
# indir / outdir / type / config_file handling
# -----------------------------------------------------------------------------

def new_indir(xmlfile, filename, ftype, config_file, usedate, num_images):
    """
    Create a new <indir> node or update the usedate of an existing one.
    If ftype is not empty, also create a <type> child (and a <config_file>
    grandchild) with the given config_file / usedate / num_images.
    """
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_indir = ("indir[@name=" + '"' + "%s" + "\"]")
    fstr_indir = (fstr_indir % filename)
    result = mytree.findall(fstr_indir)
    if not result:  # indir does not exist in xml
        print("new_indir try to create indir-entry for: " + filename)
        i = ET.SubElement(myroot, 'indir')
        i.set("name", filename)
        i.set("usedate", usedate)

        if ftype != "":
            j = ET.SubElement(i, 'type')
            j.set("name", ftype)
            j.set("num_images", str(num_images))

            k = ET.SubElement(j, 'config_file filename=' + '"' + config_file + '"' +
                              ' usedate=' + '"' + usedate + '"' +
                              ' num_images=' + '"' + str(num_images) + '"')
    else:  # update usedate
        print("indir node already exists: " + filename)
        for i in result:
            i.set("usedate", usedate)
    indent(myroot)
    mytree.write(xmlfile)


def new_type(xmlfile, filename, ftype, config_file, usedate, num_images):
    """
    Create a new <type> node under an existing <indir>.
    If the indir does not exist, create it first (via new_indir) and then
    add the type.
    """
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_indir = ("indir[@name=" + '"' + "%s" + "\"]")
    fstr_indir = (fstr_indir % filename)
    fstr_type = ("type[@name=" + '"' + "%s" + "\"]")
    fstr_type = (fstr_type % ftype)
    result = mytree.findall(fstr_indir)
    if result:  # indir exists, check if type exists
        for i in result:
            result2 = i.findall(fstr_type)
            if not result2:  # type does not exist yet
                j = ET.SubElement(i, 'type')
                j.set("name", ftype)
                j.set("num_images", str(num_images))
                k = ET.SubElement(j, 'config_file filename=' + '"' + config_file + '"' +
                                  ' usedate=' + '"' + usedate + '"' +
                                  ' num_images=' + '"' + str(num_images) + '"')
            else:
                print("indir / type node already exists: " + filename + ' / ' + ftype)
        indent(myroot)
        mytree.write(xmlfile)
    else:
        new_indir(xmlfile, filename, ftype, config_file, usedate, num_images)


def new_cfgfile(xmlfile, filename, ftype, config_file, usedate, num_images):
    """
    Create a new <config_file> node under <indir>/<type>, or update an
    existing one. Creates the indir / type levels as needed.
    """
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
                    files = j.findall(fstr_cfgf)
                    if not files:  # config_file not yet in indir / type
                        ET.SubElement(j, 'config_file filename=' + '"' + config_file + '"' +
                                      ' usedate=' + '"' + usedate + '"' +
                                      ' num_images=' + '"' + str(num_images) + '"')
                    else:
                        print("indir / type / config_file node already exists: " +
                              filename + ' / ' + ftype + ' / ' + config_file)
                    j.set("num_images", str(num_images))
                indent(myroot)
                mytree.write(xmlfile)
            else:
                new_type(xmlfile, filename, ftype, config_file, usedate, num_images)
    else:
        new_indir(xmlfile, filename, ftype, config_file, usedate, num_images)


def new_outdir(xmlfile, filename, usedate):
    """Create a new <outdir> node or update the usedate of an existing one."""
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_outdir = ("outdir[@name=" + '"' + "%s" + "\"]")
    fstr_outdir = (fstr_outdir % filename)
    result = mytree.findall(fstr_outdir)
    if not result:  # outdir does not exist
        i = ET.SubElement(myroot, 'outdir')
        i.set("name", filename)
        i.set("usedate", usedate)
    else:
        for i in result:
            i.set("usedate", usedate)
    indent(myroot)
    mytree.write(xmlfile)


def get_outdirs(xmlfile):
    """Return {outdir_name: {'usedate': ...}} for all <outdir> nodes."""
    outdirs = {}
    mytree = ET.parse(xmlfile)
    result = mytree.findall("outdir")
    for i in result:
        outdirs[i.attrib['name']] = {}
        outdirs[i.attrib['name']]['usedate'] = i.attrib['usedate']
    return outdirs


def get_indirs(xmlfile):
    """Return {indir_name: {'usedate': ...}} for all <indir> nodes."""
    indirs = {}
    mytree = ET.parse(xmlfile)
    result = mytree.findall("indir")
    for i in result:
        indirs[i.attrib['name']] = {}
        indirs[i.attrib['name']]['usedate'] = i.attrib['usedate']
    return indirs


def get_cfgfiles(xmlfile, filename, ftype):
    """
    Return {config_file_name: {'usedate': ..., 'num_images': ...}}
    for all <config_file> nodes under <indir name=filename>/<type name=ftype>.
    """
    cfg_files = {}
    mytree = ET.parse(xmlfile)
    fstr_indir = ("indir[@name=" + '"' + "%s" + "\"]")
    fstr_indir = (fstr_indir % filename)
    fstr_type = ("type[@name=" + '"' + "%s" + "\"]")
    fstr_type = (fstr_type % ftype)
    result = mytree.findall(fstr_indir)
    for i in result:
        result2 = i.findall(fstr_type)
        for j in result2:
            files = j.findall('.//config_file')
            for r in files:
                cfg_files[r.attrib['filename']] = {}
                cfg_files[r.attrib['filename']]['usedate'] = r.attrib['usedate']
                cfg_files[r.attrib['filename']]['num_images'] = r.attrib['num_images']
    return cfg_files


def update_cfgfile(xmlfile, filename, ftype, config_file, usedate, num_images):
    """
    Update usedate and num_images of an existing <config_file> node under
    <indir name=filename>/<type name=ftype>.
    """
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
                    files = j.findall(fstr_cfgf)
                    for k in files:
                        k.set("usedate", usedate)
                        k.set("num_images", str(num_images))
    indent(myroot)
    mytree.write(xmlfile)


def delete_cfgfile(xmlfile, filename, ftype, cfg_file):
    """Delete a <config_file> node under <indir>/<type>."""
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
        result2 = i.findall(fstr_type)
        for j in result2:
            files = j.findall(fstr_cfgfile)
            for r in files:
                j.remove(r)
    indent(myroot)
    mytree.write(xmlfile)


def delete_indir(xmlfile, filename):
    """Delete an <indir> node including all children."""
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_indir = ("indir[@name=" + '"' + "%s" + "\"]")
    fstr_indir = (fstr_indir % filename)
    result = mytree.findall(fstr_indir)
    for i in result:
        myroot.remove(i)
    indent(myroot)
    mytree.write(xmlfile)


def delete_outdir(xmlfile, filename):
    """Delete an <outdir> node including all children."""
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_outdir = ("outdir[@name=" + '"' + "%s" + "\"]")
    fstr_outdir = (fstr_outdir % filename)
    result = mytree.findall(fstr_outdir)
    for i in result:
        myroot.remove(i)
    indent(myroot)
    mytree.write(xmlfile)


# -----------------------------------------------------------------------------
# Legacy flat accessors (still used by Dateimeister_support)
#
# These read/write the flat top-level nodes:
#     <subdir type_name="..." subdir="..."/>
#     <rendertype type_name="..." rendertype="..."/>
#     <process_image suffix_name="..." process="..."/>
# The type_name / suffix_name is treated as a global concept here: the same
# value applies no matter which camera a type / suffix belongs to.
# -----------------------------------------------------------------------------

def get_subdirs(xmlfile):
    """
    Return {type_name: subdir} by scanning the flat top-level <subdir> nodes.
    Kept for backward compatibility with Dateimeister_support.
    """
    dirs = {}
    mytree = ET.parse(xmlfile)
    result = mytree.findall("subdir")
    for i in result:
        dirs[i.attrib['type_name'].upper()] = i.attrib['subdir']
    return dirs


def get_rendertypes(xmlfile):
    """
    Return {type_name: rendertype} by scanning the flat top-level <rendertype>
    nodes. Kept for backward compatibility with Dateimeister_support.
    """
    ret = {}
    mytree = ET.parse(xmlfile)
    result = mytree.findall("rendertype")
    for i in result:
        ret[i.attrib['type_name'].upper()] = i.attrib['rendertype']
    return ret


def get_process_image(xmlfile):
    """
    Return {suffix_name: process} by scanning the flat top-level
    <process_image> nodes. Kept for backward compatibility with
    Dateimeister_support.
    """
    dirs = {}
    mytree = ET.parse(xmlfile)
    result = mytree.findall("process_image")
    for i in result:
        dirs[i.attrib['suffix_name'].upper()] = i.attrib['process'].upper()
    return dirs


def new_subdir(xmlfile, type_name, subdir):
    """
    Legacy: create or update a flat <subdir type_name=...> node.
    Kept for backward compatibility. MyCameraTreeview uses
    new_subdir_camera() instead.
    """
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    rc = 0
    fstr = ('subdir[@type_name="%s"]' % type_name)
    result = mytree.findall(fstr)
    if not result:
        i = ET.SubElement(myroot, 'subdir')
        i.set("type_name", type_name)
        i.set("subdir", subdir)
    else:
        for i in result:
            i.set("subdir", subdir)
        rc = 1
    indent(myroot)
    mytree.write(xmlfile)
    return rc


def new_rendertype(xmlfile, type_name, rendertype):
    """
    Legacy: create or update a flat <rendertype type_name=...> node.
    Kept for backward compatibility. MyCameraTreeview uses
    new_rendertype_camera() instead.
    """
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    rc = 0
    fstr = ('rendertype[@type_name="%s"]' % type_name)
    result = mytree.findall(fstr)
    if not result:
        i = ET.SubElement(myroot, 'rendertype')
        i.set("type_name", type_name)
        i.set("rendertype", rendertype)
    else:
        for i in result:
            i.set("rendertype", rendertype)
        rc = 1
    indent(myroot)
    mytree.write(xmlfile)
    return rc


def new_process_image(xmlfile, suffix_name, process):
    """
    Legacy: create or update a flat <process_image suffix_name=...> node.
    Kept for backward compatibility. MyCameraTreeview uses
    new_process_image_camera() instead.
    """
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    rc = 0
    fstr = ('process_image[@suffix_name="%s"]' % suffix_name)
    result = mytree.findall(fstr)
    if not result:
        i = ET.SubElement(myroot, 'process_image')
        i.set("suffix_name", suffix_name)
        i.set("process", process)
    else:
        for i in result:
            i.set("process", process)
        rc = 1
    indent(myroot)
    mytree.write(xmlfile)
    return rc


# -----------------------------------------------------------------------------
# Camera accessors
# -----------------------------------------------------------------------------

def get_cameras(xmlfile):
    """Return {camera_name: {'usedate': ...}} for all <camera> nodes."""
    cameras = {}
    mytree = ET.parse(xmlfile)
    result = mytree.findall("camera")
    for i in result:
        cameras[i.attrib['name']] = {}
        cameras[i.attrib['name']]['usedate'] = i.attrib['usedate']
    return cameras


def get_cameras_usedate(xmlfile):
    """Return {camera_name_upper: usedate} for all <camera> nodes."""
    dict_result = {}
    mytree = ET.parse(xmlfile)
    result = mytree.findall("camera")
    for i in result:
        dict_result[i.attrib['name'].upper()] = i.attrib['usedate']
    return dict_result


def get_cameras_types_suffixes(xmlfile):
    """
    Return {camera: {type: [suffix, ...]}} for all cameras.
    Camera names and type names are upper-cased; suffix names are upper-cased
    as well.
    """
    dict_result = {}
    mytree = ET.parse(xmlfile)
    cameras = mytree.findall("camera")
    for camera in cameras:
        dict_result[camera.attrib['name'].upper()] = {}
        types = camera.findall('type')
        for type in types:
            dict_result[camera.attrib['name'].upper()][type.attrib['name'].upper()] = []
            suffixes = type.findall('suffix')
            if suffixes:
                for suffix in suffixes:
                    dict_result[camera.attrib['name'].upper()][type.attrib['name'].upper()].append(
                        suffix.attrib['name'])
    return dict_result


def new_camera(xmlfile, cameraname, usedate):
    """
    Create a new <camera> node or update the usedate of an existing one.
    Return 0 if newly created, 1 if updated.
    """
    rc = 0
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_obj = ('camera[@name="%s"]' % cameraname)
    result = mytree.findall(fstr_obj)
    if not result:  # camera does not exist
        i = ET.SubElement(myroot, 'camera')
        i.set("name", cameraname)
        i.set("usedate", usedate)
        rc = 0
    else:
        for i in result:
            i.set("usedate", usedate)
        rc = 1
    indent(myroot)
    mytree.write(xmlfile)
    return rc


def new_camera_type_suffix(xmlfile, cameraname, ctype, suffix, usedate):
    """
    Create a <suffix> under camera/type. Creates camera and/or type if
    needed. Updates the camera's usedate.
    """
    rc = 0
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_camera = ('camera[@name="%s"]' % cameraname)
    fstr_type = ('type[@name="%s"]' % ctype)
    fstr_suffix = ('suffix[@name="%s"]' % suffix)
    result = mytree.findall(fstr_camera)
    if result:
        for i in result:
            i.set("usedate", usedate)
            result2 = i.findall(fstr_type)
            if not result2:  # type does not exist yet
                j = ET.SubElement(i, 'type')
                j.set("name", ctype)
                k = ET.SubElement(j, 'suffix name=' + '"' + suffix + '"')
            else:
                print("camera / type node already exists: " + cameraname + ' / ' + ctype)
                for j in result2:
                    result3 = j.findall(fstr_suffix)
                    if not result3:  # add suffix only if it does not exist
                        k = ET.SubElement(j, 'suffix name=' + '"' + suffix + '"')
        indent(myroot)
        mytree.write(xmlfile)
    else:
        new_camera(xmlfile, cameraname, usedate)
        new_camera_type_suffix(xmlfile, cameraname, ctype, suffix, usedate)
        rc = 1


def update_camera_type_suffix(xmlfile, cameraname, ctype, suffix, newname, usedate):
    """
    Rename a <suffix> node. If newname is empty, delete the suffix instead.
    Returns 0 on success, 1 if the camera does not exist, 2 if the type
    does not exist, 3 if the suffix does not exist.
    """
    rc = 0
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_camera = ('camera[@name="%s"]' % cameraname)
    fstr_type = ('type[@name="%s"]' % ctype)
    fstr_suffix = ('suffix[@name="%s"]' % suffix)
    result = mytree.findall(fstr_camera)
    if result:
        for i in result:
            result2 = i.findall(fstr_type)
            if not result2:
                rc = 2
                break
            else:
                for j in result2:
                    result3 = j.findall(fstr_suffix)
                    if not result3:
                        rc = 3
                        print("update_camera_type_suffix - suffix not found: " + suffix)
                        break
                    else:
                        for ii in result3:
                            if newname == "":
                                j.remove(ii)
                            else:
                                ii.set("name", newname)
        indent(myroot)
        mytree.write(xmlfile)
    else:
        rc = 1
    return rc


def new_camera_type(xmlfile, cameraname, ctype, usedate):
    """
    Create a <type> under an existing camera.
    Returns 0 on success, 1 if the camera does not exist, 2 if the type
    already exists.
    """
    rc = 0
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_camera = ('camera[@name="%s"]' % cameraname)
    fstr_type = ('type[@name="%s"]' % ctype)
    result = mytree.findall(fstr_camera)
    if result:
        for i in result:
            i.set("usedate", usedate)
            result2 = i.findall(fstr_type)
            if not result2:
                j = ET.SubElement(i, 'type')
                j.set("name", ctype)
            else:
                rc = 2
                print("new_camera_type type already exists: " + cameraname + '.' + ctype)
                break
        indent(myroot)
        mytree.write(xmlfile)
    else:
        rc = 1
        print("new_camera_type camera not found: " + cameraname)
    return rc


def update_camera_type(xmlfile, cameraname, ctype, newname, usedate):
    """
    Rename a <type> node. If newname is empty, delete the type (and all
    its children) instead.
    Returns 0 on success, 1 if the camera does not exist, 2 if the type
    does not exist.
    """
    rc = 0
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_camera = ('camera[@name="%s"]' % cameraname)
    fstr_type = ('type[@name="%s"]' % ctype)
    result = mytree.findall(fstr_camera)
    if result:
        for i in result:
            result2 = i.findall(fstr_type)
            if not result2:
                rc = 2
                break
            else:
                for j in result2:
                    if newname == "":
                        i.remove(j)
                    else:
                        j.set("name", newname)
        indent(myroot)
        mytree.write(xmlfile)
    else:
        rc = 1
    return rc


def update_camera_usedate(xmlfile, cameraname, usedate):
    """
    Update the usedate attribute of a camera.
    Returns 0 on success, 1 if the camera does not exist.
    """
    rc = 0
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_camera = ('camera[@name="%s"]' % cameraname)
    result = mytree.findall(fstr_camera)
    if result:
        for i in result:
            i.set("usedate", usedate)
        indent(myroot)
        mytree.write(xmlfile)
    else:
        rc = 1
    return rc


def update_camera(xmlfile, cameraname, newname):
    """
    Rename a camera. If newname is empty, delete the camera (and all its
    children) instead.
    """
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_camera = ('camera[@name="%s"]' % cameraname)
    result = mytree.findall(fstr_camera)
    for i in result:
        if newname == "":
            myroot.remove(i)
        else:
            i.set("name", newname)
    indent(myroot)
    mytree.write(xmlfile)


# -----------------------------------------------------------------------------
# Per-camera accessors: subdir / rendertype / process_image
#
# These read from the modern camera/type (/suffix) structure and treat
# subdir / rendertype / process_image as belonging to a SPECIFIC camera's
# type (or suffix). They do NOT touch the flat legacy nodes above.
# -----------------------------------------------------------------------------

def get_subdirs_per_camera(xmlfile):
    """
    Return {camera: {type_name: subdir}} reading camera/type/subdir nodes.
    The flat top-level <subdir> nodes are ignored.
    """
    result = {}
    mytree = ET.parse(xmlfile)
    for cam in mytree.findall("camera"):
        cam_name = cam.attrib['name'].upper()
        cam_dict = {}
        for t in cam.findall("type"):
            type_name = t.attrib['name'].upper()
            sub = t.find('subdir')
            if sub is not None and 'subdir' in sub.attrib:
                cam_dict[type_name] = sub.attrib['subdir']
        if cam_dict:
            result[cam_name] = cam_dict
    return result


def get_rendertypes_per_camera(xmlfile):
    """
    Return {camera: {type_name: rendertype}} reading camera/type/rendertype
    nodes. The flat top-level <rendertype> nodes are ignored.
    """
    result = {}
    mytree = ET.parse(xmlfile)
    for cam in mytree.findall("camera"):
        cam_name = cam.attrib['name'].upper()
        cam_dict = {}
        for t in cam.findall("type"):
            type_name = t.attrib['name'].upper()
            rt = t.find('rendertype')
            if rt is not None and 'rendertype' in rt.attrib:
                cam_dict[type_name] = rt.attrib['rendertype']
        if cam_dict:
            result[cam_name] = cam_dict
    return result


def get_process_image_per_camera(xmlfile):
    """
    Return {camera: {type_name: {suffix_name: process_image}}} reading
    camera/type/suffix/process_image nodes.

    <process_image> is stored as a child element of <suffix>:
        <suffix name="JPG"><process_image process="USE_JPEG"/></suffix>
    """
    result = {}
    mytree = ET.parse(xmlfile)
    for cam in mytree.findall("camera"):
        cam_name = cam.attrib['name'].upper()
        cam_dict = {}
        for t in cam.findall("type"):
            type_name = t.attrib['name'].upper()
            suf_dict = {}
            for s in t.findall("suffix"):
                suffix_name = s.attrib['name'].upper()
                pi = s.find('process_image')
                if pi is not None and 'process' in pi.attrib:
                    suf_dict[suffix_name] = pi.attrib['process'].upper()
            if suf_dict:
                cam_dict[type_name] = suf_dict
        if cam_dict:
            result[cam_name] = cam_dict
    return result


def new_subdir_camera(xmlfile, camera, type_name, subdir):
    """
    Create or update the <subdir> child under camera/type[@name=type_name].
    Only this one camera/type is touched.
    Returns:
        0 if the <subdir> was newly created,
        1 if it was updated,
        2 if the camera/type does not exist.
    """
    mytree = ET.parse(xmlfile)
    fstr_camera = ('camera[@name="%s"]' % camera)
    fstr_type = ('type[@name="%s"]' % type_name)
    cam = mytree.find(fstr_camera)
    if cam is None:
        print("new_subdir_camera - camera not found: " + camera)
        return 2
    t = cam.find(fstr_type)
    if t is None:
        print("new_subdir_camera - camera " + camera + " has no type: " + type_name)
        return 2
    sub = t.find('subdir')
    if sub is None:
        i = ET.SubElement(t, 'subdir')
        i.set("subdir", subdir)
        rc = 0
    else:
        sub.set("subdir", subdir)
        rc = 1
    indent(mytree.getroot())
    mytree.write(xmlfile)
    return rc


def new_rendertype_camera(xmlfile, camera, type_name, rendertype):
    """
    Create or update the <rendertype> child under camera/type[@name=type_name].
    Only this one camera/type is touched.
    Returns:
        0 if newly created,
        1 if updated,
        2 if the camera/type does not exist.
    """
    mytree = ET.parse(xmlfile)
    fstr_camera = ('camera[@name="%s"]' % camera)
    fstr_type = ('type[@name="%s"]' % type_name)
    cam = mytree.find(fstr_camera)
    if cam is None:
        print("new_rendertype_camera - camera not found: " + camera)
        return 2
    t = cam.find(fstr_type)
    if t is None:
        print("new_rendertype_camera - camera " + camera + " has no type: " + type_name)
        return 2
    rt = t.find('rendertype')
    if rt is None:
        i = ET.SubElement(t, 'rendertype')
        i.set("rendertype", rendertype)
        rc = 0
    else:
        rt.set("rendertype", rendertype)
        rc = 1
    indent(mytree.getroot())
    mytree.write(xmlfile)
    return rc


def new_process_image_camera(xmlfile, camera, type_name, suffix_name, process_image):
    """
    Create or update the <process_image> child under
    camera/type[@name=type_name]/suffix[@name=suffix_name].
    Only this one suffix is touched.
    Returns:
        0 if the <process_image> element was newly created,
        1 if it was updated,
        2 if the camera/type/suffix was not found.
    """
    mytree = ET.parse(xmlfile)
    fstr_camera = ('camera[@name="%s"]' % camera)
    fstr_type = ('type[@name="%s"]' % type_name)
    fstr_suffix = ('suffix[@name="%s"]' % suffix_name)
    cam = mytree.find(fstr_camera)
    if cam is None:
        print("new_process_image_camera - camera not found: " + camera)
        return 2
    t = cam.find(fstr_type)
    if t is None:
        print("new_process_image_camera - camera " + camera + " has no type: " + type_name)
        return 2
    s = t.find(fstr_suffix)
    if s is None:
        print("new_process_image_camera - no suffix " + suffix_name +
              " under camera " + camera + " type " + type_name)
        return 2
    pi = s.find('process_image')
    if pi is None:
        i = ET.SubElement(s, 'process_image')
        i.set("process", process_image)
        rc = 0
    else:
        pi.set("process", process_image)
        rc = 1
    indent(mytree.getroot())
    mytree.write(xmlfile)
    return rc


# -----------------------------------------------------------------------------
# Diatisch section
# -----------------------------------------------------------------------------

def get_cfgfiles_diatisch(xmlfile):
    """Return {filename: {'usedate': ..., 'ctr_source': ..., 'ctr_target': ...}}
    for all <configfile> nodes under <config_files>."""
    cfgfiles = {}
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    result1 = myroot.findall("config_files")
    if result1:
        for i in result1:
            result2 = i.findall("configfile")
            for j in result2:
                cfgfiles[j.attrib['filename']] = {}
                cfgfiles[j.attrib['filename']]['usedate'] = j.attrib['usedate']
                cfgfiles[j.attrib['filename']]['ctr_source'] = j.attrib['ctr_source']
                cfgfiles[j.attrib['filename']]['ctr_target'] = j.attrib['ctr_target']
    return cfgfiles


def get_diatisch_items_usedate(xmlfile, parent, entry, attrname):
    """
    Generic helper to return {attrname-value: {'usedate': ...}} for all
    <entry> nodes under <parent>.
    """
    indirs = {}
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    result1 = myroot.findall(parent)
    if result1:
        for i in result1:
            result2 = i.findall(entry)
            for j in result2:
                indirs[j.attrib[attrname]] = {}
                indirs[j.attrib[attrname]]['usedate'] = j.attrib['usedate']
    return indirs


def new_cfgfile_diatisch(xmlfile, config_file, usedate, ctr_source, ctr_target):
    """Create or update a <configfile> under <config_files>."""
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr_cfgf = ('configfile[@filename="%s"]' % config_file)
    result1 = mytree.findall("config_files")
    if result1:
        for i in result1:
            result2 = i.findall(fstr_cfgf)
            if not result2:
                print("new config-file, try to create entry for: " + config_file)
                j = ET.SubElement(i, 'configfile')
                j.set("filename", config_file)
                j.set("usedate", usedate)
                j.set("ctr_source", str(ctr_source))
                j.set("ctr_target", str(ctr_target))
            else:
                print("config-file node already exists: " + config_file)
                for j in result2:
                    j.set("usedate", usedate)
                    j.set("ctr_source", str(ctr_source))
                    j.set("ctr_target", str(ctr_target))
        indent(myroot)
        mytree.write(xmlfile)
    else:
        print("try to make config_files-node")
        new_node_diatisch(xmlfile, "config_files", usedate)
        new_cfgfile_diatisch(xmlfile, config_file, usedate, ctr_source, ctr_target)


def new_dir_diatisch(xmlfile, parent, entrytype, attrname, attrvalue, usedate):
    """
    Create or update an <entrytype> node with the given attribute under
    <parent>. Creates the parent node if needed.
    """
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr1 = ('{:s}[@{:s}="{:s}"]').format(entrytype, attrname, attrvalue)
    print("xml search: " + fstr1)
    result1 = mytree.findall(parent)
    if result1:
        for i in result1:
            result2 = i.findall(fstr1)
            if not result2:
                print(("new {:s}, try to create entry").format(entrytype))
                j = ET.SubElement(i, entrytype)
                j.set(attrname, attrvalue)
                j.set("usedate", usedate)
            else:
                print(("{:s} node {:s} = {:s} already exists").format(entrytype, attrname, attrvalue))
                for j in result2:
                    j.set("usedate", usedate)

        indent(myroot)
        mytree.write(xmlfile)
    else:
        print(("try to make {:s}-node").format(parent))
        new_node_diatisch(xmlfile, parent, usedate)
        new_dir_diatisch(xmlfile, parent, entrytype, attrname, attrvalue, usedate)


def new_node_diatisch(xmlfile, nodetype, usedate):
    """Create a top-level node <nodetype> under the root if it does not exist."""
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    result1 = mytree.findall(nodetype)
    if not result1:
        i = ET.SubElement(myroot, nodetype)
        i.set("usedate", usedate)
    indent(myroot)
    mytree.write(xmlfile)


def delete_diatisch_item(xmlfile, parent, entrytype, attrname, attrvalue):
    """Delete an <entrytype> node under <parent>."""
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    fstr = ('{:s}[@{:s}="{:s}"]').format(entrytype, attrname, attrvalue)
    print("xml search: " + fstr)
    result1 = myroot.findall(parent)
    if result1:
        for i in result1:
            result2 = i.findall(fstr)
            for j in result2:
                i.remove(j)
    indent(myroot)
    mytree.write(xmlfile)


def get_filenames_diatisch(xmlfile, ftype, ftype2):
    """Return a flat list of names from <ftype>/<ftype2 name=...> nodes."""
    files = []
    mytree = ET.parse(xmlfile)
    myroot = mytree.getroot()
    result = mytree.findall(ftype)
    for i in result:
        result2 = i.findall(ftype2)
        for j in result2:
            files.append(j.attrib['name'])
    return files


# -----------------------------------------------------------------------------
# Beautify
# -----------------------------------------------------------------------------

def indent(elem, level=0):
    """Recursively add indentation to the given ElementTree element."""
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