# 🚗Cable Juice Planner🔋🌞📅 til Home Assistant (PyScript)

### Beskrivelse:
Planlægger og styrer opladning af elbil, ud fra en arbejdsplan eller de billigste tider over en uge.

Ved **Solcelleoverskud til opladning**, oplades bilen med solcelle overskudsproduktion, den kan indstilles til at bruge alt strøm i nuværende time også selv, hvis opladningen starter senere i nuværende time, vil den bruge alt overproduktion fra timen, den kan også indstilles til x antal minutter tilbage.

Ved **Arbejdsplan opladning**, specificere man nødvendig kilometer per arbejdsdag, afgang, hjemkomst og forvarm valg. Scriptet finder de billigste tider at lade bilen på og starter/stopper selv ladningen derefter, forvarmer bilen til afgang, hvis valgt

Ved **Optimal ugeopladning (uden Arbejdsplan)**, specificere man forventer antal kilometer, der køres per dag. Scriptet deler differencen mellem nuværende batteriniveau (f.eks. 27%) og **Elbilens maks anbefalet ladingsprocent** (f.eks. 90%) op i 3 dele (f.eks. 63%/3=21%) og på 1/4/7 dag(e) fra nu af finder de billigste tider at lade bilen på og starter/stopper selv ladningen derefter.

Der understøttes nuværende/fremtidig (prognose) solcelle overproduktion og powerwall afladning i planlægningen og under opladning

<a href="https://sloth.nu/tesla_solar_demo.gif" target="_blank"><img src="images/tesla_solar_demo_small.gif" width="49%"></a><a href="https://sloth.nu/virtual_ev_demo.gif" target="_blank"><img src="images/virtual_ev_demo_small.gif" width="49%"></a>
[![Opladnings periode](images/charging_period.png)]
---

### Funktioner:
- Detaljeret opladningshistorik
- Solcelle over produktion til rådighed i nuværende time (tilvalg)
- Nuværende strømpris med fratrukket solcelle overproduktion
- Oversigter:
  - Planlagte opladninger
  - Afgangsplan
  - Solcelle over produktion prognose
- Tur planlægning
- Manuel opladning
- Emoji forklaring
- Tvangsladning under daglig batteri niveau (op til **Daglig hjemkomst batteri niveau** f.eks. 30%)
- Udregning af reel (med detaljeret historik):
  - Kørsel effektivitet
  - km/kWh
  - Estimerede rækkevidde
- Refusion af elafgift

- ### Indstillinger:
  - Opladningsregler:
    - Solcelleoverskud til opladning
    - Arbejdsplan opladning
    - Optimal ugeopladning (uden Arbejdsplan)
  - Automatisk fuld opladning, hver X antal dage
  - Automatisk opladning ved billig og meget billig strøm
  - **Batteriniveau- og Forvarmningsindstillinger for Elbil** indstillinger:
    - Daglig hjemkomst batteri niveau efter arbejde (minimum)
    - Tur hjemkomst batteri niveau
    - Elbilens minimum ladingsprocent
    - Elbilens maks anbefalet ladingsprocent
  - Solcelleoverproduktion Salgspris, fastpris eller nuværende salgspris (fratrukket udgifter for at sælge det)
  - Kalkulering af lade tab

