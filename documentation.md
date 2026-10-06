Dateimeister – Landkarte
Dritte Fassung. Mit Sektion „Die cmd-Dateien" und Korrekturen zur Undo/Redo-Architektur.

1. Präambel
Der Dateimeister ist ein Bildverwaltungsprogramm für Still Photos und Videos. Er soll dem Anwender die vollständige Kontrolle darüber geben, was mit seinen Images passiert. Es laufen keinerlei Kopier- oder Löschprozesse im Hintergrund automatisch ab, sondern erst dann, wenn der Benutzer sie manuell aufruft. Er sieht den Inhalt der Befehlsdateien und kann für jedes einzelne Objekt kontrollieren, was bei der Ausführung der Befehlsdatei passiert. Dies grenzt den Dateimeister von anderen Bildverwaltungsprogrammen ab, bei denen der Anwender oft gar nicht erkennen kann, was mit seinen Images passiert. Der Dateimeister wendet sich an technisch orientierte Anwender, die maximale Kontrolle statt maximalen Komfort wünschen.

2. Ablauf aus Benutzer-Sicht
Der Benutzer öffnet den Dateimeister.

Er wählt eine Kamera aus einer Liste. Jede Kamera definiert eine Reihe von Typen (z. B. JPEG, RAW, VIDEO), jeder Typ einen Subdir (Unterordner im Ziel) und einen Rendertype (STILL / VIDEO). Jeder Typ hat Suffixe (z. B. JPG, JPEG), die angeben, welche Dateien zu diesem Typ gehören. Jedes Suffix hat ein process_image, das sagt, wie die Datei behandelt wird (JPEG, USE_JPEG, VIDEO).

Er wählt ein Quellverzeichnis (indir) und ein Zielverzeichnis (outdir).

Er klickt Generate. Der Dateimeister durchsucht das Quellverzeichnis, ordnet die gefundenen Dateien den Typen der Kamera zu und berechnet für jede Datei einen Zielpfad.

Er sieht die Bilder als Thumbnails. Jedes Bild ist zunächst Include (ausgewählt). Er kann einzelne Bilder auf Exclude setzen oder alle auf einmal.

Seine Auswahl wird historisiert, sodass er Undo und Redo benutzen kann.

Er kann Duplikate anzeigen – also Dateien aus verschiedenen Quellordnern, die denselben Zielnamen hätten.

Er klickt Exec. Der Dateimeister schreibt cmd-Dateien mit den Kopier- und Löschbefehlen und zeigt sie in einem eigenen Fenster.

Der Benutzer führt die cmd-Dateien aus (oder lässt sie ausführen).

3. Bausteine
Modul	Aufgabe
Dateimeister_support	Hauptfenster; Steuerung aller Abläufe
MyCameraTreeview	Kamera-Dialog: Kameras, Typen, Suffixe, Subdirs, Rendertypes, Process_images
dateimeister_config_xml	XML-Persistenz: Kameras, Verzeichnisse, Config-Dateien
dateimeister_generator	Berechnet aus indir + Regeln die Zielpfade (Copy-Liste)
dateimeister_video	Video-Player für die Vorschau auf dem Canvas (ffpyplayer)
MyFSImage	Detailfenster für STILL-Bilder
MyFSVideo	Detailfenster für VIDEO-Dateien (steuert mpv)
MyDuplicates	Fenster für Duplikate (gleicher Zielname, verschiedene Quellen)
PrintPreview	Druckvorschau für ausgewählte Bilder
Undo_Redo	Historisierung für Undo/Redo (drei Clients: Camera, Dateimeister, Diatisch)
tools	Hilfsfunktionen, Globals, EventManager, MyThumbnail, ScrolledTreeView
Diatisch	Eigenständige Anwendung für Diashow-Auswahl (geringe Kopplung)
Dateimeister_messages	Fenster für die Ausführung der cmd-Dateien
4. Die cmd-Dateien
Der Dateimeister erzeugt pro Imagetype drei cmd-Dateien im Verzeichnis <datadir>/cmd/. Sie sind das eigentliche Ergebnis des Programms: Der Benutzer prüft ihren Inhalt und führt sie aus.

