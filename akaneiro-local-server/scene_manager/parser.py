"""Parse scene XML files to extract breakable actors, triggers, and gates."""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple, Any
import os


class BreakableObject:
    """Represents a breakable/interactive object in the scene."""
    
    def __init__(self, content: str, position: Tuple[float, float, float], 
                 scale: Tuple[float, float, float] = (1.0, 1.0, 1.0),
                 rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)):
        self.content = content  # Prefab name (e.g., "CH_Wolf_Insane")
        self.position = position
        self.scale = scale
        self.rotation = rotation
        self.health = 1  # Default health for breakable objects
    
    def __repr__(self):
        return f"BreakableObject(content='{self.content}', pos={self.position})"


class Trigger:
    """Represents a trigger zone in the scene."""
    
    def __init__(self, trigger_id: int, position: Tuple[float, float, float],
                 size: Tuple[float, float, float], trigger_type: str = 'gate_open',
                 target_gate_id: Optional[int] = None):
        self.trigger_id = trigger_id
        self.position = position  # Center of trigger zone
        self.size = size  # Half-extents (x, y, z)
        self.trigger_type = trigger_type  # gate_open, spawn, etc.
        self.target_gate_id = target_gate_id  # Gate to open when triggered
        self.triggered = False  # Whether this trigger has been activated
    
    def contains_point(self, point: Tuple[float, float, float]) -> bool:
        """Check if a point is inside the trigger zone."""
        return (abs(point[0] - self.position[0]) <= self.size[0] and
                abs(point[1] - self.position[1]) <= self.size[1] and
                abs(point[2] - self.position[2]) <= self.size[2])
    
    def __repr__(self):
        return f"Trigger(id={self.trigger_id}, type='{self.trigger_type}', pos={self.position})"


class Gate:
    """Represents a gate/wall that can be opened or closed."""
    
    def __init__(self, gate_id: int, position: Tuple[float, float, float],
                 monster_required: int = 0):
        self.gate_id = gate_id
        self.position = position
        self.monster_required = monster_required  # Number of monsters to kill to open
        self.monsters_killed = 0  # Count of killed monsters
        self.is_open = False  # Whether gate is currently open
    
    def check_and_open(self, monster_type: Optional[int] = None) -> bool:
        """Check if gate should be opened based on monster kills."""
        if self.is_open:
            return False
        
        # If monster_required > 0, check kill count
        if self.monster_required > 0 and self.monsters_killed >= self.monster_required:
            self.is_open = True
            print(f"[GATE] Gate {self.gate_id} opened! (monsters killed: {self.monsters_killed}/{self.monster_required})")
            return True
        
        # If monster_required == 0, gate opens when player enters trigger zone
        if self.monster_required == 0:
            self.is_open = True
            print(f"[GATE] Gate {self.gate_id} opened by trigger!")
            return True
        
        return False
    
    def record_kill(self) -> bool:
        """Record a monster kill and check if gate should open."""
        self.monsters_killed += 1
        return self.check_and_open()
    
    def __repr__(self):
        return f"Gate(id={self.gate_id}, open={self.is_open}, kills={self.monsters_killed})"


class SceneData:
    """Complete scene data loaded from XML."""
    
    def __init__(self, map_name: str):
        self.map_name = map_name
        self.breakable_actors: List[BreakableObject] = []
        self.triggers: Dict[int, Trigger] = {}  # trigger_id -> Trigger
        self.gates: Dict[int, Gate] = {}  # gate_id -> Gate
    
    def add_breakable(self, actor: BreakableObject):
        self.breakable_actors.append(actor)
    
    def add_trigger(self, trigger: Trigger):
        self.triggers[trigger.trigger_id] = trigger
    
    def add_gate(self, gate: Gate):
        self.gates[gate.gate_id] = gate


