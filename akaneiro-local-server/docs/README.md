# Akaneiro Demon Hunters - Local Server

A complete local server implementation for the abandoned Steam game **Akaneiro: Demon Hunters**. Replaces the defunct official servers with a Python-based auth + game server stack backed by SQLite.

## Quick Start

```bash
# Terminal 1 - Auth server (HTTP, port 80)
cd akaneiro-local-server
python auth_server.py

# Terminal 2 - Game server (TCP, port 8080)
cd akaneiro-local-server
python game_server.py

# Then launch Akaneiro from Steam as usual
```

## Prerequisites

### Hosts File Configuration

Add these entries to `C:\Windows\System32\drivers\etc\hosts` (run editor as Administrator):

```
127.0.0.1 mw.angry-red.com
127.0.0.1 spicyworld.spicyhorse.com
```

- `mw.angry-red.com` → Auth server endpoints
- `spicyworld.spicyhorse.com` → Steam authentication endpoints

### Python Environment

Uses the system Python at: `C:/Users/<>>/AppData/Local/Python/bin/python.exe`

No external dependencies required — only uses Python standard library (`socket`, `sqlite3`, `struct`, etc.).

---

## Architecture

```
┌──────────────┐     HTTP      ┌─────────────────┐
│  Game Client │ ─────────────▶│  Auth Server    │
│  (Unity 4.x) │ ◀──────────── │  Port: 80       │
└──────────────┘   HTTPS/HTTP  └─────────────────┘
        │                        │
        │  TCP connect to        │  Returns IP + token
        │  127.0.0.1:8080        │
        ▼                        │
┌─────────────────┐              │
│  Game Server    │◀─────────────┘
│  Port: 8080     │   Login response
│  (TCP)          │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  SQLite DB      │
│  akaneiro_local │
└─────────────────┘
```

### Auth Server (`auth_server.py`)

Handles all HTTP endpoints the client hits during login:

| Endpoint | Purpose |
|----------|---------|
| `/login` | Normal client login (Steam ticket) |
| `/client/steam/user/authorize` | Steam ticket authorization |
| `/client.php?mod=login` | Web client email/password login |
| `/client/steam/dlc/validate` | DLC validation (Early Access Starter Pack) |
| `/client/steam/transaction/init` | Transaction initialization |
| `/client/steam/transaction/complete` | Transaction completion |
| `/client.php?mod=recharge` | Web client payment processing |

### Game Server (`game_server.py`)

TCP server handling 70+ protocol messages with full SQLite persistence:

```
[4 bytes body size][2 bytes msg type][body]
msg type: 0=game logic, 1=heartbeat ping, 2=heartbeat pong
```

---

## Implemented Features

### ✅ Authentication & Accounts
- Steam ticket login (creates/looks up accounts by `steam_id`)
- Web email/password login (creates/looks up accounts by `email`, auto-creates new accounts)
- DLC validation for Early Access Starter Pack
- Concurrent multi-client support (threaded)

### ✅ Character System
- Character creation with class-specific starter items:
  - **Prowess** (style=1): Katana + armor set
  - **Fortitude** (style=2): Club + armor set
  - **Cunning** (style=4): Sickle + armor set
- Name collision detection (returns error code 60 if taken)
- Character selection with full attribute display on hunter screen
- Character deletion (cascades to items, talent, well_data)

### ✅ Inventory & Equipment
- Bag info sent proactively after scene load (client never requests it)
- Equipped items visible in BOTH equipbag (model rebuild) and basebag (inventory)
- Equip validation: items only go to correct slot types
- Correct client slot mapping: helm=0, necklace=1, chest=2, cloak=3, ring=4, weapon=6/7, legs=8
- 3D models load in inventory menu when viewing equipped items

### ✅ Scene Loading & Spawning
- Map-specific spawn positions extracted from XML Scene_Objs:
  - Hub_Village_Tutorial: (51.39, 6.98, 99.23)
  - Hub_Village: (81.35, 2.05, 84.85)
- Tutorial NPC (Bounty Master) and wolf monster spawn on tutorial map entry
- Village NPCs spread across hub world

### ✅ Missions & Social
- Mission acceptance from NPCs with progress tracking
- Mission list retrieval with status display
- Mail system (get, open, delete, send)
- Friend list retrieval
- Daily rewards with claim status

### ✅ Combat & Progression
- Normal attack and fight skill handling
- Movement position updates with server echo
- Item pickup (money and items)
- EXP gain notifications
- Mastery level-up tracking
- Talent point assignment (Prowess/Fortitude/Cunning)

### ✅ Economy & World Systems
- Shop item/consume info retrieval
- Pet purchasing and selection
- Well data management (karma system)
- Area unlocking, threat levels, stash purchasing
- Character gender/name change requests
- Cool-down management

