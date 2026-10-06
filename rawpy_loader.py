# -*- coding: utf-8 -*-
"""
rawpy_loader.py - Laden von RAW-Dateien (NEF, RAF, CR2/CR3, ARW, DNG, ...)
mit rawpy/LibRaw.

Anwendungsfaelle:

  1. Canvas-Thumbnails (schnell, Qualitaet egal):
       load_raw_thumbnail(file, height)
     Rueckgabe: (PIL.Image, width, height) oder (None, 0, 0) bei Fehler.

  2. Detailansicht, erste Anzeige:
       load_raw_embedded(file)
     Rueckgabe: PIL.Image oder None bei Fehler.

  3. Detailansicht, volle Auflaesung:
       load_raw_full(file)
     Rueckgabe: PIL.Image oder wirft Exception bei Fehler.

  4. Metadaten (kuratiert, fuer die Basis-Anzeige):
       load_raw_metadata(file)
     Rueckgabe: {category: {key: str(value), ...}, ...}

  5. Metadaten (alle EXIF-Tags aus dem eingebetteten JPEG):
       load_raw_all_exif(file)
     Rueckgabe: {category: {key: str(value), ...}, ...}

Alle Funktionen veraendern das Original-File nicht.
"""

import io
import os

from PIL import Image, ImageOps

try:
    import rawpy
except ImportError:
    rawpy = None


def _ensure_rawpy():
    if rawpy is None:
        raise RuntimeError(
            "rawpy ist nicht installiert. Bitte 'pip install rawpy' ausfuehren."
        )


def _extract_embedded_image(raw):
    """Hilfsfunktion: liefert das eingebettete JPEG als PIL.Image
    oder None, wenn keines vorhanden ist.
    """
    try:
        thumb = raw.extract_thumb()
        if thumb.format == rawpy.ThumbFormat.JPEG:
            img = Image.open(io.BytesIO(thumb.data))
            img.load()
            return img
        else:
            return Image.fromarray(thumb.data)
    except rawpy.LibRawNoThumbnailError:
        return None


# ----------------------------------------------------------------------
# Bild laden
# ----------------------------------------------------------------------

def load_raw_thumbnail(file, height):
    """Schneller Weg fuer Canvas-Thumbnails.

    Extrahiert das eingebettete JPEG und skaliert es auf 'height' Pixel.
    Kein postprocess, weil das bei vielen Bildern zu langsam waere.

    Rueckgabe:
        (PIL.Image, width, height) bei Erfolg
        (None, 0, 0) bei Fehler.
    """
    if rawpy is None:
        return None, 0, 0

    try:
        with rawpy.imread(file) as raw:
            img = _extract_embedded_image(raw)
    except Exception:
        return None, 0, 0

    if img is None:
        return None, 0, 0

    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")

    w_orig, h_orig = img.size
    if h_orig != height:
        faktor = height / h_orig
        new_size = (max(1, int(w_orig * faktor)), height)
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    return img, img.size[0], img.size[1]


def load_raw_embedded(file):
    """Liefert das eingebettete JPEG-Vorschaubild in voller Groesse.

    Wenn kein eingebettetes JPEG vorhanden ist, wird postprocess()
    benutzt (langsam).

    Rueckgabe: PIL.Image oder None bei Fehler.
    """
    if rawpy is None:
        return None

    try:
        with rawpy.imread(file) as raw:
            img = _extract_embedded_image(raw)
            if img is None:
                img = Image.fromarray(raw.postprocess(use_camera_wb=True))
    except Exception:
        return None

    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def load_raw_full(file):
    """Volle Sensor-Auflaesung per postprocess().

    Langsam (1-2 s bei 50 MP), aber die maximale Qualitaet.
    use_camera_wb=True entspricht dem Weissabgleich, den die Kamera
    zur Aufnahmezeit gemessen hat.

    Rueckgabe: PIL.Image. Wirft Exception bei Fehler.
    """
    _ensure_rawpy()

    with rawpy.imread(file) as raw:
        rgb = raw.postprocess(use_camera_wb=True)

    img = Image.fromarray(rgb)
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def sensor_size(file):
    """Liefert (width, height) des Sensors, oder None wenn nicht lesbar."""
    if rawpy is None:
        return None
    try:
        with rawpy.imread(file) as raw:
            return raw.sizes.width, raw.sizes.height
    except Exception:
        return None


# ----------------------------------------------------------------------
# Metadaten
# ----------------------------------------------------------------------

def _format_shutter(shutter_speed):
    """Formatiert die Belichtungszeit. Aus 0.0005 wird '1/2000s'."""
    try:
        s = float(shutter_speed)
    except (TypeError, ValueError):
        return str(shutter_speed)
    if s <= 0:
        return str(shutter_speed)
    if s < 1:
        return f"1/{int(round(1/s))}s"
    return f"{s:.2f}s"


def _format_aperture(aperture):
    """Formatiert die Blende. Aus 4.0 wird 'f/4.0'."""
    try:
        a = float(aperture)
    except (TypeError, ValueError):
        return str(aperture)
    return f"f/{a:.1f}"


def _format_focal(focal):
    """Formatiert die Brennweite. Aus 59.0 wird '59 mm'."""
    try:
        f = float(focal)
    except (TypeError, ValueError):
        return str(focal)
    return f"{f:.0f} mm"