class SceneParser:
    """Parse scene XML files to extract game data."""
    
    def __init__(self, xml_base_path: str = None):
        self._scenes: Dict[str, SceneData] = {}
        self.xml_base_path = None  # Always initialize first!
        
        if xml_base_path is None:
            # Default path - try multiple locations
            import os
            possible_paths = [
                '../akaneiro-client-compiled/assetbundles/XML/SCENE',  # From akaneiro-local-server/
                'akaneiro-client-compiled/assetbundles/XML/SCENE',      # From workspace root
                '../akaneiro-client/Assets/Resources/Scenes',          # From akaneiro-local-server/
                'akaneiro-client/Assets/Resources/Scenes',             # From workspace root
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    self.xml_base_path = path
                    break
            
            if self.xml_base_path is None:
                print("[WARN] Scene XML path not found, using empty scene data")
    
    def load_scene(self, map_name: str) -> Optional[SceneData]:
        """Load scene data for a specific map."""
        if map_name in self._scenes:
            return self._scenes[map_name]
        
        if not self.xml_base_path:
            return None
        
        xml_path = os.path.join(self.xml_base_path, f'{map_name}.xml')
        
        if not os.path.exists(xml_path):
            print(f"[WARN] Scene XML not found: {xml_path}")
            return None
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            scene_data = SceneData(map_name)
            
            # Parse Breakable_Objs
            breakables_elem = root.find('Breakable_Objs')
            if breakables_elem is not None:
                for obj in breakables_elem.findall('Obj_Name'):
                    content = obj.attrib.get('Content', '')
                    
                    # Try to get position from separate attributes (Pos_X, Pos_Y, Pos_Z)
                    # or combined attribute (Pos_X, Pos_Y, Pos_Z)
                    pos_x = obj.attrib.get('Pos_X')
                    pos_y = obj.attrib.get('Pos_Y')
                    pos_z = obj.attrib.get('Pos_Z')
                    
                    if pos_x is not None and pos_y is not None and pos_z is not None:
                        try:
                            position = (float(pos_x), float(pos_y), float(pos_z))
                        except:
                            position = (0.0, 0.0, 0.0)
                    else:
                        # No position in XML - breakables spawn at prefab positions
                        position = None
                    
                    actor = BreakableObject(content, position or (0.0, 0.0, 0.0))
                    scene_data.add_breakable(actor)
            
            # Parse Triggers
            triggers_elem = root.find('Triggers')
            if triggers_elem is not None:
                for trigger in triggers_elem.findall('Trigger'):
                    try:
                        trigger_id = int(trigger.attrib.get('id', '0'))
                        pos_x = float(trigger.attrib.get('PosX', '0'))
                        pos_y = float(trigger.attrib.get('PosY', '0'))
                        pos_z = float(trigger.attrib.get('PosZ', '0'))
                        size_x = float(trigger.attrib.get('SizeX', '5.0'))
                        size_y = float(trigger.attrib.get('SizeY', '2.0'))
                        size_z = float(trigger.attrib.get('SizeZ', '5.0'))
                        
                        trigger_type = trigger.attrib.get('TriggerType', 'gate_open')
                        target_gate_id = int(trigger.attrib.get('TargetGateID', '0')) if 'TargetGateID' in trigger.attrib else None
                        
                        trigger_obj = Trigger(
                            trigger_id=trigger_id,
                            position=(pos_x, pos_y, pos_z),
                            size=(size_x, size_y, size_z),
                            trigger_type=trigger_type,
                            target_gate_id=target_gate_id
                        )
                        
                        scene_data.add_trigger(trigger_obj)
                    except Exception as e:
                        print(f"[WARN] Error parsing trigger: {e}")
            
            # Parse Gates (if defined separately)
            gates_elem = root.find('Gates')
            if gates_elem is not None:
                for gate in gates_elem.findall('Gate'):
                    try:
                        gate_id = int(gate.attrib.get('id', '0'))
                        pos_x = float(gate.attrib.get('PosX', '0'))
                        pos_y = float(gate.attrib.get('PosY', '0'))
                        pos_z = float(gate.attrib.get('PosZ', '0'))
                        monster_required = int(gate.attrib.get('MonsterRequired', '0'))
                        
                        gate_obj = Gate(
                            gate_id=gate_id,
                            position=(pos_x, pos_y, pos_z),
                            monster_required=monster_required
                        )
                        
                        scene_data.add_gate(gate_obj)
                    except Exception as e:
                        print(f"[WARN] Error parsing gate: {e}")
            
            self._scenes[map_name] = scene_data
            
            print(f"Loaded scene data for '{map_name}': "
                  f"{len(scene_data.breakable_actors)} breakables, "
                  f"{len(scene_data.triggers)} triggers, "
                  f"{len(scene_data.gates)} gates")
            
            return scene_data
        
        except Exception as e:
            print(f"[ERROR] Error loading scene data for {map_name}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_scene(self, map_name: str) -> Optional[SceneData]:
        """Get loaded scene data (loads if not already loaded)."""
        if map_name not in self._scenes:
            return self.load_scene(map_name)
        return self._scenes[map_name]


# Module-level convenience function
_scene_parser = None

def load_scene_data(xml_base_path: str = None) -> SceneParser:
    """Load or return cached scene parser instance."""
    global _scene_parser
    
    if _scene_parser is None:
        _scene_parser = SceneParser(xml_base_path)
    
    return _scene_parser
