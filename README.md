# Appliance Patterns

Intégration Home Assistant dédiée à l'apprentissage local des profils énergétiques d'appareils ménagers. Elle collecte les séries temporelles des capteurs de puissance, isole les cycles, découvre automatiquement les motifs récurrents et fournit en temps réel le programme détecté, la phase en cours, le temps restant estimé et la confiance associée.

## Installation

1. Copier le dossier `custom_components/appliance_patterns` dans votre instance Home Assistant (dossier `config/custom_components`).
2. Redémarrer Home Assistant.
3. Ajouter l'intégration via *Paramètres → Appareils et services → Ajouter une intégration* et sélectionner **Appliance Patterns**.

## Configuration

Chaque entrée de configuration représente un appareil et accepte :

| Option | Description |
| --- | --- |
| `name` | Nom de l'appareil (utilisé pour les entités) |
| `power_sensors` | Liste des capteurs de puissance (W) à surveiller |
| `on_power` | Seuil de démarrage (W) |
| `off_power` | Seuil d'arrêt (W) |
| `off_delay` | Durée en secondes sous le seuil avant clôture du cycle |
| `sample_interval` | Intervalle de sous-échantillonnage (s) |
| `window_duration` | Taille de la fenêtre de détection (s) |
| `min_run_duration` | Durée minimale d'un cycle pour être enregistré |

Configuration YAML (optionnelle) :

```yaml
appliance_patterns:
  appliances:
    - name: lave_vaisselle
      power_sensors:
        - sensor.lave_vaisselle_power
      on_power: 20
      off_power: 5
      off_delay: 120
      sample_interval: 5
      window_duration: 1800
      min_run_duration: 600
```

## Fonctionnement ML

- **Collecte** : l'intégration construit une fenêtre glissante (par défaut 30 min) alimentée par les capteurs sélectionnés et détecte automatiquement les démarcations de cycle via les seuils on/off.
- **Prétraitement** : chaque cycle est sous-échantillonné, normalisé et stocké localement (API Storage de Home Assistant, pas de Cloud).
- **Découverte de motifs** : un modèle incrémental regroupe les cycles par similarité (DTW) et génère des gabarits moyens. Chaque gabarit conserve durée moyenne, enveloppe de variance et segments de phases extraits par analyse de pente.
- **Détection temps réel** : la fenêtre active est comparée aux gabarits via DTW. Le meilleur score fournit programme, phase courante, temps restant (`durée_apprise - temps_ecoulé`) et confiance normalisée.

## Entités créées

Pour un appareil nommé `lave_vaisselle` :

- `sensor.lave_vaisselle_state`
- `sensor.lave_vaisselle_program`
- `sensor.lave_vaisselle_phase`
- `sensor.lave_vaisselle_time_remaining`
- `sensor.lave_vaisselle_confidence`

## Services

| Service | Description |
| --- | --- |
| `appliance_patterns.reset_patterns` | Réinitialise les motifs appris pour une entrée (paramètre `entry_id`). |
| `appliance_patterns.export_patterns` | Exporte les cycles et gabarits vers l'événement `appliance_patterns_exported`. |
| `appliance_patterns.import_patterns` | Importe un jeu de motifs/cycles (paramètres `entry_id`, `payload`). |

## Exemple Lovelace

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Lave-vaisselle
    entities:
      - sensor.lave_vaisselle_state
      - sensor.lave_vaisselle_program
      - sensor.lave_vaisselle_phase
  - type: gauge
    name: Confiance
    entity: sensor.lave_vaisselle_confidence
    min: 0
    max: 100
  - type: sensor
    entity: sensor.lave_vaisselle_time_remaining
    graph: line
    detail: 2
```

## Tests

Quatre jeux de tests couvrent :

1. Collecte et détection des cycles (logique `RunTracker`).
2. Distance DTW.
3. Groupement des cycles.
4. Prédiction du temps restant.

Lancer la suite depuis la racine :

```bash
pytest
```
