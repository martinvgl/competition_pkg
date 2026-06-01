# Mise en service — de zéro

Procédure complète : construire la carte, puis lancer la mission avec la carte
dynamique. Méthode de la Lecture 3 (Cartographer + `turtlebot3_navigation2`).

## Amorce d'environnement — dans chaque terminal `ros2`

```bash
cd ~/ros2_lecture_ws
. 0_env.sh
. /entrypoint.sh
. 4a_turtlebot3_settings.sh
source install/setup.bash
```

Mots de passe : `turtlebot3_mode` -> `r0s1ecture` ; SSH robot -> `turtlebot`.
Les terminaux **[robot]** (synchro, SSH) tournent sans environnement.

---

## Phase 0 — Préparation (une seule fois)

1. Placer le package : `mv competition_pkg ~/ros2_lecture_ws/src/`
2. Compiler — [env] :
   ```bash
   colcon build --symlink-install
   source install/setup.bash
   ```
3. Vérifier les exécutables : `ros2 pkg executables competition_pkg`
   (doit lister `sm`, `fakerobot`, `obstacle_mapper`).
4. Créer le dossier des cartes : `mkdir -p ~/ros2_lecture_ws/maps`

---

## Phase 1 — Construire et sauvegarder la carte

1. **[robot]** Synchro horloge : `turtlebot3_mode`
2. **[robot]** Robot :
   ```bash
   ssh -YC turtle@192.168.11.2
   ros2 launch ros2_lecture bringup.launch.py
   ```
3. **[env]** SLAM : `ros2 launch turtlebot3_cartographer cartographer.launch.py`
4. **[env]** RViz : `rviz2`
   - Fixed Frame = `map`, display **Map** sur `/map`, **LaserScan** sur `/scan`.
5. **[env]** Téléop : `ros2 run turtlebot3_teleop teleop_keyboard`
   - Conduire **lentement** (A W S X D) pour couvrir toute la zone.
   - **Noter le point de départ du robot.**
6. **[env]** Sauvegarder la carte (Cartographer toujours actif) :
   ```bash
   ros2 run nav2_map_server map_saver_cli -f ~/ros2_lecture_ws/maps/competition_map
   ```
7. `Ctrl+C` sur Cartographer, téléop et bringup.

---

## Phase 2 — Mission

1. **[robot]** Synchro horloge : `turtlebot3_mode` (laisser tourner).
2. **[robot]** Robot :
   ```bash
   ssh -YC turtle@192.168.11.2
   ros2 launch ros2_lecture bringup.launch.py
   ```
   - **Démarrer le robot au point de départ noté en Phase 1.**
3. **[env]** Localisation + navigation (ouvre RViz) :
   ```bash
   ros2 launch turtlebot3_navigation2 navigation2.launch.py \
       map:=$HOME/ros2_lecture_ws/maps/competition_map.yaml
   ```
4. **RViz** :
   - Fixed Frame = `map`.
   - Outil **2D Pose Estimate** : cliquer la position réelle du robot et tirer
     dans sa direction.
   - Ajouter un display **Map** sur `/updated_map`.
5. **[env]** Caméra : `ros2 run competition_pkg fakerobot`
6. **[env]** Carte dynamique : `ros2 run competition_pkg obstacle_mapper`
   - Attendre le log `Reference map received: ...`.
7. **[env]** Machine à états : `ros2 run competition_pkg sm` puis **ENTER**.

---

## Tester la carte dynamique

Poser un objet neuf (absent du SLAM) sur une cellule **libre**, à portée du
LiDAR et assez haut pour croiser le plan de scan. Le terminal `obstacle_mapper`
affiche `New obstacle at world (...)`, et la cellule passe en obstacle sur
`/updated_map` dans RViz.
