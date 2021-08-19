# IliasCrawler
## ⚠️ ACHTUNG ⚠️
#### Dieses Programm ist zum Herunterladen von Ilias-Inhalten als Privatkopie gedacht, um auch z.B. wenn das Ilias offline ist oder wenn du um Zug unterwegs bist lernen zu können.
#### Bitte verwende das Programm nur um Ilias-Inhalte für dich selbst herunterzuladen und gebe die Dateien nur mit ausdrücklicher Erlaubnis der Copyright-Inhaber an andere weiter!
#### Spreche die Verwendung des Programms im Zweifelsfall mit dem Ersteller der Kurse ab bevor du es verwendest!

#### Bitte beachte dass du das Programm nicht zu häufig einsetzt um die Server des Ilias nicht zu überlasten.  #### Aktiviere gegebenenfalls "antiDosRateLimit" im Skript um Pausen zwischen einzelnen Downloads zu erzeugen und die Belastung des Netzwerks zu verringern.

## Installation
1. Python installieren
  Lade dir Python auf https://www.python.org/ herunter und installiere es
2. requests installieren
  Öffne die Kommandozeile deines PCs ("cmd" in der Windows-Suche) und führe "python -m pip install requests" aus
3. BeautifulSoup installieren:
  Führe in der Kommandozeile "python -m pip install bs4" aus
4. Öffne die Datei iliasCrawler.py mit einem Texteditor und gebe bei username und password deine Ilias-Anmeldedaten ein. Füge bei baseUrl den link zu dem Kurs ein, welchen du herunterladen willst.
5. Öffne nun eine Kommandozeile im Ordner des Programms indem du im Windows-Explorer in die Dateipfadleiste klickst, "cmd" eingibst und enter drückst.

Es sollte sich eine Kommandozeile öffnen bei welcher Pfad vor dem Cursor der Pfad in dem das Programm liegt ist.

Nun sollten alles vorbereitet sein und du kannst das Programm mit "python iliasCrawler.py" starten.

## Config
Es gibt zwei config dateien, einmal `.iliassecret`
```
username
password
```

und

`.ilias_crawler_config`

Dabei kann man mit skip courses entweder kurse inkludieren oder exludieren je nachdem was man möchte man kann aber nicht beides gleichzeitig verwenden.
Eine Kurs id erhält man aus der URL (`https://ilias3.uni-stuttgart.de/goto_Uni_Stuttgart_crs_2121423.html` hier wäre die ID 2121423), diese kann man in die incl oder skip liste mit aufnehmen.
Gibt man keine der beiden Listen an werden alle Kurse in denen man mitglied ist geladen.
Eine Übersicht findet man unter:


bsp config:

```
{
    "skip_courses": []
    "incl_courses": [
        "2121423"
    ],
    "download_files": true,
    "download_opencast": true
}
```


## Todo:
1. Kein neues Herunterladen von bereits geladenen Dateien
2. Support von zusätzlichen Ilias-Strukturen (Eingebetteter Text in Ordnern, Speichern von links, etc.)

## Lizenzen
Dieses Programm verwendet FFmpeg.
Der FFmpeg-Sourcecode wurde unverändert übernommen und kompiliert von https://www.gyan.dev/ffmpeg/builds/ bezogen.
