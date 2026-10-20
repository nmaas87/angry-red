"""Parse Monster.xml to extract enemy definitions."""

import xml.etree.ElementTree as ET
from typing import Dict, Optional


class MonsterDefinition:
    """Represents a monster/enemy definition from XML."""
    
    def __init__(self, monster_id: int):
        self.monster_id = monster_id
        self.name = ""
        self.max_health = 0
        self.xp = 0
        self.vision_radius = 0.0
        self.alert_distance = 0.0
        self.wander_speed = 0.0
        self.wander_time = 0.0
        self.run_speed = 0.0
        self.turn_speed = 0.0
        self.attack_sight_chance = 0
        self.attack_on_damage_chance = 0
        self.initial_state = "Idle"
        self.can_stun = False
        self.can_poison = False
        self.can_slow = False
        self.can_knock_back = False
        self.can_fear = False
    
    def __repr__(self):
        return f"Monster(id={self.monster_id}, name='{self.name}', hp={self.max_health})"


class MonsterParser:
    """Parse and cache monster data from Monster.xml."""
    
    def __init__(self, xml_path: str = None):
        self._monsters: Dict[int, MonsterDefinition] = {}
        self._xml_path = xml_path
        
        if xml_path:
            self.load(xml_path)
    
    def load(self, xml_path: str) -> 'MonsterParser':
        """Parse Monster.xml and populate self._monsters."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            for monster_elem in root.findall('Monster'):
                monster = self._parse_monster(monster_elem)
                if monster:
                    self._monsters[monster.monster_id] = monster
            
            print(f"Loaded {len(self._monsters)} monsters from {xml_path}")
        
        except Exception as e:
            print(f"Error loading monsters from {xml_path}: {e}")
            import traceback
            traceback.print_exc()
            self._monsters = {}
        
        return self
    
    def _parse_monster(self, elem) -> Optional[MonsterDefinition]:
        """Parse a single Monster XML element."""
        try:
            monster_id = int(elem.attrib.get('ID', '0'))
            if monster_id == 0:
                return None
            
            monster = MonsterDefinition(monster_id)
            
            # Parse basic fields with defaults
            def get_float(attr, default=0.0):
                val = elem.attrib.get(attr, str(default))
                try:
                    return float(val)
                except ValueError:
                    return default
            
            def get_int(attr, default=0):
                val = elem.attrib.get(attr, str(default))
                try:
                    return int(val)
                except ValueError:
                    return default
            
            def get_bool(attr, default=False):
                val = elem.attrib.get(attr, str(default)).lower()
                return val in ('true', '1', 'yes')
            
            monster.name = elem.attrib.get('Name', '')
            monster.max_health = get_int('MaxHealth', 100)
            monster.xp = get_int('XP', 10)
            monster.vision_radius = get_float('VisionRadius', 5.0)
            monster.alert_distance = get_float('AlertDistance', 3.0)
            monster.wander_speed = get_float('WanderSpeed', 1.0)
            monster.wander_time = get_float('WanderTime', 5.0)
            monster.run_speed = get_float('RunSpeed', 4.0)
            monster.turn_speed = get_float('TurnSpeed', 2.0)
            monster.attack_sight_chance = get_int('AttackSightChance', 100)
            monster.attack_on_damage_chance = get_int('AttackOnDamageChance', 100)
            monster.initial_state = elem.attrib.get('InitialState', 'Idle')
            monster.can_stun = get_bool('CanStun', False)
            monster.can_poison = get_bool('CanPoison', False)
            monster.can_slow = get_bool('CanSlow', False)
            monster.can_knock_back = get_bool('CanKnockBack', False)
            monster.can_fear = get_bool('CanFear', False)
            
            return monster
        
        except Exception as e:
            print(f"Error parsing monster: {e}")
            return None
    
    def get_monster(self, monster_id: int) -> Optional[MonsterDefinition]:
        """Get a specific monster by ID."""
        return self._monsters.get(monster_id)
    
    def get_all_monsters(self) -> Dict[int, MonsterDefinition]:
        """Get all loaded monsters."""
        return self._monsters
    
    @property
    def monster_ids(self) -> list:
        """Get list of all monster IDs."""
        return list(self._monsters.keys())


# Module-level convenience function
_monster_parser = None

def load_monsters_xml(xml_path: str = None) -> MonsterParser:
    """Load or return cached monster parser instance."""
    global _monster_parser
    
    if _monster_parser is None:
        if xml_path is None:
            # Default path - look for Monster.xml directly in this directory
            import os
            xml_path = os.path.join(os.path.dirname(__file__), 'Monster.xml')
        
        _monster_parser = MonsterParser(xml_path)
    
    return _monster_parser