def load_raw_metadata(file):
    """Liest die wichtigsten RAW-Metadaten ueber rawpy.

    Kombiniert zwei Quellen:

      1. raw.other - ISO, Blende, Brennweite, Belichtungszeit, Zeitstempel.
         Diese Felder sind bei allen getesteten Kameras (Nikon, Fuji,
         Panasonic) gefuellt.

      2. EXIF aus dem eingebetteten JPEG - Hersteller, Modell, Software,
         Artist. Diese Felder sind NICHT in raw.other verfuegbar, aber
         das eingebettete JPEG enthaelt die vollstaendigen EXIF-Daten.

    Rueckgabe: {category: {key: str(value), ...}, ...}
    Bei Fehler: {"Error": {"Message": "..."}}
    """
    if rawpy is None:
        return {"Error": {"Message": "rawpy nicht installiert"}}

    result = {}

    try:
        with rawpy.imread(file) as raw:
            # --- Exposure (aus raw.other) ---
            exposure = {}
            try:
                other = raw.other
                if getattr(other, "iso_speed", None) is not None:
                    exposure["ISO"] = str(int(other.iso_speed))
                if getattr(other, "aperture", None) is not None:
                    exposure["Aperture"] = _format_aperture(other.aperture)
                if getattr(other, "shutter_speed", None) is not None:
                    exposure["Shutter"] = _format_shutter(other.shutter_speed)
                if getattr(other, "focal_length", None) is not None:
                    exposure["Focal Length"] = _format_focal(other.focal_length)
                if getattr(other, "timestamp", None) is not None:
                    exposure["Date"] = str(other.timestamp)
            except Exception:
                pass
            if exposure:
                result["Exposure"] = exposure

            # --- Camera (aus EXIF des eingebetteten JPEG) ---
            camera = {}
            try:
                img = _extract_embedded_image(raw)
                if img is not None:
                    exif = img.getexif()
                    from PIL import ExifTags
                    TAGS = ExifTags.TAGS
                    # Invertiertes Dict: Tag-Name -> Wert
                    tags_by_name = {}
                    for tag_id, value in exif.items():
                        tag_name = TAGS.get(tag_id, str(tag_id))
                        tags_by_name[tag_name] = value
                    for tag_name, label in (
                        ("Make", "Manufacturer"),
                        ("Model", "Model"),
                        ("Software", "Software"),
                        ("Artist", "Artist"),
                        ("Copyright", "Copyright"),
                    ):
                        v = tags_by_name.get(tag_name)
                        if v is None:
                            continue
                        # Strings trimmen, Leerzeichen entfernen
                        if isinstance(v, str):
                            v = v.strip()
                        elif isinstance(v, bytes):
                            try:
                                v = v.decode("utf-8", errors="replace").strip()
                            except Exception:
                                v = None
                        if v:
                            camera[label] = str(v)
            except Exception:
                pass
            if camera:
                result["Camera"] = camera

    except Exception as e:
        result["Error"] = {"Message": str(e)}

    return result


def load_raw_all_exif(file):
    """Liest alle EXIF-Tags aus dem eingebetteten JPEG.

    Fuer 'view all meta' in der Detailansicht. Liefert die rohen
    EXIF-Daten des eingebetteten JPEGs, mit demselben Kategorie-Schema
    wie MyFSImage._read_all_metadata fuer JPEGs.

    Lange Werte (>100 Zeichen) werden gekuerzt, um die Anzeige lesbar
    zu halten.

    Rueckgabe: {category: {key: str(value), ...}, ...}
    """
    if rawpy is None:
        return {}

    def _stringify(v):
        if isinstance(v, bytes):
            try:
                s = v.decode("ascii")
                if s.isprintable():
                    return s
            except Exception:
                pass
            if len(v) <= 16:
                return v.hex(" ")
            return f"(binary, {len(v)} bytes)"
        if isinstance(v, (tuple, list)):
            return ", ".join(_stringify(x) for x in v)
        if isinstance(v, dict):
            return "{" + ", ".join(f"{k}={_stringify(x)}" for k, x in v.items()) + "}"
        s = str(v)
        if len(s) > 100:
            return s[:97] + "..."
        return s

    result = {}
    try:
        with rawpy.imread(file) as raw:
            img = _extract_embedded_image(raw)
            if img is None:
                return {}
            try:
                from PIL import ExifTags
                TAGS = ExifTags.TAGS
                GPSTAGS = ExifTags.GPSTAGS
            except ImportError:
                return {}

            # --- Info (JPEG-spezifisch) ---
            info = {}
            for k, v in (img.info or {}).items():
                if k == "exif":
                    continue
                info[k] = _stringify(v)
            if info:
                result["Info"] = info

            # --- EXIF ---
            exif = img.getexif()
            if exif:
                main = {}
                for tag_id, value in exif.items():
                    tag_name = TAGS.get(tag_id, str(tag_id))
                    if tag_name in ("ExifOffset", "GPSInfo", "InteropOffset"):
                        try:
                            sub = exif.get_ifd(tag_id)
                        except Exception:
                            sub = {}
                        if tag_name == "GPSInfo":
                            result["GPS"] = {
                                GPSTAGS.get(k, str(k)): _stringify(v)
                                for k, v in sub.items()
                            }
                        else:
                            cat = "Exif" if tag_name == "ExifOffset" else "Interop"
                            result[cat] = {
                                TAGS.get(k, str(k)): _stringify(v)
                                for k, v in sub.items()
                            }
                    else:
                        main[tag_name] = _stringify(value)
                if main:
                    result["EXIF"] = main
    except Exception:
        pass

    return result