### Påkrævet integrationer
- HACS (https://github.com/hacs/integration)
- PyScript (https://github.com/custom-components/pyscript)
- Energi Data Service (Carnot) (https://github.com/MTrab/energidataservice)
- Sun

### Understøttet og testet integrationer
- [Easee Charger](https://github.com/nordicopen/easee_hass)
- [Kia UVO](https://github.com/Hyundai-Kia-Connect/kia_uvo) (Forvarmning ikke understøttet endnu)
- [Tessie](https://www.home-assistant.io/integrations/tessie/)
- [TeslaFi](https://github.com/jhansche/ha-teslafi)
- [Tesla](https://github.com/alandtse/tesla)
- [Fronius](https://www.home-assistant.io/integrations/fronius/)
- [Kostal](https://www.home-assistant.io/integrations/kostal_plenticore/)
- [Huawei Solar](https://github.com/wlcrs/huawei_solar)

### Todo
1. Monta understøttelse
2. Kia UVO understøttelse
3. [Zaptec EV charger](https://github.com/custom-components/zaptec)
3. Ladetab kalkulering ved 1 fase & 3 faser ved min & max amps
4. Gør at scriptet ikke låser Home Assistant når den kører charge_if_needed()
---
### Fremtiden
- Konvertere scriptet til en integration

---

### Installation:
1.  Navigere til Home Assistant config mappen
2.  Sæt koden nedenunder ind i configuration.yaml
```yaml
homeassistant:
  packages: !include_dir_named packages/
```
3. Kopiere al teksten i [update_cable_juice_planner.sh](scripts/update_cable_juice_planner.sh)
4. Lav en fil ved navn "install_cable_juice_planner.sh" (lige meget hvor)
5. Sæt teksten ind du har kopieret
6. SSH ind i Home Assistant
7. Navigerer til scripts mappen
8. Start "bash install_cable_juice_planner.sh"
    - install_cable_juice_planner.sh vil clone denne repo i Home Assistant mappen og pyscript/ev.py vil starte.
9. Ved første start vil den lave en yaml config fil (ev_config.yaml) i roden af Home Assistant mappen
10. Redigere denne efter dit behov
11. Genstart Home Assistant eller åben og gem ev.py filen
    - Ved anden start vil den lave en yaml fil i packages mappen (packages\ev.yaml) med alle entities scriptet bruger \
        - Dette variere afhængig af om der er integrationer til solceller, el bilen osv. der bliver registreret i konfig filen
        - Alle entitier navne starter med ev_ der laves
12. Genstart Home Assistant
13. Evt. Copy & Paste kortene i [Cable-Juice-Planner/cards mappen](cards) mappen

- Ved flere elbiler køres kommando "ln -n Cable-Juice-Planner/pyscript/ev.py pyscript/ev2.py" i SSH, dette laver en ny hardlink til ev.py, den nye prefiks vil være ev2
  - I "ev2_config.yaml" -> "home.entity_ids.ignore_consumption_from_entity_ids" indsættes entity_id fra "ev_config.yaml" -> "charger.entity_ids.power_consumtion_entity_id", hvis du har solceller og 2 laderer.

<center>

### [Konfiguration eksempler](config_examples)

</center>

### Opdatering fra ældre version:

- Hvis man opdaterer fra en ældre version med Cable-Juice-Planner-Readme i config mappen, skal man kører opdateringen 3 gange.
  - Hvis Cable-Juice-Planner-Readme stadig er i config mappen, skal man copy & paste alt i [update_cable_juice_planner.sh](scripts/update_cable_juice_planner.sh) og sætte ind i /config/scripts/update_cable_juice_planner.sh og opdatere 3 gange igen

---

### Filer der laves i roden af Home Assistant mappen:
- ev_config.yaml **(Konfigurations filen)**
- ev_charging_history_db.yaml **(Opladningshistorik database)**
- ev_drive_efficiency_db.yaml **(Kørselseffiktivitet procent database)**
- ev_km_kwh_efficiency_db.yaml **(Km/Kwh database)**
- ev_kwh_avg_prices_db.yaml **(Offline strøm priser database)**
- ev_solar_production_available_db.yaml **(Solcelle over produktion database)**


---
> [!Note]
> ### Tilføj til dette til configuration.yaml for at kunne opdatere fra Home Assistant service
> #### Docker:
> ```yaml
>homeassistant:
>  packages: !include_dir_named packages/
>
> shell_command:
>   update_cable_juice_planner: "bash /config/Cable-Juice-Planner/scripts/update_cable_juice_planner.sh"
> ```
>
> #### Home Assistant OS:
> ```yaml
>homeassistant:
>  packages: !include_dir_named packages/
>
> shell_command:
>   update_cable_juice_planner: "bash /mnt/data/supervisor/homeassistant/Cable-Juice-Planner/scripts/update_cable_juice_planner.sh"
> ```
---
> [!Note]
> ### Lav et script og modtag resultat i en notifikation
> 1. Indstillinger
> 2. Automatiseringer & Scener
> 3. Scripts
> 4. Tilføj Script
> 5. Opret nyt script
> 6. Klik på ⋮
> 7. Rediger i YAML
> 8. Copy & Paste koden nedenunder
> 9. Gem script
> ```yaml
> alias: Cable Juice Planner Opdatering
> sequence:
>   - service: shell_command.update_cable_juice_planner
>     data: {}
>     response_variable: return_response
>   - if: "{{ return_response['returncode'] == 0 }}"
>     then:
>       - service: persistent_notification.create
>         metadata: {}
>         data:
>           title: Cable Juice Planner Opdatering
>           message: "{{ return_response['stdout'] }}"
>     else:
>       - service: persistent_notification.create
>         metadata: {}
>         data:
>           title: Cable Juice Planner Opdatering ERROR
>           message: "{{ return_response['stderr'] }}"
> description: ""
> icon: mdi:cloud-download
> ```

> [!Note]
> Klik på et billede nedenunder for at få Home Assistant kortet
> | Emoji beskrivelse | Historik | Oversigt |
> | --- | --- | --- |
> | [![Emoji beskrivelse](images/emoji_description.png)](cards/emoji_description.yaml) | [![Historik](images/history.png)](cards/history.yaml)<br>[Virtuel batteriniveau entity](cards/history_emulated_battery.yaml) | [![Oversigt](images/overview.png)](cards/overview.yaml) |
>
> | Uge strømpriser | Solcelleoverproduktion |
> | --- | --- |
> | [![Uge strømpriser](images/week_prices.png)](cards/week_prices.yaml) | [![Solcelleoverproduktion](images/solar_price_graf.png)](cards/solar_price_graf.yaml) |
>
> | Manuel ladning | Tur ladning |
> | --- | --- |
> | [![Manuel](images/manual.png)](cards/manual.yaml) | [![Tur](images/trip.png)](cards/trip.yaml) |
>
> | Indstillinger |  |
> | --- | --- |
> | [![Indstillinger](images/settings_solar_charging.png)](cards/settings_solar_charging.yaml) | [![Indstillinger](images/settings_fully_charged.png)](Readme/cards/settings_fully_charged.yaml) |
> | [![Indstillinger](images/settings_fill_up.png)](cards/settings_fill_up.yaml) | [![Indstillinger](images/settings_cheap_charging.png)](cards/settings_cheap_charging.yaml) |
> | [![Indstillinger](images/settings_workplan.png)](cards/settings_workplan.yaml) | [![Indstillinger](images/settings_battery_level_preheat.png)](Readme/cards/settings_battery_level_preheat.yaml) |
> | [![Indstillinger](images/settings_solar_sell_price.png)](cards/settings_solar_sell_price.yaml) | [![Indstillinger](images/settings_calculate_loss.png)](cards/settings_calculate_loss.yaml) |


