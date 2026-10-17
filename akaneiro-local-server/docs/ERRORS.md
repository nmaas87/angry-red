# Known Errors & Limitations

## Client-Side Issues (Cannot Fix Without Modifying Client)

### 1. Base Stats Not Refreshed After Returning from Gameplay

**Symptom:** When clicking "back" from in-game to return to the character selection screen, base stats (Power, Skill, Defense, HP/MaxHP, MP/MaxMP) show as 0 for all characters. Clicking on individual characters does not refresh them either.

**Root Cause:** 
- `ClearCharaList()` clears ALL label values including base stats
- `SetActiveCharaBtn()` repopulates character display (name, level, icon) but does NOT call `SelectBaseManager.UpdateCharacterAttrInfo()` for any character
- The 5 base stats are only updated by `UpdateCharacterAttrInfo()` which is called in `SelectChara()`, but this isn't triggered when returning from gameplay

**Affected Labels:**
- MaxHP (CurHP display)
- MaxMP (CurMP display)  
- Power
- Defense
- Skill

**Workaround:** Perform a complete logout/login cycle instead of clicking "back" from in-game. Base stats will show correctly on initial login or after re-login.

**Client Code Locations:**
- `SelectCharaStats.SetStats()` - only updates name/level/icon, not base stats
- `SelectBaseManager.UpdateCharacterAttrInfo()` - updates base stats but isn't called when returning from gameplay
- `OptionCtrl.BackToSelectBtnDelegate()` - calls `SavePlayerInfoTOList()` which modifies CharacterList during logout

---

## Server-Side Issues (Fixed)

### 2. Character Model Not Updating on Equip (FIXED)

**Status:** ✅ Fixed

**What was fixed:**
- Added equipbag population in `build_bag_info()` so equipped items are sent to client
- Modified `handle_equip_item()` to send full bag info after equipping, triggering `InitPlayerModelEquips()` on the NGUI path
- Character model now updates immediately when equipping items

### 3. Wrong Equipment Slot Mapping (FIXED)

**Status:** ✅ Fixed

**What was fixed:**
- Corrected EQUIPMENT_SLOT_TO_CLIENT_INDEX mapping for legs/breeches and cloak slots
- Updated CLIENT_PART_TO_ITEM_TYPES to match correct client indices
- Changed EQUIPMENT_SLOTS to store client indices directly (1:1 mapping)
- Client index 3 = cloak, Client index 8 = legs/breeches

### 4. Empty attrVec in Login Response (FIXED)

**Status:** ✅ Fixed

**What was fixed:**
- Added base stats (15 attributes) to each character's attrVec during USER_LOGIN_OK response
- Stats are now displayed on the hunter selection screen for all characters

### 5. Empty equipinfo in Login Response (FIXED)

**Status:** ✅ Fixed

**What was fixed:**
- Added equipped items to each character's equipinfo during USER_LOGIN_OK response
- Character models now show wearing their equipment on the selection screen

---

## Protocol Notes

### Base Stats Attribute Types Used:
- `ATTR_MaxHP` (type 2) - Displayed as HP/Health
- `ATTR_MaxMP` (type 3) - Displayed as MP/Energy  
- `ATTR_Power` (type 4) - Displayed as Power
- `ATTR_Defense` (type 5) - Displayed as Defense
- `ATTR_Skill` (type 6) - Displayed as Skill

### Client Slot Mapping (Correct):
```python
CLIENT_EQUIP_SLOTS = {
    0: 'helm',       # Head
    1: 'necklace',   # Neck
    2: 'chest',      # Chest
    3: 'cloak',      # Cloak/Back (NOT legs!)
    4: 'ring',       # Ring
    6: 'weapon_1h',  # One-handed weapon
    7: 'weapon_2h',   # Two-handed weapon
    8: 'legs',       # Legs/Breeches (NOT cloak!)
}
```
