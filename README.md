### Installation:
1.  Navigere til Home Assistant config og lav en mappe ved navn "packages"
2.  Sæt koden nedenunder ind i configuration.yaml
```yaml
homeassistant:
  packages: !include_dir_named packages/
```
3. Kopiere al teksten i [update_cable_juice_planner.sh](scripts/update_cable_juice_planner.sh)
4. Navigere til Home Assistant config/scripts mappen
5. Lav en fil ved navn "update_cable_juice_planner.sh"
6. Sæt teksten ind du har kopieret
7. SSH ind i Home Assistant
8. Navigerer til scripts mappen
9. Start update_cable_juice_planner.sh
    - update_cable_juice_planner.sh vil clone denne repo i Home Assistant mappen og pyscript/ev.py vil starte.
10. Første start vil lave en yaml config fil (ev_config.yaml) i roden af Home Assistant mappen
11. Redigere denne efter dit behov
12. Genstart Home Assistant eller åben og gem ev.py filen
    - Anden start vil lave lave en yaml fil i packages mappen (packages\ev.yaml) med alle entities scriptet bruger \
        - Dette variere afhængig af om der er integrationer til solceller, el bilen osv. der bliver registreret i konfig filen
        - Alle entitier navne starter med ev_ der laves
13. Genstart Home Assistant

- Hvis du har flere elbiler laves der en kopi af ev.py til ev_2.py, den nye prefiks vil være ev_2
- I "ev2_config.yaml" -> "home.entity_ids.ignore_consumption_from_entity_ids" indsættes entity_id fra "ev_config.yaml" -> "charger.entity_ids.power_consumtion_entity_id", hvis du har solceller og 2 laderer.
---

### Todo
1. Monta understøttelse
2. Kia UVO understøttelse
3. Ladetab kalkulering ved 1 fase & 3 faser ved min & max amps
---
### Fremtiden
- Konvertere scriptet til en integration
---
> [!Note]
> ### Tilføj til dette til configuration.yaml for at kunne opdatere fra Home Assistant service
> #### Docker:
> ```yaml
>homeassistant:
>  packages: !include_dir_named packages/
>
> shell_command:
>   update_cable_juice_planner: "bash /config/scripts/update_cable_juice_planner.sh"
> ```
>
> #### Home Assistant OS:
> ```yaml
>homeassistant:
>  packages: !include_dir_named packages/
>
> shell_command:
>   update_cable_juice_planner: "bash /mnt/data/supervisor/homeassistant/scripts/update_cable_juice_planner.sh"
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
> | [![Emoji beskrivelse](Cable-Juice-Planner-Readme/emoji_description.png)](Cable-Juice-Planner-Readme/cards/emoji_description.yaml) | [![Historik](Cable-Juice-Planner-Readme/history.png)](Cable-Juice-Planner-Readme/cards/history.yaml) | [![Oversigt](Cable-Juice-> Planner-Readme/overview.png)](Cable-Juice-Planner-Readme/cards/overview.yaml) |
>
> | Uge strømpriser | Solcelleoverproduktion |
> | --- | --- |
> | [![Uge strømpriser](Cable-Juice-Planner-Readme/week_prices.png)](Cable-Juice-Planner-Readme/cards/week_prices.yaml) | [![Solcelleoverproduktion](Cable-Juice-Planner-Readme/solar_price_graf.png)](Cable-Juice-Planner-Readme/cards/solar_price_graf.yaml) |
>
> | Manuel ladning | Tur ladning |
> | --- | --- |
> | [![Manuel](Cable-Juice-Planner-Readme/manual.png)](Cable-Juice-Planner-Readme/cards/manual.yaml) | [![Tur](Cable-Juice-Planner-Readme/trip.png)](Cable-Juice-Planner-Readme/cards/trip.yaml) |
>
> | Indstillinger |  |
> | --- | --- |
> | [![Indstillinger](Cable-Juice-Planner-Readme/settings_solar_charging.png)](Cable-Juice-Planner-Readme/cards/settings_solar_charging.yaml) | [![Indstillinger](Cable-Juice-Planner-Readme/settings_fully_charged.png)](Cable-Juice-Planner-> Readme/cards/settings_fully_charged.yaml) |
> | [![Indstillinger](Cable-Juice-Planner-Readme/settings_fill_up.png)](Cable-Juice-Planner-Readme/cards/settings_fill_up.yaml) | [![Indstillinger](Cable-Juice-Planner-Readme/settings_cheap_charging.png)](Cable-Juice-Planner-Readme/cards/settings_cheap_charging.yaml) |
> | [![Indstillinger](Cable-Juice-Planner-Readme/settings_workplan.png)](Cable-Juice-Planner-Readme/cards/settings_workplan.yaml) | [![Indstillinger](Cable-Juice-Planner-Readme/settings_battery_level_preheat.png)](Cable-Juice-Planner-> Readme/cards/settings_battery_level_preheat.yaml) |
> | [![Indstillinger](Cable-Juice-Planner-Readme/settings_solar_sell_price.png)](Cable-Juice-Planner-Readme/cards/settings_solar_sell_price.yaml) | [![Indstillinger](Cable-Juice-Planner-Readme/settings_calculate_loss.png)](Cable-Juice-Planner-Readme/cards/settings_calculate_loss.yaml) |