---

## Database Schema

```sql
accounts (id PK, steam_id UNIQUE, email UNIQUE, password, nickname, karma, gold, created_at)
characters (id PK, account_id FK, nickname, style, sex, level, exp, status, is_tutorial, current_map, x, y, z, hp, max_hp, mp, max_mp, power, defense, skill, phy_atk, damage_reduction, critical, hp_recover, mp_recover, move_speed, attack_speed, critical_damage, creation_time)
items (id PK, character_id FK, item_type, item_id, quantity, slot)
missions (id PK, character_id FK, mission_id, status, progress)
mail (id PK, character_id FK, sender, subject, body, read, created_at)
pets (id PK, character_id FK, pet_type, level)
mastery (id PK, character_id FK, mastery_type, level)
talent (id PK, character_id FK, prowess, fortitude, cunning, left_points)
well_data (id PK, character_id FK, speed_level, time_level, lid_level, begin_time)
leaderboard (id PK, character_id FK, score, rank)
shop_items (id PK, item_type, item_id, price, currency)
```

---

## Class Starter Items Reference

| Style | Class | Weapon ID | Armor IDs |
|-------|-------|-----------|-----------|
| 1 | Prowess | 1001 (Katana) | 2001 (Helm), 2002 (Breastplate), 2003 (Breeches) |
| 2 | Fortitude | 1003 (Club) | 2001, 2002, 2003 |
| 4 | Cunning | 1008 (Sickle) | 2001, 2002, 2003 |

---

## Troubleshooting

### "Web Server is insane" Error
Auth server isn't running or hosts file misconfigured. Verify:
1. Auth server running on port 80 (`python auth_server.py`)
2. Both hosts entries present: `mw.angry-red.com` and `spicyworld.spicyhorse.com`

### Character Stuck at "Establishing Connection..."
- Game server not running or not accepting connections on port 8080
- Check game server logs for errors
- Ensure both servers are started before launching the game

### Black Screen After Character Creation
The mission selection screen may appear black if data is missing. This was fixed by ensuring proper bag info and character attributes are sent during login.

### Base Stats Show as 0 on Character Selection (After Returning from Game)
**Known client-side bug.** Clicking "back" from in-game to the character selection screen doesn't refresh base stats (Power, Skill, Defense, HP/MP). 

**Workaround:** Perform a complete logout/login cycle. Stats display correctly on initial login or after re-login.

### Item Icons / 3D Models Not Showing
- Verify prefab IDs are being sent correctly in bag info and equip responses
- Check that `get_prefab_id()` returns valid values (weapons=1, armor based on class style)
- The client requires these to populate `ItemPrefabs.GetItemPrefab()` — null causes crashes

### "Couldn't Connect to Host" (Countly Errors)
Harmless. Countly analytics server is defunct. These errors appear in output_log.txt but don't affect gameplay.

---

## Testing Procedures

### Fresh Start
```bash
# 1. Kill any running Python processes
powershell -Command "Stop-Process -Name python -Force"

# 2. Delete database to reset everything
del akaneiro-local-server\akaneiro_local.db

# 3. Start servers fresh
python auth_server.py
python game_server.py
```

### Web Login Test Flow
1. Launch Akaneiro
2. Enter email: `test@test.com`, password: `password`
3. Should see login success and character selection screen
4. Create a character → should appear with starter items in inventory
5. Select character → enter tutorial → verify NPCs spawn, items visible

### Steam Login Test Flow
1. Launch Akaneiro through Steam
2. Client auto-authenticates via Steam ticket
3. Same flow as above after authentication

---

## File Locations

| Path | Purpose |
|------|---------|
| `auth_server.py` | HTTP auth server (port 80) |
| `game_server.py` | TCP game server (port 8080) |
| `akaneiro_local.db` | SQLite database (auto-created on first run) |
| `docs/FACTS.md` | Technical facts, protocol details, known issues |
| `docs/ERRORS.md` | Detailed client-side bug documentation |

---

## Known Limitations

### Client-Side Bugs (Cannot Fix Server-Side)
- Base stats don't refresh after clicking "back" from in-game
- Character model gender mismatch on selection screen (hardcoded female in PreLoadPlayer.cs)
- Unity WWW class asset bundle loading issues on Windows/Linux (requires client recompilation)

### Server-Side TODOs
- Full combat system (enemy AI, damage calculations, skill effects)
- Dynamic NPC interactions and quest progression logic
- Shop/economy transaction processing with actual item transfers
- Monster spawning with trigger-based activation
- All remaining protocol handlers (~100+ more to implement)

---

## Credits & Acknowledgments

This project reverse-engineers the network protocol of Akaneiro: Demon Hunters (2014, Angry Red / Spicyhorse Games). Protocol analysis was performed using PCAP captures from the original live servers.
