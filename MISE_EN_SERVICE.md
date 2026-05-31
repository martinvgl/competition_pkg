# Mise en service — de zéro (sans carte préalable)

Robot d'évacuation `competition_pkg` + carte dynamique (`obstacle_mapper`).

Le principe en deux temps : on **construit d'abord une carte** au SLAM et on la
**sauvegarde**, puis on lance la mission en **republiant cette carte comme
référence statique**. Le nœud `obstacle_mapper` lit `/map` une seule fois au
démarrage ; il lui faut donc une carte stable, pas un SLAM en cours.

> Conventions de commandes ci-dessous :
> - **[env]** = terminal *dans* l'environnement Singularity (`. 0_env.sh` puis
>   `. /entrypoint.sh`), workspace sourcé.
> - **[robot]** = terminal connecté au TurtleBot3 (SSH), **sans** environnement.
> - Les hôtes/SSH et `turtlebot3_mode` sont spécifiques au montage du cours :
>   adapte-les à ta salle si besoin.

---

## Phase 0 — Préparation (une seule fois)

### 0.1 Placer le package dans le workspace

```bash
# Décompresser competition_pkg-mapper.zip puis :
mv competition_pkg ~/ros2_lecture_ws/src/
```

### 0.2 Entrer dans l'environnement et compiler — [env]

```bash
cd ~/ros2_lecture_ws
. 0_env.sh
. /entrypoint.sh
colcon build --symlink-install
source install/setup.bash
```

### 0.3 Dépendances (si pas déjà installées)

```bash
sudo apt update
sudo apt install python3-opencv ros-humble-cv-bridge \
                 ros-humble-slam-toolbox ros-humble-navigation2 \
                 ros-humble-nav2-bringup
```

### 0.4 Vérifier que l'entry point existe — [env]

```bash
ros2 pkg executables competition_pkg
# Doit lister : sm, fakerobot, obstacle_mapper
```

### 0.5 Créer le dossier des cartes

```bash
mkdir -p ~/ros2_lecture_ws/maps
```

---

## Phase 1 — Construire et sauvegarder la carte (SLAM)

Objectif : parcourir tout l'environnement au téléopérateur pendant que
`slam_toolbox` construit la carte, puis la sauvegarder.

### 1.1 Synchronisation horloge — [robot, sans env]

```bash
turtlebot3_mode
```

### 1.2 Démarrer le robot — [robot]

```bash
ssh -YC turtle@192.168.11.2          # mot de passe : turtlebot
ros2 launch ros2_lecture bringup.launch.py
```

> Variante hors salle de cours : `ros2 launch turtlebot3_bringup robot.launch.py`.
> Variante simulation : `ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py`.
> Dans tous les cas, cette étape doit publier `/scan`, `/odom`, `/tf` et écouter `/cmd_vel`.

### 1.3 Lancer le SLAM — [env]

```bash
ros2 launch slam_toolbox online_async_launch.py
```

### 1.4 RViz pour visualiser la carte en construction — [env]

```bash
rviz2
```

Ajoute un display **Map** sur le topic `/map`, et un display **LaserScan** sur
`/scan`. Fixe le *Fixed Frame* à `map`.

### 1.5 Téléopérer pour cartographier — [env]

```bash
ros2 run turtlebot3_teleop teleop_keyboard
```

Conduis lentement le robot pour couvrir **toute** la zone (le long des murs,
dans chaque recoin). Évite les rotations trop rapides : elles dégradent la
qualité du SLAM. **Note le point de départ** : c'est là que tu réinitialiseras
la pose en phase 2 (voir 2.5).

### 1.6 Sauvegarder la carte — [env, nouveau terminal sourcé]

Quand la carte est complète et propre dans RViz :

```bash
ros2 run nav2_map_server map_saver_cli -f ~/ros2_lecture_ws/maps/competition_map
```

Cela crée `competition_map.yaml` + `competition_map.pgm`. Vérifie :

```bash
ls -l ~/ros2_lecture_ws/maps/
cat ~/ros2_lecture_ws/maps/competition_map.yaml
```

### 1.7 Arrêter le SLAM, le teleop et le bringup

`Ctrl+C` dans les terminaux SLAM, teleop et robot. La carte est maintenant
sur disque ; on repart proprement en phase 2.

---

## Phase 2 — Mission (carte statique + carte dynamique)

À partir d'ici, `map_server` republie la carte sauvegardée sur `/map` (statique
et *latched*), AMCL localise le robot dessus, Nav2 navigue, et le mapper compare
le LiDAR à cette référence.

### 2.1 Synchronisation horloge — [robot, sans env]

```bash
turtlebot3_mode
```

### 2.2 Démarrer le robot — [robot]

```bash
ssh -YC turtle@192.168.11.2
ros2 launch ros2_lecture bringup.launch.py
```

### 2.3 Localisation + carte statique — [env]

```bash
ros2 launch nav2_bringup localization_launch.py \
    map:=$HOME/ros2_lecture_ws/maps/competition_map.yaml
```

Cela lance `map_server` (publie `/map`) **et** AMCL (fournit la TF `map → odom`).

