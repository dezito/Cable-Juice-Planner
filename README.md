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
10. update_cable_juice_planner.sh vil clone denne repo i Home Assistant mappen og pyscript/ev.py vil starte.
11. Første start vil lave en yaml config fil (ev_config.yaml) i roden af Home Assistant mappen
11. Genstart Home Assistant eller åben og gem ev.py filen
12. Anden start vil lave lave en yaml fil i packages mappen (packages\ev.yaml) med alle entities scriptet bruger \
    - Dette variere afhængig af om der er integrationer til solceller, el bilen osv. der bliver registreret i konfig filen
    - Alle entitier navne starter med ev_ der laves
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
| Emoji beskrivelse | Historik | Oversigt |
| --- | --- | --- |
| ![Emoji beskrivelse](Cable-Juice-Planner-Readme/emoji_description.png) | ![Historik](Cable-Juice-Planner-Readme/history.png) | ![Oversigt](Cable-Juice-Planner-Readme/overview.png) |

| Uge strømpriser | Solcelleoverproduktion |
| --- | --- |
| ![Uge strømpriser](Cable-Juice-Planner-Readme/week_prices.png) | ![Solcelleoverproduktion](Cable-Juice-Planner-Readme/solar_price_graf.png) |

| Manuel ladning | Tur ladning |
| --- | --- |
| ![Manuel](Cable-Juice-Planner-Readme/manual.png) | ![Tur](Cable-Juice-Planner-Readme/trip.png) |

| Indstillinger |  |
| --- | --- |
| ![Indstillinger](Cable-Juice-Planner-Readme/settings_solar_charging.png) | ![Indstillinger](Cable-Juice-Planner-Readme/settings_fully_charged.png) |
| ![Indstillinger](Cable-Juice-Planner-Readme/settings_fill_up.png) | ![Indstillinger](Cable-Juice-Planner-Readme/settings_cheap_charging.png) |
| ![Indstillinger](Cable-Juice-Planner-Readme/settings_workplan.png) | ![Indstillinger](Cable-Juice-Planner-Readme/settings_battery_level_preheat.png) |
| ![Indstillinger](Cable-Juice-Planner-Readme/settings_solar_sell_price.png) | ![Indstillinger](Cable-Juice-Planner-Readme/settings_calculate_loss.png) |
