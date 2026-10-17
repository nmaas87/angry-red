# Akaneiro Demon Hunters - Local Server Project Facts

## Project Overview
- **Game:** Akaneiro Demon Hunters (Steam, abandoned)
- **Goal:** Build a complete local server to replace the defunct official servers
- **Client:** Unity 4.1.5f1 game client with Steam and Web login support
- **Status:** Core systems working end-to-end (login, character creation, tutorial, inventory, equipment, scene loading)

---

## Environment
- **Python path**: `C:/Users/<>/AppData/Local/Python/bin/python.exe`
- **Working directory**: `C:\Users\<>\.lmstudio\apps\bionic\projects\<>\workspace`
- **Game install**: `C:\Program Files (x86)\Steam\steamapps\common\Akaneiro Demon Hunters`

## Process Management (Windows)
- **Kill Python processes**: Use PowerShell: `powershell -Command "Stop-Process -Name python -Force"`
  - Bash `kill` doesn't work reliably on Windows
  - `taskkill /F /PID <pid>` has slash interpretation issues in bash
- **DB location**: `akaneiro-local-server/akaneiro_local.db` (uses script directory, not CWD)
- **Clean restart**: Kill Python processes → delete DB → start servers fresh

---

## Architecture

### Two-Server Setup
1. **Auth Server** (`auth_server.py`) - HTTP on port 80
   - Handles `/login` (normal client login)
   - Handles `/client/steam/user/authorize` (Steam ticket auth)
   - Handles `/client.php?mod=login` (Web client email/password)
   - Handles `/client/steam/dlc/validate` (DLC validation)

2. **Game Server** (`game_server.py`) - TCP on port 8080
   - SQLite database for all game data
   - ~70+ protocol handlers implemented and tested
   - Manages characters, inventory, missions, combat, etc.

---

## Account System

### Steam Login
- Uses Steam session tickets for authentication
- Creates/looks up account by `steam_id` in database
- Returns token and game server address to client

### Web Login (Email/Password)
- Uses email/password for authentication  
- Creates/looks up account by `email` in database
- Response format: `uid:"1002",token:"local_web_token_abc123",key:"local_web_key_xyz789",ip:"127.0.0.1:8080",gameCode:"local_web_gamecode_abc123",message:"success"`
- New email/password pairs create new accounts automatically

### Database Schema
```sql
accounts (id, steam_id, email, password, nickname, karma, gold, created_at)
characters (id, account_id, nickname, style, sex, level, exp, status, is_tutorial, current_map, x, y, z, hp, max_hp, mp, max_mp, power, defense, skill, ...)
items (id, character_id, item_type, item_id, quantity, slot)
talent (character_id, prowess, fortitude, cunning, left_points)
well_data (character_id, speed_level, time_level, lid_level, begin_time)
missions (id, character_id, mission_id, status, progress)
mail (id, character_id, sender, subject, body, read, created_at)
pets (id, character_id, pet_type, level)
mastery (id, character_id, mastery_type, level)
leaderboard (id, character_id, score, rank)
shop_items (id, item_type, item_id, price, currency)
```

### Character Classes & Starter Items
Three disciplines available during character creation:
| Style | Class | Color | Starter Weapon | Armor Set |
|-------|-------|-------|----------------|-----------|
| 1 | **Prowess** | Red | Katana (1001) | Helm(2001), Breastplate(2002), Breeches(2003) |
| 2 | **Fortitude** | Green/White | Club (1003) | Helm(2001), Breastplate(2002), Breeches(2003) |
| 4 | **Cunning** | Blue | Sickle (1008) | Helm(2001), Breastplate(2002), Breeches(2003) |

All classes receive the same armor set - only weapons differ by discipline.

### Equipment Slots
**Database slots** (used when storing items in DB):
| Slot # | Item Type | Example ID |
|--------|-----------|------------|
| 0 | Weapon (main hand) | 1001 (Katana) |
| 1 | Helm (head) | 2001 |
| 2 | Necklace | 3002 |
| 3 | Breastplate (chest) | 2002 |
| 4 | Cloak (back) | 2010 |
| 5 | Ring | 3001 |
| 6 | Breeches (legs) | 2003 |

**Client part indices** (sent by client in EquipItem packets - based on actual observed behavior):
| Part # | Item Type(s) Allowed |
|--------|----------------------|
| 0 | Helm |
| 1 | Necklace |
| 2 | Breastplate/Chest |
| 3 | Cloak |
| 4 | Ring |
| 6 | Weapon (1h/2h) |
| 7 | Two-handed weapon |
| 8 | Breeches/Legs |

**Note:** The client's slot mapping differs from the EEquipmentType enum. Slot 3 = cloak, Slot 8 = legs/breeches. This was a major source of bugs - the original code had them swapped.

