Projekt: Sundhedsovervågning med MQTT og Flask
==============================================

Dette projekt er en del af uddannelsen IT-Teknolog ved KEA. Det er udviklet af gruppemedlemmerne Emil, Javier og Morten under vejledning af lærerne Bo og Charlie. Projektet fokuserer på overvågning af sundhedsdata med brug af MQTT, Flask, og en kombination af hardware- og softwareteknologier.

Formål
------

Projektets mål er at udvikle et system, der kan overvåge vitale tegn fra sensorer, håndtere nødalarmer og give brugervenlig adgang til data gennem et webinterface. Systemet er designet til brug i sundhedssektoren, fx på plejehjem.

Funktioner
----------

### 1\. MQTT-integration

-   **Beskeder mellem sensorer og backend**: Systemet bruger MQTT til at kommunikere mellem hardwareenheder og backend.

-   **Relay**: Beskeder bliver videresendt mellem en lokal og en fjern MQTT-broker.

-   **Automatiske notifikationer**: Systemet sender e-mails ved kritiske hændelser som fald eller nødsituationer.

### 2\. Databasehåndtering

-   Vitale tegn som puls og batteriniveau bliver krypteret og gemt i en database.

-   Data kan filtreres efter CPR-nummer og tidsintervaller.

### 3\. Webinterface

-   **Login og adgangskontrol**: Brugere kan logge ind for at se data.

-   **Visning af data**: Webinterfacet viser data for specifikke patienter baseret på deres CPR-nummer.

-   **Anmodning om opdateringer**: Brugere kan bede systemet om at opdatere patientdata via MQTT.

### 4\. Hardware-integration

-   Sensorer til overvågning af puls, batteriniveau og fald.

-   MPU6050 accelerometer til faldregistrering.

-   Alarm med vibration og MQTT-beskeder.

### 5\. Kryptering

-   Kryptering og dekryptering af data ved brug af AES for at sikre datasikkerhed.

### 6\. Logging og fejlhåndtering

-   Fejl og hændelser logges i systemet for debugging og analyse.

Teknologier
-----------

### Backend

-   Flask til webapplikationen og REST API.

-   Flask-Login til autentificering.

-   Flask-SQLAlchemy til databasehåndtering.

### Kommunikation

-   Paho-MQTT til beskedhåndtering.

-   E-mailnotifikationer via SMTP.

### Hardware

-   Raspberry Pi og ESP32 til sensordataindsamling og beskedhåndtering.

-   MPU6050 til faldregistrering.

### Database

-   Microsoft SQL Server til lagring af krypterede data.

### Kryptering

-   Pycryptodome til AES-kryptering.

Installation
------------

1.  Klon projektet fra GitHub:

    ```
    git clone https://github.com/JavierVolpe/IoMT3-ITTek-3A2
    ```

2.  Installer afhængigheder:

    ```
    pip install -r requirements.txt
    ```

3.  Konfigurer `.env`-filen med relevante indstillinger:

    ```
    DB_USERNAME=<brugernavn>
    DB_PASSWORD=<adgangskode>
    MQTT_BROKER_URL=<broker-url>
    SECRET_KEY=<krypteringsnøgle>
    ```

4.  Kør Flask-appen:

    ```
    python app.py
    ```

Brugsanvisning
--------------

1.  Log ind på webinterfacet med dine brugeroplysninger.

2.  Indtast et CPR-nummer for at søge efter vitale tegn.

3.  Anmod om opdateringer ved at klikke på "Request Update".

4.  Se nødnotifikationer i realtid via MQTT.

Projektstruktur
---------------

-   `app.py`: Flask-applikationens hovedfil.

-   `mqtt_listener.py`: Håndtering af MQTT-beskeder.

-   `models.py`: Database- og datamodeldefinitioner.

-   `config.py`: Konfigurationer til database og MQTT.

-   `encryption.py`: Funktioner til kryptering og dekryptering.

-   `requirements.txt`: Liste over afhængigheder.

Team
----

-   **Gruppemedlemmer**: Emil Fabricius Schlosser, Javier Alejandro Volpe, Morten Hamborg Johansen

-   **Vejledere**: Bo Hansen og Charlie Demasi
