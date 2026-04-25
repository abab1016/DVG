# Sprint 2 – Process Mining und Prozessanalyse

**Projekt:** DVG — Digitalisierung Eingangsrechnungsbearbeitung  
**Sprint-Zeitraum:** April 2026  
**Team:** Sam Haghighi, Efe Yueksei, Nick Rusna, Abubakar Abdi Tube  
**GitHub:** [https://github.com/abab1016/DVG]

---

## 1. Ziel des Sprints

In Sprint 2 wurde der Ist-Prozess der Eingangsrechnungsbearbeitung mit Process Mining analysiert. Grundlage dafür waren die bereitgestellten CSV-Dateien und die Auswertung in Celonis.

Ziel des Sprints war es,

- Event-Daten zu analysieren,
- Process Mining mit Celonis durchzuführen,
- tatsächliche Prozessvarianten zu identifizieren,
- Bottlenecks zu erkennen und fachlich zu diskutieren,
- erste Optimierungshypothesen als Grundlage für Sprint 3 abzuleiten.

Die Ergebnisse aus Sprint 2 dienen als Basis für Sprint 3. Dort werden auf Grundlage der Analyse ein Soll-Prozess in BPMN, konkrete Optimierungen und eine Zielarchitektur entworfen.

---

## 2. Ausgangsszenario

Das Projekt behandelt die Digitalisierung der Eingangsrechnungsbearbeitung.

Der fachliche Zielprozess aus dem Projektszenario umfasst im Kern folgende Schritte:

1. Ein Lieferant sendet eine Rechnung.
2. Ein Sachbearbeiter speichert die Rechnung inklusive Metadaten.
3. Die Rechnungsdaten werden extrahiert.
4. Die Rechnung wird geprüft und bei Erfolg freigegeben.
5. Die Rechnungsdaten werden im ERP-System erfasst.
6. Die Zahlung wird veranlasst.
7. Die Rechnung wird archiviert.

Sprint 2 fokussiert nicht auf die Implementierung neuer Komponenten, sondern auf die Analyse realer bzw. bereitgestellter Prozessdaten. Dafür wurden die Event-Daten in Celonis importiert, visualisiert und ausgewertet.

---

## 3. Datenbasis

Für die Analyse wurden zwei CSV-Dateien verwendet:

- `events_table.csv`
- `case_data_table.csv`

Diese beiden Dateien bilden gemeinsam die Datenbasis für das Process Mining.

---

### 3.1 Event Log: `events_table.csv`

Die Datei `events_table.csv` enthält die einzelnen Ereignisse bzw. Aktivitäten der Prozessfälle.

| Spalte | Bedeutung im Process Mining |
|---|---|
| `case_id` | eindeutige Fall-ID; verbindet alle Events eines Falls |
| `activity` | ausgeführte Aktivität im Prozess |
| `timestamp` | Zeitpunkt der Aktivität |
| `resource` | ausführende Person, Rolle oder System |

Die Event-Tabelle ist die zentrale Tabelle für das Process Mining. Jede Zeile beschreibt, dass in einem bestimmten Fall zu einem bestimmten Zeitpunkt eine bestimmte Aktivität ausgeführt wurde.

Die wichtigsten Felder sind:

- `case_id` als Fallkennung,
- `activity` als Aktivitätsname,
- `timestamp` als Grundlage für Reihenfolge und Durchlaufzeiten.

Ohne diese drei Felder kann kein sinnvoller Prozessgraph erzeugt werden.

---

### 3.2 Case-/Master-Daten: `case_data_table.csv`

Die Datei `case_data_table.csv` enthält zusätzliche Informationen zu den einzelnen Fällen.

| Spalte | Bedeutung |
|---|---|
| `case_id` | eindeutige Fall-ID |
| `amount` | Rechnungsbetrag |
| `vendor` | Lieferant |
| `channel` | Eingangskanal der Rechnung |

Diese Tabelle ergänzt das Event Log um fachliche Attribute. Dadurch können die Fälle zusätzlich nach Betrag, Lieferant oder Eingangskanal analysiert werden.

Die `case_id` dient in der Case-Tabelle als Primärschlüssel und in der Event-Tabelle als Fremdschlüssel. Beide Tabellen werden in Celonis über dieses Feld miteinander verbunden.

---

### 3.3 Bewertung der Datenbasis

Die CSV-Dateien sind für die Analyse geeignet, weil sie die grundlegenden Anforderungen an ein Event Log erfüllen:

- eindeutige Fallkennung über `case_id`,
- definierte Aktivitäten über `activity`,
- Zeitstempel über `timestamp`,
- zusätzliche Ressourceninformation über `resource`,
- fachliche Attribute über `amount`, `vendor` und `channel`.

Damit ist die Datenbasis ausreichend, um den Kontrollfluss, Durchlaufzeiten, Varianten und Bottlenecks zu analysieren.

---

## 4. Import und Datenmodell in Celonis

Die Daten wurden in Celonis im Bereich `Data Integration` importiert.

### 4.1 Vorgehen beim Import

Das Vorgehen beim Import war:

1. Celonis öffnen.
2. Bereich `Data Integration` auswählen.
3. Neuen Data Pool erstellen.
4. `events_table.csv` per Upload Files hochladen.
5. Spaltennamen, Trennzeichen und Datentypen prüfen.
6. Tabelle importieren.
7. `case_data_table.csv` hochladen.
8. Auch hier Spaltennamen, Trennzeichen und Datentypen prüfen.
9. Data Model erstellen.
10. `events_table.csv` als Activity Table auswählen.
11. Beide Tabellen über `case_id` verbinden.
12. `case_id`, `activity` und `timestamp` korrekt mappen.
13. Process Explorer öffnen und erste Visualisierung prüfen.

![Celonis Dashboard](../images/celonis/Dashboard_celonis_1.png)

![Data Integration in Celonis](../images/celonis/DataIntegration_celonis_2.png)

![Create from Scratch in Celonis](../images/celonis/Scratch_celonis_3.png)

![Datapool in Celonis](../images/celonis/Datapool_celonis_3.png)

![Datasource in Celonis](../images/celonis/Datasource_celonis_4.png)

![Upload der CSV-Dateien in Celonis](../images/celonis/Upload_celonis_5.png)

![Configuration des Uploads in Celonis](../images/celonis/configure_celonis.png)

![Save und Import in Celonis](../images/celonis/SaveImport_celonis.png)

![Import Grün in Celonis](../images/celonis/Import_celonis.png)

![Erstelltes Datenmodell in Celonis](../images/celonis/DataModell_celonis_6.png)

![Event-Tabelle in Celonis](../images/celonis/Events_Table_celonis_7.png)

![Case-Tabelle in Celonis](../images/celonis/Case_Table_celonis_8.png)

---

### 4.2 Mapping in Celonis

| Feld | Celonis-Rolle |
|---|---|
| `case_id` | Case ID |
| `activity` | Activity Name |
| `timestamp` | Event Timestamp |
| `resource` | Resource |
| `amount` | Case Attribute |
| `vendor` | Case Attribute |
| `channel` | Case Attribute |

Das Mapping ist entscheidend, weil Celonis daraus den Prozessgraphen, die Varianten und die Durchlaufzeiten berechnet.

![Verbindung über Case ID in Celonis](../images/celonis/CaseIdVerbindung_celonis_9.png)

![Mapping in Celonis](../images/celonis/Mapping_celonis_10.png)

---

### 4.3 Datenmodell

![Datenmodell in Celonis](../images/celonis/DataModell_celonis.png)

---

## 5. Was ist Process Mining?

Process Mining verbindet Datenanalyse mit Geschäftsprozessmanagement. Dabei werden Event Logs ausgewertet, um zu erkennen, wie ein Prozess tatsächlich ausgeführt wird.

Im Mittelpunkt stehen Fragen wie:

- Wie läuft der Prozess wirklich ab?
- Welche Prozesspfade kommen vor?
- Welche Varianten gibt es?
- Wo entstehen Schleifen oder Nacharbeit?
- Wie lange dauern einzelne Schritte?
- Wo liegen Bottlenecks?
- Welche Fälle weichen vom erwarteten Ablauf ab?

Im Gegensatz zu einer rein theoretischen Prozessbeschreibung basiert Process Mining auf tatsächlichen Ereignisdaten. Dadurch wird sichtbar, ob der reale Prozess dem gedachten Soll-Prozess entspricht oder davon abweicht.

---

## 6. Ist-Prozess

Der im Process Explorer erkennbare zentrale Ablauf der Eingangsrechnungsbearbeitung lautet:

```text
Receive Invoice
→ Register Invoice
→ Enter Invoice Data
→ Validate Invoice
→ Approve Invoice
→ Enter into ERP
→ Execute Payment
→ Archive
```

Dieser Ablauf beschreibt den fachlichen Standardfall.

### 6.1 Beschreibung des Happy Paths

| Schritt | Aktivität | Fachliche Bedeutung |
|---:|---|---|
| 1 | `Receive Invoice` | Rechnung geht beim Unternehmen ein |
| 2 | `Register Invoice` | Rechnung wird registriert und dem Prozess zugeordnet |
| 3 | `Enter Invoice Data` | Rechnungsdaten werden erfasst |
| 4 | `Validate Invoice` | Rechnung wird fachlich bzw. systemseitig geprüft |
| 5 | `Approve Invoice` | Rechnung wird freigegeben |
| 6 | `Enter into ERP` | Rechnung wird im ERP-System erfasst |
| 7 | `Execute Payment` | Zahlung wird ausgeführt |
| 8 | `Archive` | Rechnung wird archiviert |

Der Happy Path ist fachlich plausibel, weil er die Kernschritte der Eingangsrechnungsbearbeitung vollständig abbildet: Eingang, Erfassung, Prüfung, Freigabe, ERP-Verarbeitung, Zahlung und Archivierung.

---

### 6.2 Gesamtprozess in Celonis

![Process Explorer Gesamtprozess](../images/celonis/ProcessGraph_celonis.png)
![Datenmodell Prozess in Celonis](../images/celonis/prozess1_celonis.png)
![Datenmodell Prozess in Celonis](../images/celonis/prozess2_celonis.png)
![Datenmodell Prozess in Celonis](../images/celonis/prozess3_celonis.png)
![Datenmodell Prozess in Celonis](../images/celonis/prozess4_celonis.png)
![Datenmodell Prozess in Celonis](../images/celonis/prozess5_celonis.png)

---

## 7. Prozessvarianten

Die Analyse zeigt, dass nicht alle Fälle exakt dem Happy Path folgen. Neben dem Standardablauf existieren zusätzliche Aktivitäten und Sonderpfade.

Zusätzliche Aktivitäten im Datensatz sind:

- `Request Info`
- `Receive Info`
- `Compliance Check`

Diese Aktivitäten zeigen Sonderfälle und Abweichungen vom Standardprozess.

---

### 7.1 Zentrale Varianten

| Variante | Beschreibung | Fachliche Bedeutung |
|---|---|---|
| Happy Path | Standardablauf ohne Rückfragen oder Zusatzprüfungen | normaler Prozess |
| Variante ohne `Enter Invoice Data` | Rechnung wird ohne manuelle Datenerfassung weiterverarbeitet | vermutlich strukturierte oder elektronische Rechnung |
| Variante mit `Request Info` / `Receive Info` | Rückfrage wegen fehlender oder unklarer Informationen | verursacht zusätzliche Wartezeit |
| Variante mit `Compliance Check` | zusätzliche Prüfung | fachlich sinnvoll, aber zeitintensiver |
| Nicht abgeschlossene Fälle | Fälle erreichen nicht vollständig den Abschluss | kritisch zu prüfen |

---

### 7.2 Fachliche Einordnung der Varianten

Fälle mit `Request Info` und `Receive Info` sind besonders relevant, weil sie auf unvollständige oder unklare Rechnungsinformationen hindeuten. Diese Varianten führen zu zusätzlichen Schleifen und verlängern die Durchlaufzeit.

Fälle mit `Compliance Check` sind fachlich nachvollziehbar, da sie Risiko- oder Sonderfälle abbilden. Trotzdem erhöhen sie die Prozessdauer und die Varianz zwischen den Fällen.

Fälle ohne `Enter Invoice Data` können unterschiedlich interpretiert werden. Einerseits kann dies positiv sein, wenn strukturierte oder elektronische Rechnungen direkt verarbeitet werden können. Andererseits muss geprüft werden, ob dieser Pfad fachlich korrekt ist und keine notwendige Erfassung übersprungen wird.

Nicht abgeschlossene Fälle müssen gesondert betrachtet werden, da sie auf offene, fehlerhafte oder noch nicht vollständig bearbeitete Rechnungen hinweisen können.

---

### 7.3 Rework und Schleifen

Rework entsteht vor allem durch Rückfragen. Die Kombination aus `Request Info` und `Receive Info` bildet eine Informationsschleife. Diese Schleife entsteht, wenn für die weitere Bearbeitung Informationen fehlen oder unklar sind.

Fachlich bedeutet das:

- Der Prozess kann nicht direkt weiterlaufen.
- Es muss auf eine interne oder externe Antwort gewartet werden.
- Die Durchlaufzeit erhöht sich.
- Die Bearbeitung wird weniger planbar.

Diese Schleifen sind typische Kandidaten für Optimierungen, weil sie meist durch bessere Eingangsdaten, klare Pflichtfelder oder frühere Validierung reduziert werden können.

---

## 8. Bottleneck-Analyse

Die Bottleneck-Analyse zeigt deutliche Unterschiede in den Übergangszeiten zwischen den Prozessschritten. Einige Schritte laufen relativ schnell ab, andere verursachen erhebliche Wartezeiten.

Die Analyse basiert auf der Throughput Time im Celonis Process Explorer.

![Bottleneck-Analyse in Celonis](../images/celonis/Bottlenecks_celonis.png)

---

### 8.1 Durchlaufzeiten im Happy Path

| Übergang | Durchlaufzeit |
|---|---:|
| `Receive Invoice → Register Invoice` | ca. 47 Minuten |
| `Register Invoice → Enter Invoice Data` | ca. 35 Minuten |
| `Enter Invoice Data → Validate Invoice` | ca. 2 Stunden |
| `Validate Invoice → Approve Invoice` | ca. 7 Stunden |
| `Approve Invoice → Enter into ERP` | ca. 1 Stunde |
| `Enter into ERP → Execute Payment` | ca. 2 Tage |
| `Execute Payment → Archive` | ca. 17 Minuten |

Die Gesamtdurchlaufzeit des Happy Paths beträgt ca. 2,5 Tage.

Auffällig ist, dass der Übergang `Enter into ERP → Execute Payment` mit ca. 2 Tagen den mit Abstand größten Anteil an der Gesamtdurchlaufzeit hat.

---

### 8.2 Ranking der längsten Übergänge

| Rang | Übergang | Durchlaufzeit | Bewertung |
|---:|---|---:|---|
| 1 | `Enter into ERP → Execute Payment` | ca. 2 Tage | Hauptbottleneck |
| 2 | `Validate Invoice → Approve Invoice` | ca. 7 Stunden | relevanter Freigabeengpass |
| 3 | `Enter Invoice Data → Validate Invoice` | ca. 2 Stunden | mittlere Verzögerung |
| 4 | `Approve Invoice → Enter into ERP` | ca. 1 Stunde | moderater Übergang |
| 5 | `Receive Invoice → Register Invoice` | ca. 47 Minuten | geringe bis mittlere Verzögerung |
| 6 | `Register Invoice → Enter Invoice Data` | ca. 35 Minuten | geringe Verzögerung |
| 7 | `Execute Payment → Archive` | ca. 17 Minuten | unkritisch |

Der erste Übergang im Ranking ist mehr als deutlich länger als die übrigen Übergänge. Deshalb ist `Enter into ERP → Execute Payment` der wichtigste Hebel für spätere Prozessoptimierung.

---

## 9. Wichtigste Bottlenecks

### 9.1 Hauptbottleneck: `Enter into ERP → Execute Payment`

Der kritischste Engpass liegt zwischen `Enter into ERP` und `Execute Payment`.

Dieser Übergang dauert ca. 2 Tage und verursacht damit den größten Teil der gesamten Durchlaufzeit.

#### Mögliche Ursachen

- Batch-basierte Zahlungsläufe
- feste Zahlungszyklen
- manuelle Freigabe vor Zahlungsausführung
- technische oder organisatorische Wartezeit im ERP-/Zahlungssystem
- Priorisierung anderer Zahlungen
- fehlende automatische Übergabe an das Zahlungssystem

#### Auswirkung

- stark verlängerte Gesamtdurchlaufzeit
- verspätete Zahlungsausführung
- geringere Transparenz über offene Zahlungen
- potenzielle Unzufriedenheit bei Lieferanten
- schlechtere Planbarkeit des Zahlungsprozesses

#### Fachliche Bewertung

Dieser Bottleneck ist der wichtigste Optimierungshebel. Wenn dieser Übergang verkürzt wird, sinkt die gesamte Prozessdurchlaufzeit deutlich. Da die eigentliche Bearbeitung vor diesem Schritt bereits abgeschlossen ist, handelt es sich wahrscheinlich überwiegend um Wartezeit und nicht um wertschöpfende Bearbeitungszeit.

#### Optimierungsansatz

- häufigere Zahlungsläufe
- priorisierte Zahlung kritischer Fälle
- automatische Weiterleitung nach ERP-Erfassung
- SLA-Überwachung für Zahlungsausführung
- Dashboard für offene Zahlungen
- Eskalation bei Überschreitung definierter Fristen

---

### 9.2 Bottleneck: `Validate Invoice → Approve Invoice`

Der Übergang von der Validierung zur Freigabe dauert ca. 7 Stunden.

#### Mögliche Ursachen

- manuelle Prüfung durch Verantwortliche
- Verfügbarkeit der Genehmiger
- fehlende Priorisierung
- Warteschlangen bei Freigaben
- unklare Zuständigkeiten
- Freigaben erfolgen nur zu bestimmten Zeiten

#### Auswirkung

- Verzögerung um fast einen Arbeitstag
- Abhängigkeit von menschlicher Verfügbarkeit
- Prozess bleibt trotz technischer Unterstützung teilweise manuell
- längere Liegezeit zwischen Prüfung und Freigabe

#### Fachliche Bewertung

Die Freigabe ist fachlich notwendig, weil sie Kontrolle und Risikoreduktion sicherstellt. Trotzdem sollte geprüft werden, ob jede Rechnung manuell freigegeben werden muss. Besonders bei kleinen Beträgen oder bekannten Lieferanten kann eine automatisierte oder regelbasierte Freigabe sinnvoll sein.

#### Optimierungsansatz

- automatische Freigabe bei Rechnungen unter einem definierten Schwellenwert
- regelbasierte Freigabe für bekannte Lieferanten
- Eskalation bei Überschreitung definierter Wartezeiten
- digitale Freigabeaufgaben mit Benachrichtigung
- Vertreterregelung bei Abwesenheiten

---

### 9.3 Bottleneck: `Request Info` / `Receive Info`

Die Aktivitäten `Request Info` und `Receive Info` bilden eine Rückfrageschleife.

Diese entsteht vermutlich, wenn Rechnungsinformationen fehlen, unklar sind oder nicht zur Bestellung passen.

#### Mögliche Ursachen

- unvollständige Rechnungsdaten
- fehlende Pflichtangaben
- Preisabweichungen
- unklare Lieferanteninformationen
- manuelle Klärung mit externen Beteiligten
- fehlende Plausibilitätsprüfung beim Eingang

#### Auswirkung

- zusätzliche Prozessschritte
- externe Wartezeiten
- längere Durchlaufzeit
- höhere Varianz im Prozess
- schlechtere Planbarkeit
- höherer manueller Aufwand

#### Fachliche Bewertung

Diese Schleife ist problematisch, weil sie keinen direkten Mehrwert erzeugt. Sie korrigiert oder ergänzt fehlende Informationen, die idealerweise bereits beim Rechnungseingang korrekt vorhanden sein sollten. Daher ist sie ein typischer Kandidat für Datenqualitäts- und Eingangsvalidierungsmaßnahmen.

#### Optimierungsansatz

- Pflichtfeldprüfung direkt beim Rechnungseingang
- automatisierte Plausibilitätsprüfung
- Lieferantenportal mit strukturierten Eingaben
- frühzeitige Fehlererkennung vor Validierung
- klare Rückmeldungen an Lieferanten bei unvollständigen Daten

![Bottleneck bei Request Info und Receive Info](../images/celonis/BottleneckRecieveRequest_celonis.png)

---

### 9.4 Bottleneck / Zusatzaufwand: `Compliance Check`

Der `Compliance Check` ist eine zusätzliche Prüfaktivität, die nicht im Standard-Happy-Path liegt.

Fachlich ist diese Prüfung sinnvoll, wenn bestimmte Rechnungen ein erhöhtes Risiko haben oder regulatorische Anforderungen erfüllen müssen.

#### Mögliche Ursachen

- hoher Rechnungsbetrag
- unbekannter Lieferant
- risikobehafteter Eingangskanal
- interne Kontrollanforderungen
- regulatorische Anforderungen
- auffällige Rechnungsdaten

#### Auswirkung

- längere Durchlaufzeit
- zusätzliche manuelle Prüfung
- höhere Varianz zwischen Standardfällen und Sonderfällen
- potenzieller Engpass bei Compliance-Verantwortlichen

#### Fachliche Bewertung

Der `Compliance Check` ist nicht grundsätzlich negativ. Er kann notwendig sein, um finanzielle, rechtliche oder organisatorische Risiken zu reduzieren. Optimiert werden sollte daher nicht zwingend die Existenz dieser Aktivität, sondern ihre gezielte Anwendung. Eine risikobasierte Vorprüfung könnte sicherstellen, dass nur wirklich auffällige Fälle manuell geprüft werden.

#### Optimierungsansatz

- risikobasierte Compliance-Regeln
- automatisierte Vorprüfung
- manuelle Prüfung nur bei auffälligen Fällen
- transparente Kriterien für Compliance-Fälle
- Priorisierung besonders kritischer Fälle

---

## 10. Fallzahlen und Auffälligkeiten

Aus der Analyse ergeben sich folgende zentrale Kennzahlen:

| Kennzahl | Wert |
|---|---:|
| Gesamtzahl Fälle | 1.500 |
| Fälle mit `Enter Invoice Data` | ca. 1.010 |
| Anteil mit `Enter Invoice Data` | ca. 67 % |
| Fälle mit Abschluss `Archive → End` | ca. 1.420 |
| Abschlussrate | ca. 95 % |
| Nicht abgeschlossene Fälle | ca. 80 |
| Happy-Path-Durchlaufzeit | ca. 2,5 Tage |

---

### 10.1 Interpretation der Fallzahlen

Auffällig ist, dass nicht alle Fälle die manuelle Datenerfassung durchlaufen. Das kann positiv sein, wenn strukturierte oder elektronische Rechnungen direkt weiterverarbeitet werden. Es kann aber auch auf unterschiedliche Prozessvarianten oder Datenqualitätsprobleme hinweisen.

Ebenfalls auffällig sind die ca. 80 nicht abgeschlossenen Fälle. Diese Fälle sollten in einem optimierten Prozess aktiv überwacht werden. Andernfalls besteht das Risiko, dass Rechnungen liegen bleiben, Zahlungen verspätet ausgeführt werden oder Fälle nicht sauber archiviert werden.

---

### 10.2 Offene bzw. nicht abgeschlossene Fälle

Nicht abgeschlossene Fälle können verschiedene Ursachen haben:

- Fall ist zum Zeitpunkt der Datenerhebung noch aktiv.
- Fall wurde fehlerhaft beendet.
- Archivierung wurde vergessen.
- Technischer Fehler im Prozess oder in der Datenerfassung.
- Prozess wurde außerhalb des betrachteten Systems abgeschlossen.

Für Sprint 3 ergibt sich daraus die Hypothese, dass offene Fälle durch Monitoring, Fristen und Eskalationen besser kontrolliert werden sollten.

---

## 11. Wertschöpfungsanalyse

Die Aktivitäten wurden grob in wertschöpfend, geschäftswertschöpfend und nicht wertschöpfend eingeordnet.

| Aktivität / Übergang | Einordnung | Begründung |
|---|---|---|
| `Receive Invoice` | geschäftswertschöpfend | startet den Prozess und macht die Rechnung bearbeitbar |
| `Register Invoice` | geschäftswertschöpfend | Rechnung wird nachvollziehbar erfasst |
| `Enter Invoice Data` | teilweise nicht wertschöpfend | manuelle Erfassung ist notwendig, aber grundsätzlich automatisierbar |
| `Validate Invoice` | geschäftswertschöpfend | verhindert fehlerhafte Zahlungen |
| `Approve Invoice` | geschäftswertschöpfend | notwendige Freigabe und Kontrollfunktion |
| `Compliance Check` | geschäftswertschöpfend | reduziert rechtliche und finanzielle Risiken |
| `Request Info` / `Receive Info` | nicht wertschöpfend | Nacharbeit wegen unvollständiger oder unklarer Daten |
| Wartezeit bis Zahlung | nicht wertschöpfend | reine Liegezeit ohne direkten fachlichen Mehrwert |
| `Execute Payment` | wertschöpfend / geschäftswertschöpfend | Zahlung erfüllt die Verbindlichkeit gegenüber dem Lieferanten |
| `Archive` | geschäftswertschöpfend | Nachvollziehbarkeit, Dokumentation und gesetzliche Anforderungen |

---

### 11.1 Bewertung der Wertschöpfung

Der Prozess enthält mehrere notwendige Kontroll- und Dokumentationsschritte. Diese sind nicht immer direkt wertschöpfend aus Kundensicht, aber geschäftswertschöpfend, weil sie rechtliche, organisatorische oder finanzielle Risiken reduzieren.

Problematisch sind vor allem:

- Wartezeiten,
- Rückfrageschleifen,
- manuelle Datenerfassung,
- nicht abgeschlossene Fälle,
- lange Zeit zwischen ERP-Erfassung und Zahlung.

Diese Punkte erzeugen keinen direkten Mehrwert und sollten deshalb in Sprint 3 priorisiert betrachtet werden.

---

## 12. Optimierungshypothesen für Sprint 3

Aus den Analyseergebnissen ergeben sich mehrere Optimierungshypothesen für Sprint 3.

---

### 12.1 Zahlungsausführung beschleunigen

Der Übergang `Enter into ERP → Execute Payment` ist mit ca. 2 Tagen der größte Engpass. Eine Beschleunigung dieses Schritts hätte den größten Einfluss auf die Gesamtdurchlaufzeit.

#### Mögliche Maßnahmen

- häufigere Zahlungsläufe
- priorisierte Zahlung dringender Fälle
- automatische Weiterleitung nach ERP-Erfassung
- SLA-Überwachung für offene Zahlungen
- Eskalation bei Überschreitung definierter Zahlungsfristen

#### Erwarteter Nutzen

- kürzere Gesamtdurchlaufzeit
- bessere Transparenz offener Zahlungen
- schnellere Zahlung an Lieferanten
- geringere Liegezeiten im Prozess

---

### 12.2 Freigabeprozess automatisieren

Der Übergang `Validate Invoice → Approve Invoice` dauert ca. 7 Stunden. Für einfache und risikoarme Rechnungen kann eine automatische Freigabe sinnvoll sein.

#### Mögliche Maßnahmen

- automatische Freigabe unterhalb eines Schwellenwerts
- regelbasierte Freigabe bekannter Lieferanten
- Eskalation bei längerer Wartezeit
- digitale Aufgabenliste für Genehmiger
- Vertreterregelung bei Abwesenheit

#### Erwarteter Nutzen

- geringere Wartezeiten bei Standardfällen
- weniger manuelle Freigaben
- stärkere Fokussierung manueller Prüfung auf kritische Fälle
- bessere Planbarkeit des Prozesses

---

### 12.3 Rückfragen reduzieren

`Request Info` und `Receive Info` verursachen zusätzliche Schleifen und externe Wartezeiten.

#### Mögliche Maßnahmen

- Pflichtfeldprüfung beim Rechnungseingang
- strukturierter Upload über Lieferantenportal
- automatische Plausibilitätsprüfung
- klare Fehlermeldungen an Lieferanten
- Validierung von Rechnungsnummer, Betrag, Lieferant und Pflichtangaben direkt beim Eingang

#### Erwarteter Nutzen

- weniger Rückfragen
- weniger externe Wartezeit
- bessere Datenqualität
- stabilerer Prozessablauf

---

### 12.4 Manuelle Datenerfassung reduzieren

Die Aktivität `Enter Invoice Data` ist ein manueller Schritt. Wenn strukturierte Rechnungen bereits direkt verarbeitet werden können, sollte dieser Weg stärker genutzt werden.

#### Mögliche Maßnahmen

- automatische Extraktion von Rechnungsdaten
- strukturierte Rechnungsformate
- OCR oder KI-Unterstützung
- manuelle Kontrolle nur bei geringer Plausibilität
- direkte Übergabe validierter Daten an das ERP-System

#### Erwarteter Nutzen

- weniger manueller Aufwand
- geringere Fehleranfälligkeit
- schnellere Verarbeitung
- bessere Skalierbarkeit bei hohem Rechnungsvolumen

---

### 12.5 Offene Fälle überwachen

Ca. 80 Fälle wurden nicht vollständig abgeschlossen. Diese Fälle sollten aktiv überwacht werden.

#### Mögliche Maßnahmen

- Monitoring offener Fälle
- Eskalation nach definierter Frist
- Dashboard für offene Rechnungen
- automatische Erinnerung an zuständige Bearbeiter
- Statusmodell mit klaren Endzuständen

#### Erwarteter Nutzen

- weniger liegengebliebene Fälle
- bessere Kontrolle über offene Rechnungen
- höhere Abschlussquote
- bessere Nachvollziehbarkeit im Prozess

---

## 13. Priorisierung der Optimierungshypothesen

| Priorität | Optimierungshypothese | Begründung |
|---:|---|---|
| 1 | Zahlungsausführung beschleunigen | größter Bottleneck mit ca. 2 Tagen Wartezeit |
| 2 | Freigabeprozess automatisieren | zweitgrößter Engpass mit ca. 7 Stunden Wartezeit |
| 3 | Rückfragen reduzieren | reduziert Schleifen und externe Wartezeiten |
| 4 | Manuelle Datenerfassung reduzieren | reduziert Aufwand und Fehlerpotenzial |
| 5 | Offene Fälle überwachen | erhöht Prozesskontrolle und Abschlussquote |

Für Sprint 3 sollten insbesondere die ersten drei Punkte betrachtet werden, weil sie den größten Einfluss auf Durchlaufzeit und Prozessstabilität erwarten lassen.

---

## 14. Fazit

Die Process-Mining-Analyse zeigt, dass der Rechnungsprozess grundsätzlich nachvollziehbar aufgebaut ist, aber deutliche Schwachstellen in der Durchlaufzeit besitzt.

Der größte Engpass liegt zwischen `Enter into ERP` und `Execute Payment`. Dieser Schritt verursacht mit ca. 2 Tagen den größten Teil der Gesamtdurchlaufzeit. Zusätzlich entstehen Verzögerungen durch manuelle Freigaben und Rückfrageschleifen bei unvollständigen Informationen.

Für Sprint 3 sollten deshalb insbesondere folgende Punkte betrachtet werden:

1. Beschleunigung der Zahlungsausführung
2. Automatisierung einfacher Freigaben
3. Reduktion von Rückfragen durch bessere Eingangsdaten
4. Reduktion manueller Datenerfassung
5. Monitoring offener Fälle

Diese Erkenntnisse bilden die Grundlage für den Soll-Prozess und die Zielarchitektur in Sprint 3.

---

## 15. Review-Demo-Skript

Wir haben in Sprint 2 die bereitgestellten Event-Daten mit Celonis analysiert. Ziel war es, den tatsächlichen Ist-Prozess der Eingangsrechnungsbearbeitung sichtbar zu machen, Varianten zu identifizieren und Engpässe zu erkennen.

Zuerst wurden die beiden CSV-Dateien importiert. Die Event-Tabelle enthält die Aktivitäten pro Fall. Die Case-Tabelle ergänzt fachliche Attribute wie Betrag, Lieferant und Eingangskanal. Beide Tabellen wurden über die `case_id` verbunden.

Im Process Explorer sieht man den zentralen Happy Path der Eingangsrechnungsbearbeitung: Rechnungseingang, Registrierung, Datenerfassung, Validierung, Freigabe, ERP-Erfassung, Zahlung und Archivierung.

Die Analyse zeigt, dass es neben dem Standardablauf auch Sonderfälle gibt. Besonders relevant sind Rückfragen über `Request Info` und `Receive Info` sowie zusätzliche `Compliance Check`-Schritte. Diese Varianten verlängern die Durchlaufzeit und erhöhen die Prozesskomplexität.

Der größte Bottleneck liegt zwischen `Enter into ERP` und `Execute Payment`. Dieser Übergang dauert ca. 2 Tage und verursacht damit den größten Teil der Gesamtdurchlaufzeit. Weitere Verzögerungen entstehen bei der Freigabe und durch Rückfrageschleifen.

Aus der Analyse leiten wir mehrere Optimierungshypothesen für Sprint 3 ab: häufigere oder priorisierte Zahlungsläufe, automatische Freigabe einfacher Rechnungen, bessere Prüfung der Eingangsdaten, Reduktion manueller Datenerfassung und Monitoring offener Fälle.

Damit liefert Sprint 2 die Grundlage für den Soll-Prozess und die Zielarchitektur in Sprint 3.
