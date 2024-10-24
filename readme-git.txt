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