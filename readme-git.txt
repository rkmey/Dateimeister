git tag erstellen
git tag <name>, z,B, v.1.0.0

tad gilt nur lokal! Um es auf den remote server zu bringen:
git push origin <tag_name>

das Tag auf einen anderen Rechner bringen:
git pull

ansehen mit:
git tag


Vergleich remote / local file:
git diff master:Diatisch.py -- Diatisch.py
git diff master:Dateimeister_support.py -- Dateimeister_support.py

VIEL besser mit BeyondCompare durch Anpassungen in .gitconfig (Alias, Bekanntgabe von BC):
git last Dateimeister_support.py
ACHTUNG: Groß-/Kleinschreibung beachten! Sonst passiert gar nichts - ohne Fehlermeldung
aus irgendeinem Grund funktioniert das nicht immer, deshalb jetzt neu:
git rdiff <dateiname>


lokal geänderte Datei auf Stand des letzten Commits zurücksetzen:
git restore Dateimeister_processlist.py

lokale Sicherungen:
20260826 video_player gesihert in E:\Arbeit\DATEIMEISTER_SAVE - Umbau auf pyvidplayer2

20260927: wenn man eine überflüssige Datei anlegt und anschließend löscht, zeigt git beim status deleted an.
um sie in git loszuwerden:
git commit -am "Remove obsolete comparison copy Dateimeister_FSVideo a.py"
git push.