### Prefab IDs (Critical for Item Display)
**Source:** `akaneiro-client-compiled/Akaneiro_Data/resources.assets` and CSV localization files

The client requires valid prefab IDs to display items on character models and in inventory. Without them, `ItemPrefabs.GetItemPrefab()` returns null causing NullReferenceException crashes.

**Current Implementation Pattern:**
```python
# Weapons (1000-1999): prefabID = 1 (WPN01 for levels 1-6)
# Armor (2000-2999): prefabID based on class style from CSV:
#   - Prowess (style=1): 401 (SAM01 - Heavy)
#   - Fortitude (style=2,3): 301 (SLD01 - Medium)  
#   - Cunning (style=4): 101 (MNK01 - Light)

def get_prefab_id(item_id, style=1):
    if item_id >= 1000 and item_id < 2000:
        return 1  # WPN01 for levels 1-6
    elif item_id >= 2000 and item_id < 3000:
        base = ARMOR_CLASS_BASE.get(style, 401)
        return base
    return 1
```

**Important:** The old `item_id + 10000` pattern was incorrect. The correct prefab IDs come from the CSV localization files (`WeaponAttribute.prefab.EN.txt`, `ArmorAttribute.Prefab.EN.txt`) and resources.assets analysis.

---

## Protocol Messages Implemented

### Core Flow
- `UserLogin` / `On_UserLoginOK` - Account authentication with SAccountInfo, character list (with equipinfo + attrVec)
- `UserCreateCharacter` / `On_UserCreateCharacterOK` - Character creation with class-specific starter items and correct prefab IDs
- `UserSelectCharacter` / `On_UserSelectCharacterOK` + `SendSkillInfo` - Character selection with skills and base stats
- `EnterScene` / `On_EnterSceneOk` - Scene entry
- `MapLoadOK` → Sends: `CharacterStartInfo` + `UpdateMoneyInfo` (karma/FK) + `AddExpNTF` (XP) + `SendBagInfo` + NPC/monster spawns
- `RequestBagInfo` / `SendBagInfo` - Inventory sync with equipped items from DB
- `TutorialEnterReq` / `On_TutorialEnterAck(charID, returnCode)` - Tutorial flow

### Combat & Items
- `UseNormalAttack` / `UseNormalAttackResult`, `UseFightSkill` / `UseFightSkillResult`
- `EquipItem`, `UnequipItem`, `BuyItem`, `DelItem`, `SplitItem`, `SwapItem`
- `PickupMoneyReq` / `PickupMoneyResult`, `EnemyRewardReq`
- `UpdateMoveRequest` / `UpdateMoveResult` - Player movement with position echo

### Missions & Social
- `AcceptMission` / `AcceptMissionOk`, `MissionListReq` / `MissionListAck`
- `GetPlayerMail`, `SendMail`, `DeleteMail`
- `GetFriendList` / `GetFriendListResult`

### Other Systems
- `StudyAbility`, `ChoosePet`, `UpgradeWell`, `BuyCharSlotRequest`
- `ChangeNameReq`, `ChangeGenderReq`
- `ConversationNpcCheckReq`, `DecreaseCoolDown`, `Exploretaskcomplete_req`
- `RoleMasteryListReq` / `RoleMasteryListAck`, `HasAssignedTalentPointReq` / `HasAssignedTalentPointAck`

---

## Key Implementation Details

### Bag Info Handling
- **Proactive sending:** Client never sends `RequestBagInfo`. Server proactively sends bag info after `MapLoadOK`.
- **Equipped items stay in inventory:** When equipping, items are NOT removed from inventory. They appear in BOTH `equipbag` (bagID=0) for model rebuild AND `basebag` (bagID=1) for inventory display.
- **After equip action:** Server sends full bag info update after each equip/unequip to trigger client's `InitPlayerModelEquips()` which rebuilds the character 3D model.

### Character Spawn Positions
Extracted from XML Scene_Objs in `akaneiro-client-compiled/assetbundles/XML/SCENE/`:
| Map | Position (x, y, z) |
|-----|-------------------|
| Hub_Village | (81.35, 2.05, 84.85) |
| Hub_Village_Tutorial | (51.39, 6.98, 99.23) |

### Packet Format
```
[4 bytes body size][2 bytes message type][body]
Message types: 0=game logic, 1=heartbeat ping, 2=heartbeat pong
Game logic packets start with 4-byte method ID
Strings use 4-byte little-endian length prefix (WriteInt(arr.Length))
```

### String Serialization
- All strings in game protocol use **4-byte** little-endian length prefix followed by UTF-8 bytes
- Verified against PCAP hex dumps for account ID, password, nickname, createTime, IP addresses
- `write_string()` method: `WriteInt(len(encoded_bytes))` then raw bytes

---

## Known Issues (Client-Side)

