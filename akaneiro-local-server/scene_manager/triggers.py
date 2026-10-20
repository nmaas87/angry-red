"""Trigger manager for activating gates, spawning monsters, etc."""

from typing import Dict, List, Optional, Tuple
from .parser import Trigger, SceneData


class TriggerManager:
    """Manages trigger zones and their activation states."""
    
    def __init__(self):
        # Map: (character_id, map_name) -> {trigger_id: Trigger}
        self._triggers: Dict[int, Dict[str, Dict[int, Trigger]]] = {}
    
    def get_triggers_for_character(self, character_id: int, map_name: str) -> Dict[int, Trigger]:
        """Get all triggers for a character on a specific map."""
        if character_id not in self._triggers:
            self._triggers[character_id] = {}
        
        if map_name not in self._triggers[character_id]:
            self._triggers[character_id][map_name] = {}
        
        return self._triggers[character_id][map_name]
    
    def add_trigger(self, character_id: int, map_name: str, trigger: Trigger):
        """Add a trigger to the manager."""
        triggers = self.get_triggers_for_character(character_id, map_name)
        triggers[trigger.trigger_id] = trigger
    
    def load_scene_triggers(self, character_id: int, scene_data: SceneData):
        """Load all triggers from scene data for a character."""
        if not scene_data or not scene_data.triggers:
            return
        
        triggers = self.get_triggers_for_character(character_id, scene_data.map_name)
        
        for trigger in scene_data.triggers.values():
            # Only add if not already present
            if trigger.trigger_id not in triggers:
                triggers[trigger.trigger_id] = Trigger(
                    trigger_id=trigger.trigger_id,
                    position=trigger.position,
                    size=trigger.size,
                    trigger_type=trigger.trigger_type,
                    target_gate_id=trigger.target_gate_id
                )
        
        print(f"[TRIGGER] Loaded {len(triggers)} triggers for char {character_id}, map {scene_data.map_name}")
    
    def check_player_in_trigger(self, character_id: int, map_name: str, 
                                 player_position: Tuple[float, float, float]) -> List[int]:
        """Check if player is inside any untriggered zones.
        
        Returns list of trigger IDs that were just activated.
        """
        triggered = []
        triggers = self.get_triggers_for_character(character_id, map_name)
        
        for trigger in triggers.values():
            # Skip already triggered or inactive triggers
            if trigger.triggered:
                continue
            
            # Check if player is inside this trigger zone
            if trigger.contains_point(player_position):
                trigger.triggered = True
                print(f"[TRIGGER] Trigger {trigger.trigger_id} activated! (type={trigger.trigger_type})")
                
                # Execute trigger action
                if trigger.trigger_type == 'gate_open' and trigger.target_gate_id:
                    triggered.append(trigger.trigger_id)
        
        return triggered
    
    def activate_trigger(self, character_id: int, map_name: str, 
                        trigger_id: int) -> bool:
        """Manually activate a trigger (e.g., from server command)."""
        triggers = self.get_triggers_for_character(character_id, map_name)
        trigger = triggers.get(trigger_id)
        
        if not trigger or trigger.triggered:
            return False
        
        trigger.triggered = True
        print(f"[TRIGGER] Trigger {trigger_id} manually activated!")
        return True
    
    def get_all_trigger_states(self, character_id: int, map_name: str) -> List[dict]:
        """Get state of all triggers for a character on a map."""
        triggers = self.get_triggers_for_character(character_id, map_name)
        
        return [
            {
                'trigger_id': trigger.trigger_id,
                'position': trigger.position,
                'size': trigger.size,
                'trigger_type': trigger.trigger_type,
                'target_gate_id': trigger.target_gate_id,
                'triggered': trigger.triggered
            }
            for trigger in triggers.values()
        ]
    
    def get_trigger_gate_id(self, character_id: int, map_name: str, trigger_id: int) -> Optional[int]:
        """Get the target gate ID for a specific trigger."""
        triggers = self.get_triggers_for_character(character_id, map_name)
        trigger = triggers.get(trigger_id)
        return trigger.target_gate_id if trigger else None
    
    def cleanup_character(self, character_id: int):
        """Clean up all triggers for a character."""
        if character_id in self._triggers:
            del self._triggers[character_id]
