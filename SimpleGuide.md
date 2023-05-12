# Einfacher Import von OpenStreetMap Daten

## Anleitung & Beispiel

Voraussetzungen:
- ihr habt python3 installiert
- die Umgebungsvariable `$MINETEST_GAME_PATH` ist definiert mit dem Verzeichnis eurer Minetest Installation. 
- ihr seid im Terminal im Verzeichnis, wo auch diese Datei liegt

Führt jetzt das folgende Kommando aus:
	
	`$ python3 w2mt.py -p museumsinsel -a "52.52503099278771, 13.388148610331218, 52.510432501949104, 13.41351368426145"`

Danach liegt die fertige Welt im Minetest Verzeichnis im Ordner `worlds`. Diese könnt ihr jetzt als Server starten mit:

	`$ python3 w2mt_start.py -p museumsinsel

Oder ihr startet euren Minetest Client und findet die neue Welt unter dem Namen "museumsinsel".

<img width="833" alt="Screenshot 2023-04-06 at 19 10 40" src="https://user-images.githubusercontent.com/60585/230460582-b54b61b6-31bb-4ea6-b1a4-3e70142d3be0.png">


Danach seid in der Minetest Welt der Museumsinsel

<img width="1552" alt="Screenshot 2023-05-12 at 17 55 46" src="https://github.com/holgerm/world2minetest/assets/60585/bc82f841-e4fc-49be-9714-9ad760cd0c3e">




## Weitere Optionen

### Notwendige Skript Agrumente

- `-p` oder `--project` gibt den Projektnamen an. 
- `-a` oder `--area` gibt den Bereich an, für den die Welt generiert wird. Dabei werden vier Dezimalzahlen (mit Komma getrennt) erwartet, nämlich zwei Koordinatenpaare. Dazu könnt ihr euch zwei diagonal gegenüberliegende Koordinaten aus Google Maps kopieren. Die Reihenfolge ist egal.

### Optionale Skript Agrumente

- `-w` oder `--worldname` gibt den Namen der Welt an, der sich damit von dem Ordnernamen (oder hier Projektnamen genannt) unterscheiden kann. Dieser Name wird in die `world.mt` Datei eingebaut und steht auch im Client in der Liste der Welten. Wenn ihr ihn weglasst, wird der Projektname auch als Weltname (Ordnername) verwendet.
- `-d` oder `--minetest_dir` gibt den Pfad zum Homeverzeichnis eurer Minetest Installation an. Wenn ihr die Umgebungsvariable "$MINETEST_GAME_PATH" mit dem Pfad definiert habt, könnt ihr diese Option weglassen.
- `-v` oder `--verbose`: damit könnt ihr einige Infos zu den Schritten, die das Skript durchführt auf der Konsole angezeigt bekommen.
- `-m` oder `--minimap`: dann wird eine Minimap generiert, die jeden Block mit einem Pixel farbig darstellt. Die `minimap.png` liegt im Weltordner unter `world2minetest/`. ([Klicke hier für Beispiel der Minimap von der Museuminsel](https://user-images.githubusercontent.com/60585/235302579-208e17e8-91c9-48de-b638-9d24772f33b8.png))
- `-r` oder `--reuse_query` verwendet die Anfragedatei, die schon im Projektordner liegt.
- `-q` oder `--query` verwendet die eigene Anfragedatei statt der Koordinaten. Lasst dann die Optionen `-r` sowie `-a` oder `--area` weg. Die Anfragedatei müsst oihr in der [Overpass Query Language](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) schreiben und den Dateinamen hier als Argumentwert angeben.
- `-b` oder `--backend` kann die Werte `sqlite` oder `leveldb` als Wert bekommen. Damit könnt ihr das Datenbank Backend für die Weltdaten festlegen. Default ist `sqlite`.
- `-u`or `--unrestricted` (flag without value) will include all objects in the world, not rectricted to the boundary given by the ccordinates.
- `-s`or `--start`starts the world after it has been created in server mode.


### Log

In der Datei `w2mt.log` findet ihr ein ausführliches Log über den letzten Import, den ihr durchgeführt habt inkl. Fehlermeldungen.