### 1. Base Stats Not Refreshed After Returning from Gameplay
**Symptom:** When clicking "back" from in-game to return to the character selection screen, base stats (Power, Skill, Defense, HP/MaxHP, MP/MaxMP) show as 0 for all characters. Clicking on individual characters does not refresh them either.

**Root Cause:** 
- `ClearCharaList()` clears ALL label values including base stats
- `SetActiveCharaBtn()` repopulates character display (name, level, icon) but does NOT call `SelectBaseManager.UpdateCharacterAttrInfo()` for any character
- The 5 base stats are only updated by `UpdateCharacterAttrInfo()` which is called in `SelectChara()`, but this isn't triggered when returning from gameplay

**Affected Labels:** MaxHP (CurHP), MaxMP (CurMP), Power, Defense, Skill

**Workaround:** Perform a complete logout/login cycle instead of clicking "back" from in-game. Base stats will show correctly on initial login or after re-login.

**Client Code Locations:**
- `SelectCharaStats.SetStats()` - only updates name/level/icon, not base stats
- `SelectBaseManager.UpdateCharacterAttrInfo()` - updates base stats but isn't called when returning from gameplay
- `OptionCtrl.BackToSelectBtnDelegate()` - calls `SavePlayerInfoTOList()` which modifies CharacterList during logout

### 2. Countly Analytics Unreachable
**Symptom:** Repeated "couldn't connect to host" errors for Countly analytics server.

**Status:** Expected - this is a defunct game with no active analytics server. Harmless.

---

## Recent Fixes (2026-10-17)

### Auth Server (`auth_server.py`):
- ✅ Fixed DLC validate response format: now returns `{"success": {"msg": "..."}}` instead of `{"success": true}`
- ✅ Fixed Steam refresh response: added proper `{"success": {"token": "..."}}` wrapper
- ✅ Added `/client/steam/transaction/init` endpoint
- ✅ Added `/client/steam/transaction/complete` endpoint
- ✅ Added `/client.php?mod=recharge` endpoint for web client payments

### Game Server (`game_server.py`):
- ✅ Added equip validation: items can only be equipped to their correct slot type via `CLIENT_PART_TO_ITEM_TYPES`
- ✅ Fixed "WEB Server is insane" error when clicking PLAY on character selection
- ✅ **CRITICAL FIX**: Equipment slot mapping corrected - cloak=slot 3, legs=slot 8 (was swapped)
- ✅ Simplified EQUIPMENT_SLOTS to store client indices directly (1:1 mapping)
- ✅ Bag info sent proactively after MapLoadOK (client never requests it)
- ✅ NotifyItemUpdate response added after equip actions so client knows items changed
- ✅ Character model updates immediately when equipping items via bag info rebuild trigger

---

## Testing Notes
- Hosts file entries needed: `127.0.0.1 mw.angry-red.com` and `127.0.0.1 spicyworld.spicyhorse.com`
- "Webserver is insane" error = HTTP endpoint not handled by auth server

### Fresh Start Procedure
1. Delete `akaneiro_local.db` to reset database
2. Restart both auth_server.py and game_server.py
3. Test Web login with email/password (e.g., test@test.com / password)

### Common Test Flow
1. Login → Character selection screen
2. Create character → Tutorial prompt appears  
3. Accept tutorial → Enter Hub_Village_Tutorial map
4. Verify: NPCs spawn, monsters appear, items in bag, karma/XP display correctly
5. Equip items → 3D models load in inventory menu and on character model

---

## File Locations

| Path | Purpose |
|------|---------|
| `akaneiro-local-server/auth_server.py` | HTTP auth server (port 80) |
| `akaneiro-local-server/game_server.py` | TCP game server (port 8080) |
| `akaneiro-local-server/akaneiro_local.db` | SQLite database (auto-created on first run) |
| `akaneiro-client/Assets/Scripts/CS/Protocol/` | Protocol definitions, method IDs, serialization |
| `akaneiro-client/Assets/Resources/Localization/EN/` | CSV localization files with item/prefab mappings |
| `akaneiro-client-compiled/Akaneiro_Data/resources.assets` | Binary asset database with prefab references |
| `C:\Program Files (x86)\Steam\steamapps\common\Akaneiro Demon Hunters\` | Game client installation |

---

## Next Steps / TODO

- [ ] Implement remaining protocol handlers (~100+ more)
- [ ] Add full combat system (enemy AI, damage, skills)
- [ ] Implement NPC interactions and quest/mission progression
- [ ] Add shop/crafting/economy systems
- [ ] Fix client-side model gender bug (requires PreLoadPlayer.cs modification)
- [ ] Add proper spawn positions for all maps beyond Hub_Village and Hub_Village_Tutorial
- [ ] Implement monster spawning and behavior with dynamic triggers

<EOF>
