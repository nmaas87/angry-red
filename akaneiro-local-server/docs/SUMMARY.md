# Akaneiro Local Server - Session Summary

## What We Built
- **Auth Server** (port 80): Handles Steam tickets, web login (email/password), DLC validation
- **Game Server** (port 8080): ~70+ protocol handlers with SQLite backend
- **Database**: accounts, characters, items, missions, mail, pets, mastery, talent, well_data

## Working Features
1. ✅ Steam & Web login (email: test@test.com / password: password)
2. ✅ Character creation with starting items (weapon + armor in DB)
3. ✅ Tutorial flow (prompt → accept → enter Hub_Village_Tutorial)
4. ✅ NPC/monster spawning on scene load
5. ✅ Inventory sync via SEND_BAG_INFO (equipped items from DB)
6. ✅ Karma/FK display via UPDATE_MONEY_INFO
7. ✅ XP display via ADD_EXP_NTF
8. ✅ Character deletion

## Known Client Bugs (Need Fix)
- Player model hardcoded to female in PreLoadPlayer.cs line 37
- Inventory/Summon views use hardcoded sex boolean
- Ally NPCs all hardcoded to female

## Key Protocol Flow
```
Login → UserCreateCharacter → TutorialEnterReq → EnterScene(Hub_Village_Tutorial)
→ MapLoadOK sends: CharacterStartInfo + UpdateMoneyInfo + AddExpNTF + NPC/monster spawns
```

## Files Modified
- `akaneiro-local-server/auth_server.py` - Web login endpoint added
- `akaneiro-local-server/game_server.py` - All handlers, DB schema, multi-packet responses
- `akaneiro-local-server/docs/FACTS.md` - Project documentation
- `akaneiro-local-server/docs/ERRORS.md` - Client-side bugs documented

## Next Steps
- Implement remaining ~100+ protocol handlers
- Add combat system (enemy AI, damage, skills)
- Fix client-side model gender bug (requires PreLoadPlayer.cs modification)
