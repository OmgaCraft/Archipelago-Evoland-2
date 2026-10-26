# Notes techniques — Evoland 2 (dans Evoland Legendary Edition)

Même `hlboot.dat` qu'Evoland 1 (le patch final doit contenir les deux jeux). Code d'Evoland 2 : classes
à la racine (`Game`, `State`), `logic.*`, `ent.*`, `map.*`, `ui.*`.

## Données (`evo2.pak`)

| Fichier | Contenu |
|---|---|
| `data.cdb` | Base CastleDB (JSON) : `item` (74 objets), `card` (61 cartes), `levelEntry` (93 niveaux), `levelData` (132 : niveau × époque, avec `actives`, `npcs`, `monsters`, `triggers`), `active` (types d'objets : Chest, FalseChest, MagiChest, Sparkling…). |
| `extra/script/<époque>/<Niveau>.js` | Scripts de quête (hscript) : `getItem("X")`, `getCard("x")`, `hasItem`, `useItem`, drapeaux… |
| `extra/lang/*.csv` | Textes. |

Extraction : `extracted/evo2/` (via `tools/pak.py`).

## Coffres

- `levelData[].actives` de type `Chest` : `value` = contenu, `x`, `y`, `id` optionnel. 142 coffres
  (sans les niveaux de test préfixés par `_`).
- Contenu : identifiant en minuscules existant dans la table `card` → carte ; sinon objet (première lettre
  mise en majuscule : `star` → `Star`, `mineral` → `Mineral`, `energy` → `Energy`).
- Ouverture mémorisée par position : `state.getLevel().actives` contient `uid = x + y * level.width`.

## Donner un objet : `logic.Logic.getItem(item, onEnd, silent, card)` (fn@3126)

- `silent` (ref<bool>) vrai → `quickAddCard` / `quickAddItem` directement, puis `onEnd()`.
- sinon → bloque le héros, son, animation « objet obtenu », puis ajout.
- Appelée par : coffres (closure fn@6703), scripts (`ScriptGlobals.a_getItem` fn@3362, `a_getCard` fn@3355),
  `Sparkling.heroAction`, `MissingRail.update`, `SewersGem.update`, touches de debug (`Keys`).
- Inventaire : `state.inventory` = liste de `{kind: String, qty: Int}` ; équipement équipé automatiquement
  s'il est meilleur ; cartes : `state.cards`.

## État (`State`, champ `Game.state`)

`currentLevel: String`, `currentTime: null<Int>` (0 passé, 1 présent, 2 futur, 3 antique ?), `gold`,
`inventory`, `cards`, `globalFlags: StringMap` (sauvegardé → idéal pour les données Archipelago),
`levelData: StringMap`, `ach` (succès).

## Récompenses de scripts (≈ 48 appels `getItem`/`getCard`)

Objets clés notables : `TimeStone` (futur/Pyramid), `WingBroken` (futur/Pyramid), `WingTravel`
(futur/WorldMap), `NESPad` (futur/WeaponHearth), `MagiKey1` (present/PirateHideout), `MagiKey2`
(past/VikingVillage), `MagiKey3` (present/SylvesForest), `MagiKey4`/`MagiKey5` (coffres DemoniaEnd / Glitch),
`Boat` (present/MagiIsland), `Bombs` (present/Mine), `SuperBombs` (coffre Mine), `SewersKey`
(past/Capital + coffres), `VillageKey` (present/FirstVillage), `ChildKey` ×4 (present/Capital*),
`MagusKey` (past/DemoniaEnd).

## Patch (`patcher/evoland2_patch.py`) et pièges du JIT

- Accroches : début de `Logic.getItem` (fn@3126), closure d'ouverture des coffres (clé du coffre juste
  avant chaque `getItem`), `Game.update` (réception des items), `ScriptGlobals.setCredits` (objectif).
- Protocole de fichiers dans `archipelago2/` : voir l'en-tête du script.
- Toujours installer avec `patcher/build_all.py` (Evoland 1 + 2, voir `docs/COORDINATION.md`).
- **JIT de cette version de HashLink** : un bytecode invalide donne « JIT ERROR 0 (jit.c line 524) »
  au lancement (le jeu se ferme sans fenêtre).
  - Confirmé par dichotomie : une globale de type `bool` est refusée → utiliser un `i32` 0/1.
  - Précaution (non confirmée) : ne pas faire `ToDyn` sur un `null<i32>`, le convertir d'abord en
    `i32` avec `SafeCast`, comme le fait le code du jeu.
- Test rapide sans Steam : lancer `Evoland.exe` en capturant la sortie ; « Steam failed to activate »
  = le JIT a accepté le bytecode ; « JIT ERROR » = refusé. `build(bc, parts=...)` permet de n'appliquer
  qu'une partie du patch pour trouver la fonction fautive.

## Logique : faits vérifiés dans les scripts (v0.1.0)

- Actes : `act2` posé à la fin du Labo (present/Labo.js), `act3` quand les 5 fragments sont posés
  dans l'Œil du cyclone (futur/WeaponHearth.js, `activeKey`, les fragments sont consommés).
- Acte 1 : un éboulement (present/WorldMap.js, `landslide`) bloque Nibiru et Spelbuk (présent) ; levé à l'acte 2.
- Acte 3 : coffre-étoile `secondChest` de la vieille maison (present/FirstVillageInterior.js), chemin
  de Nibiru (futur, `Line001`), Gardien ailé (futur/WorldMap.js) → Module temporel.
- Égouts (passé) : la fuite demande 2 Clés des égouts ; les 4 gemmes et la carte Forgeron sont dans la
  partie « maison aux poules », entrée depuis Genova ; la 3e clé (Mudwell) ouvre la sortie de Genova.
- Colisée (Genova présent) : fermé tant que `WorldMap.pirateDestroy` n'est pas posé (repaire des pirates).
- Coffre de Dalkin : retiré tant que `DemoniaEnd.done` n'est pas posé (campagne de Demonia).
- Bosquet sacré des Sylphes : entrée fermée sans `SylveTear` (present/Sylves.js).
- Windy Valley (futur) : le garde (`locker`) bloque le Magilith antique (→ ère des Magi, Anomalie)
  jusqu'à ce que Sid ait reçu le Prototype X-01 (present/Windvalley.js, acte 2) ; le prototype ne se
  prend qu'après avoir parlé à Sid (`Windvalley.story`).
- L'objet `Gravity` n'est lu nulle part dans le code (pas une capacité).
- Référence externe : tableur communautaire « Evoland 2 Items, Flags and Logic »
  (https://docs.google.com/spreadsheets/d/1z8olt25UQ6uwJfjUcqqZWrySkZK8X4EECW4i_wOoP7k).
- Piège (v0.1.3) : le Magilith de l'Île Maudite du passé (past/MagiIsland.js, `act_mag`, sans
  condition) mène au présent derrière une porte que seule Velvet affaiblit, et le Magilith du présent
  exige `NESPad`. Avec le Bateau reçu tôt, on y arrive avant que Velvet rejoigne l'équipe (cinématique
  `futurToPresent` de futur/MagiIsland.js) : blocage. Le patch refuse ce `goto` sans Velvet ni NESPad
  (`ap2.trapGate`). Les autres Magiliths (Demonia, Caverne glacée, Windy Valley/ère des Magi) forment
  des boucles sans condition : pas de piège.
- Sauvegardes : `tools/evo2_save_fix.py` (sérialisation Haxe + CRC hxd.Save). Au chargement, une ancre
  `startAnchor` l'emporte sur heroX/heroY (Game.hx:608) : `--move niveau:époque:ancre` sort d'un blocage.