4.1 _copy_<type>.cmd – Kopieren
Kopiert die ausgewählten Dateien aus dem Quell- ins Zielverzeichnis. Zeilen für ausgeschlossene (Exclude-)Dateien sind mit dem Kommentarzeichen (@REM unter Windows, # unter UNIX) auskommentiert und damit inaktiv. Ausgeschlossene Dateien bleiben in der Liste sichtbar, werden aber nicht kopiert.

4.2 _delete_<type>.cmd – Löschen der kopierten Dateien
Löscht die kopierten Dateien im Zielverzeichnis wieder. Das ist ein Undo in Skriptform: Wenn der Benutzer versehentlich etwas kopiert hat, kann er diese Datei ausführen, um den Zustand im Zielverzeichnis wiederherzustellen. Die Quelldateien werden nicht berührt. Die Kommentar-Logik ist dieselbe wie in der _copy_-Datei: ausgeschlossene Dateien werden nicht gelöscht.

4.3 _delrelpath_<type>.cmd – Leere Unterverzeichnisse entfernen
Löscht die leeren Unterverzeichnisse im Ziel, die durch die Option addrelpath entstanden sind. Damit bleibt das Zielverzeichnis sauber, wenn ein ganzer Ordner nach dem Löschen leer zurückbleibt.

Wenn addrelpath beim Generieren nicht benutzt wurde, wird die Datei trotzdem erzeugt, enthält aber nur den Header und keine Befehle. Eine künftige Optimierung könnte darin bestehen, sie in diesem Fall gar nicht anzulegen. (Notiert als möglicher CR.)

5. Datenfluss
Gelesen:

dateimeister_configfiles.xml – Kameras, Typen, Suffixe, Subdirs, Rendertypes, Process_images, Verzeichnisse, Config-Dateinamen

Dateimeister.ini – Pfade, Template-Datei, Grenzwerte

<templatefile> – Vorlagen für Copy-, Delete- und Delrelpath-Befehle

Quelldateien im indir (nur gelesen, nie verändert)

Config-Dateien im config-Unterordner (Auswahl-Zustände)

Zieldateien im outdir (nur gelesen, um zu prüfen, ob eine Zieldatei schon existiert und neuer ist)

Geschrieben:

<datadir>/config/dateimeister_configfiles.xml – Kamera-Definitionen, Verzeichnis-Historie, Config-Datei-Historie

<datadir>/config/<config-file>.xml – Auswahl-Zustände pro Durchlauf (Include/Exclude)

<datadir>/cmd/_copy_<type>.cmd, _delete_<type>.cmd, _delrelpath_<type>.cmd – die generierten Befehlsdateien

<datadir>/temp/ – temporäre Dateien (Druckvorbereitung, Video-Screenshots)

Zielverzeichnis – die Kopien der Quelldateien (durch den Benutzer ausgeführt)

6. Invarianten
Was immer gilt, unabhängig vom Codepfad:

Quelldateien werden niemals verändert, verschoben oder gelöscht. Der Dateimeister liest sie nur.

Das Zielverzeichnis wird nur gelesen, um zu prüfen, ob eine Datei schon existiert und neuer ist (newer-Check). Sonst wird es nur beschrieben.

Kamera-Definitionen werden nur über das Kamera-Fenster geändert. Die new_*- und update_*-Funktionen in dateimeister_config_xml werden ausschließlich von MyCameraTreeview aufgerufen.

Auswahl (Include/Exclude) wird nie im Quellbild gespeichert, sondern immer in separaten Config-Dateien.

Die XML wird nach jeder Änderung vollständig neu geschrieben (durch ET.indent + write). Das ist bewusst so gewählt und performanceunkritisch.

Include/Exclude-Änderungen werden historisiert. Für das Kamera-Fenster und das Hauptfenster gelten dabei verschiedene Undo/Redo-Clients (Undo_Redo_Camera, Undo_Redo_Dateimeister), aber derselbe Mechanismus.

Die cmd-Dateien werden erst beim Klick auf Exec (oder beim Speichern der Konfiguration) geschrieben, nicht bei jeder Auswahländerung.

7. Grenzen
Was die Anwendung ausdrücklich nicht tut:

Keine Bildbearbeitung. Bilder werden nicht skaliert, gedreht, gefiltert oder konvertiert.

Keine RAW-Konvertierung. RAW-Dateien werden entweder direkt kopiert oder über ein zugeordnetes JPEG angezeigt.

Kein Löschen von Duplikaten. Duplikate werden nur angezeigt; der Benutzer entscheidet, was er tut.

Keine Internet- und Cloud-Zugriffe. Netzwerklaufwerke und NAS-Pfade sind dagegen ausdrücklich unterstützt.

Keine automatische Ausführung der cmd-Dateien. Der Benutzer führt sie selbst aus.

Keine Formatkonvertierung von Videos. mpv und ffpyplayer werden nur zur Anzeige benutzt.

8. Offene Fragen
Invariante 5: Die XML wird bei jeder Änderung vollständig neu geschrieben. Ist das eine bewusste Entscheidung für Einfachheit, oder würdest du langfristig eine schonendere Variante bevorzugen? Für die Tests ist es unwichtig, aber für die Dokumentation würde ich es gern festhalten.

Fehlt etwas Wichtiges? Zum Beispiel der Umgang mit sehr großen Dateien, die Behandlung von Fehlern beim Kopieren, die Beziehung zwischen Globals.dict_thumbnails und Globals.dict_duplicates, oder der Zeitpunkt, an dem Globals.generated zurückgesetzt wird.

9. Mögliche künftige Änderungen (CR-Liste)
_delrelpath_<type>.cmd nur anlegen, wenn addrelpath benutzt wurde. Im Moment wird die Datei immer erzeugt, enthält aber nur den Header, wenn keine relativen Pfade vorhanden sind.

Aufräumen temporärer Dateien, eigenes Verzeichnis für pdf-Dateien, da sie eigentlich nicht temporär sind.

User Documentation

Voraussetzungen für USE_JPEG
Raw + JPEG-Fallback: Der Dateimeister sucht beim Anzeigen eines RAW ohne eingebettetes JPEG nur dann nach einem gleichnamigen JPEG, wenn im Kamera-Dialog ein JPEG-Type existiert, dessen Suffixe die entsprechenden Dateien erfassen. Ohne einen solchen Type gibt es keinen Fallback – die RAW-Datei wird als blaues Rechteck dargestellt. Das ist eine bewusste Entscheidung: Der Kamera-Dialog ist die einzige Stelle, an der das Wissen über Dateitypen und ihre Endungen lebt. Der Nutzer entscheidet durch seine Konfiguration, welche Fallbacks verfügbar sind.
Und dann in der Anleitung für den Nutzer (wenn du eine schreibst):
Wenn Sie möchten, dass der Dateimeister für Ihre RAW-Dateien auch gleichnamige JPEGs als Fallback verwendet (z.B. wenn die Kamera beide Formate parallel speichert), legen Sie im Kamera-Dialog einen zusätzlichen Type für JPEG an, der die JPEG-Endungen Ihrer Kamera enthält. Ohne diesen Type zeigt der Dateimeister nur das in die RAW eingebettete JPEG oder das blaue Rechteck.

Philosophie Canvas /Single View:
Canvas vs. Detailansicht: Der Canvas zeigt Thumbnails so schnell wie möglich. Wenn ein RAW nicht schnell dargestellt werden kann (kein eingebettetes JPEG und kein gleichnamiges JPEG als Fallback), wird es als blaues Rechteck gezeigt. Der Doppelklick öffnet die Detailansicht, die postprocess verwendet und damit auch dieses RAW darstellen kann. Der Nutzer sieht jedes Bild – im Canvas als Übersicht, in der Detailansicht in voller Qualität.