### 2.4 Pile de navigation — [env]

```bash
ros2 launch nav2_bringup navigation_launch.py
```

> Alternative en une commande pour 2.3 + 2.4 :
> `ros2 launch nav2_bringup bringup_launch.py map:=$HOME/ros2_lecture_ws/maps/competition_map.yaml`

### 2.5 Initialiser la pose dans RViz — [env]

```bash
rviz2
```

- *Fixed Frame* = `map`.
- Ajoute un display **Map** sur `/map` (référence), et **un second display Map
  sur `/updated_map`** (carte dynamique avec les nouveaux obstacles).
- Clique **2D Pose Estimate** et place la flèche **à l'endroit et l'orientation
  réels du robot** (idéalement le point de départ noté en 1.5). AMCL converge.

> Important : le mapper fusionne `/odom` directement avec la grille `map`. Pour
> que les obstacles tombent au bon endroit, démarre le robot **au même point**
> que celui où tu as lancé le SLAM (origine de l'odométrie ≈ origine de la
> carte). Sinon attends-toi à un léger décalage (voir Notes).

### 2.6 Caméra (requise par l'état Follow) — [env]

```bash
ros2 run competition_pkg fakerobot      # ou le vrai nœud caméra
```

### 2.7 Carte dynamique — [env]

```bash
ros2 run competition_pkg obstacle_mapper
```

Tu dois voir dans ses logs :
`Reference map received: WxH cells, resolution=...m/cell`.
Si ce message **n'apparaît pas**, voir Dépannage (carte non reçue).

### 2.8 Machine à états — [env]

```bash
ros2 run competition_pkg sm
# Appuie sur ENTER pour démarrer la mission
```

### 2.9 (Optionnel) Visualiseurs

```bash
ros2 run yasmin_viewer yasmin_viewer_node     # puis http://localhost:8080
rqt_image_view                                 # topic /debug_image (caméra)
```

---

## Ordre de lancement (récapitulatif mission)

| # | Terminal | Commande |
| - | -------- | -------- |
| 1 | [robot]  | `turtlebot3_mode` |
| 2 | [robot]  | bringup robot (`ros2 launch ros2_lecture bringup.launch.py`) |
| 3 | [env]    | `nav2_bringup localization_launch.py map:=...competition_map.yaml` |
| 4 | [env]    | `nav2_bringup navigation_launch.py` |
| 5 | [env]    | `rviz2` → Fixed Frame `map`, Map `/map` + `/updated_map`, 2D Pose Estimate |
| 6 | [env]    | `ros2 run competition_pkg fakerobot` |
| 7 | [env]    | `ros2 run competition_pkg obstacle_mapper` |
| 8 | [env]    | `ros2 run competition_pkg sm` → ENTER |

---

## Vérifications rapides

```bash
# La carte de référence est publiée et latched ?
ros2 topic info /map --verbose          # Durability doit être TRANSIENT_LOCAL

# La carte dynamique sort à ~1 Hz ?
ros2 topic hz /updated_map

# Les alertes nouveaux obstacles arrivent ?
ros2 topic echo /new_obstacle

# Les entrées du mapper sont vivantes ?
ros2 topic hz /scan
ros2 topic hz /odom
```

Test concret : place un objet **nouveau** (absent lors du SLAM) dans une zone
libre, à portée du LiDAR. Tu dois voir un `[NEW OBSTACLE] position: ...` sur
`/new_obstacle` et la cellule passer en obstacle sur `/updated_map` dans RViz.

---

## Dépannage

**Le mapper n'affiche jamais « Reference map received ».**
La QoS de `/map` doit être `transient_local` des deux côtés. Le nœud souscrit
déjà ainsi ; vérifie côté publieur avec `ros2 topic info /map --verbose`. Assure-toi
que `localization_launch.py` (donc `map_server`) tourne bien avant de regarder.

**`/updated_map` reste identique à `/map`, aucun obstacle détecté.**
Vérifie que `/scan` et `/odom` publient (`ros2 topic hz ...`). Vérifie aussi que
la pose AMCL est initialisée (2D Pose Estimate) et que l'objet test est bien
dans une zone **libre** de la carte de référence.

**Les obstacles apparaissent décalés sur `/updated_map`.**
C'est le couplage `/odom`↔`map` (le nœud utilise l'odométrie brute, pas la TF
`map→odom`). Redémarre la mission avec le robot au point de départ du SLAM. Pour
une robustesse totale, il faut passer le nœud sur `tf2` (changement séparé, hors
périmètre minimal — je peux le faire si tu veux).

**Nav2 / la SM ne bougent pas.**
La SM `sm` attend un appui sur **ENTER**. Nav2 a besoin d'une pose initiale
valide (AMCL) et d'un goal ; l'état `Navigation` envoie un goal vers
`(0, 0)` — assure-toi que ce point est atteignable dans ta carte.

**`obstacle_mapper` introuvable.**
Tu n'as pas rebuild après avoir ajouté le package :
`colcon build --symlink-install && source install/setup.bash`.
