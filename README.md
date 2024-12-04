# Ældrepleje Hjemmehjælps System

## Problemformulering

### Hvad er problemet?
Antallet af ældre, som har brug for hjemmehjælp, stiger markant, hvilket skaber et stort pres på sundhedssektoren. Samtidig er der en mangel på arbejdskraft i hjemmeplejesektoren, og behovet for medarbejdere stiger år efter år. Ifølge KL vil antallet af danskere over 80 år stige op til 422.000 i 2030, hvilket vil kræve mere end 19.000 medarbejdere i ældrepleje.

*Kilde: [Det kræver 19.000 ekstra medarbejdere til ældrepleje at opretholde nutidens serviceniveau i 2030](https://www.kl.dk)*

### Hvorfor er det et problem?
Behovet for sygeplejersker og personlig pleje i hjemmet stiger år efter år. Uden udvikling af nye løsninger risikerer vi, at sundhedssektoren bliver mere overbelastet, hvilket kan føre til en formindsket plejekvalitet og endnu længere ventetid for de ældre.

*Kilde: [Hjemmehjælpsmodtageres livskvalitet er faldet de seneste ti år - vive.dk](https://www.vive.dk)*

### For hvem er det et problem?
Dette er især en udfordring for sundhedssektoren og hjemmeplejen, som har til ansvar at sikre kvalitet og effektivitet under det stigende pres. Samtidig kan ældre borgere opleve en lavere livskvalitet, hvis de skal vente længere på pleje eller får mindre opmærksomhed på grund af mangel på ressourcer og mandskab.

## Løsning

### Teknisk løsning
For at lette presset på hjemmeplejen udvikler vi et system, der anvender sensorer og MIoT-enheder til at automatisere rutinemæssige og tidskrævende opgaver som overvågning af de ældres vitalparametre.

#### Mulige tekniske tiltag:
1. **Indlejrede Systemer**: Bærbare enheder som smart armbånd, der måler puls, temperatur og falddetektion.
2. **Programmering**: Brug af Python og Micropython til at programmere mikrocontrollere for realtidsanalyse af data.
3. **Netværksteknologi**: Trådløs dataoverførsel via MQTT til en central database med adgang via en webplatform.

### Forventet udbytte
Projektet har potentiale til at frigøre op til 700 årsværk i hjemmeplejen ved at automatisere måling af puls og temperatur. Dette vil ikke blot spare sundhedsudgifterne, men også forbedre plejekvaliteten, da plejepersonalet får mere tid til kritiske opgaver.

*Kilde: [Eksisterende teknologi kan frigøre 2.000 medarbejdere i hjemmeplejen - IT-Branchen](https://www.itbranchen.dk)*

## Kravspecifikation

### Prio 1: Skal
1. **Lydindikation før måling**
   - Afspil en kort lyd 1 minut før puls og temperatur måles.
2. **Pulsmåling og dataoverførsel**
   - Måling med nøjagtighed ±5 bpm og overførsel til server inden for 10 sekunder.
3. **Temperaturmåling og dataoverførsel**
   - Måling med nøjagtighed ±1°C og overførsel til server inden for 10 sekunder.
4. **Falddetektion og vibrationsalarm**
   - Registrering af fald med mindst 90% detektionsrate og aktivering af vibrationsalarm.
5. **Nødknap for alarmannullering**
   - Mulighed for at stoppe alarmen inden for 30 sekunder, ellers sendes besked til sundhedspersonalet.
6. **Datavisualisering på hjemmeside**
   - Alle data visualiseres på en hjemmeside med opdateringsfrekvens på mindst hvert 30. sekund.
7. **Batteridrift**
   - Systemet skal være batteridrevet med en batterilevetid på minimum 24 timer.
8. **Krypteret MQTT-kommunikation**
   - Krypteret dataoverførsel mellem mikrokontroller og server.

### Prio 2: Bør
1. **Hjemmeside viser pulsdata**
   - Visning af pulsdata med 24-timers historik.
2. **Hjemmeside viser temperaturdata**
   - Visning af temperaturdata med 24-timers historik.
3. **Adgangskontrol**
   - Login-funktion med sikkerhedsstandarder for autoriseret adgang.
4. **Realtidsalarmer ved unormale vitale tegn**
   - Alarmer ved puls >100 bpm eller <50 bpm, temperatur >38°C eller <36°C.
5. **Overholdelse af databeskyttelse (GDPR)**
   - Kryptering af alle personfølsomme data i henhold til GDPR.

### Prio 3: Kan
1. **Grafisk visualisering**
   - Grafer på hjemmesiden for at vise trends over tid.
2. **Alarm ved store udsving**
   - Beskeder eller e-mails ved pludselige ændringer i vitale tegn.
3. **Medicinsk påmindelse**
   - Påmindelser om medicinindtag via vibration eller lyd.
4. **Hændelseslogning**
   - Logning af alle hændelser og alarmer med tidsstempler.

## Stykliste

| Antal | Produkt               | Pris uden moms |
|-------|-----------------------|----------------|
| 100   | Velcro                |                |
| 1     | Tape                  |                |
| 1     | ESP32                 |                |
| 1     | Raspberry Pi Zero 2W  |                |
| 100   | Dupont kabler         |                |
| 2     | IMU-sensor            |                |
| 1     | Temperatur sensor     |                |
| 1     | Puls sensor           |                |
| 1     | Knap                  |                |
| 1     | Vibrationsmotor       |                |
| 1     | Printplade            |                |
| 20    | Lodde ting            |                |
| 10    | Modstande             |                |
| 1     | Batteri               |                |
| 1     | OpAmp                 |                |
| 1     | Kondensator           |                |
| 1     | Buzzer                |                |

## Installation

### Hardware Opsætning
1. **Montering af sensorer**: Fastgør puls-, temperatur- og IMU-sensorerne til armbåndet.
2. **Forbindelser**: Brug Dupont kabler til at forbinde sensorerne til ESP32.
3. **Strømforsyning**: Installer batteriet og sikre korrekt tilslutning til alle komponenter.
4. **Opsætning af Raspberry Pi**: Konfigurer Raspberry Pi Zero 2W som central controller.

### Software Installation
1. **Firmware**: Upload Micropython firmware til ESP32.
2. **Programmering**: Implementer Python scripts til dataindsamling og overførsel via MQTT.
3. **Server Opsætning**: Opsæt en central server til dataopbevaring og -analyse.
4. **Webplatform**: Udvikl en webbaseret platform ved hjælp af Flask til datavisualisering.

## Brug

1. **Start systemet**: Tænd armbåndet og sikre at alle sensorer er aktive.
2. **Dataoverførsel**: Sensorerne begynder automatisk at måle og sende data til serveren.
3. **Monitorering**: Plejepersonalet kan tilgå hjemmesiden for at se realtidsdata og historik.
4. **Alarmhåndtering**: Ved detektion af fald eller unormale vitale tegn sendes alarmer til plejepersonalet.

## Bidrag

Vi er åbne for samarbejde og bidrag fra både udviklere og fagfolk inden for ældrepleje. Hvis du ønsker at bidrage til projektet, følg venligst disse trin:

1. Fork repository
2. Opret en feature branch (`git checkout -b feature/ny-feature`)
3. Commit dine ændringer (`git commit -m 'Tilføj ny feature'`)
4. Push til branch (`git push origin feature/ny-feature`)
5. Åbn en pull request

## Kontakt

For spørgsmål eller feedback, kontakt os på:

- **Email**: info@pukshj.dk, info@hjemmehjaelpen.dk, info@privatenurse.dk
- **Telefon**: [Dit Telefonnummer]

## Licens

Dette projekt er licenseret under MIT License. Se [LICENSE](LICENSE) for flere detaljer.

## Forventede Resultater

- Reduceret arbejdsbyrde for plejepersonalet.
- Hurtigere og mere pålidelig sundhedsmonitorering for ældre.
- Forbedret ressourceudnyttelse i sundhedssektoren.

## Afgrænsning

Projektet fokuserer på udvikling af et system til måling af puls, temperatur og falddetektion hos ældre borgere ved hjælp af sensorer og mikrocontrollere. Avancerede funktioner som analyse af sundhedsdata eller integration i større offentlige sundhedsdatabase-systemer er ikke en del af dette projekt for at sikre fokus og realisme i udviklingen inden for deadlines.

## Projektets Faser

### 1. Empathize (Forstå brugerens behov)
- **Brugere**: Ældre borgere, plejepersonale, sundhedssektoren.
- **Brugeroplevelser**: Reduceret livskvalitet for ældre, overbelastet plejepersonale, ressourceknaphed i sundhedssektoren.
- **Dataindsamling**: Interviews, observationer, dataanalyse.

### 2. Define (Definér problemet)
- **Problemformulering**: Udvikle en teknologisk løsning til aflaster plejepersonalet, forbedrer livskvaliteten for ældre og sikrer effektivitet i hjemmeplejen.
- **Brugerbehov**: Pålidelig og hurtig pleje for ældre, tidssparende teknologi for plejepersonalet.

### 3. Ideate (Idégenerering)
- **Løsninger**: Bærbare enheder, automatisering af dataindsamling, trådløs kommunikation, brugervenlig platform.
- **Implementering**: Raspberry Pi som central controller, Python/Micropython programmering, sikkerhedsfunktioner.

### 4. Prototype (Udvikling af prototype)
- **Elementer**: Armbånd med sensorer, MQTT dataoverførsel, webbaseret platform med Flask, sikkerhedsforanstaltninger.

### 5. Test (Afprøv og iterér)
- **Testscenarier**: Brugertests, funktionstests, dataoverførselstests, sikkerhedstests.
- **Feedback og iteration**: Indhentning af feedback og optimering af løsningen baseret på testresultater.

## Teknologier Brugte

- **Hardware**: ESP32, Raspberry Pi Zero 2W, sensorer (puls, temperatur, IMU), batterier, vibrationsmotorer.
- **Software**: Micropython, Python, MQTT, Flask.
- **Kommunikation**: Krypteret MQTT-protokol.
- **Webplatform**: Flask-baseret hjemmeside til datavisualisering og adgang for plejepersonale.

---

Tak for din interesse i vores projekt! Vi ser frem til at samarbejde med jer for at forbedre ældreplejen gennem innovative teknologiske løsninger.

