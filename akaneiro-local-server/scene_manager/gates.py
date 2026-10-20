"""Gate manager for controlling walls, doors, and breakable objects."""

from typing import Dict, List, Optional, Tuple
from .parser import Gate, SceneData


class GateManager:
    """Manages gate states and connections to triggers/monsters."""
    
    def __init__(self):
        # Map: (character_id, map_name) -> {gate_id: Gate}
        self._gates: Dict[int, Dict[str, Dict[int, Gate]]] = {}
    
    def get_gates_for_character(self, character_id: int, map_name: str) -> Dict[int, Gate]:
        """Get all gates for a character on a specific map."""
        if character_id not in self._gates:
            self._gates[character_id] = {}
        
        if map_name not in self._gates[character_id]:
            self._gates[character_id][map_name] = {}
        
        return self._gates[character_id][map_name]
    
    def add_gate(self, character_id: int, map_name: str, gate: Gate):
        """Add a gate to the manager."""
        gates = self.get_gates_for_character(character_id, map_name)
        gates[gate.gate_id] = gate
    
    def load_scene_gates(self, character_id: int, scene_data: SceneData):
        """Load all gates from scene data for a character."""
        if not scene_data or not scene_data.gates:
            return
        
        gates = self.get_gates_for_character(character_id, scene_data.map_name)
        
        for gate in scene_data.gates.values():
            # Only add if not already present
            if gate.gate_id not in gates:
                gates[gate.gate_id] = Gate(
                    gate_id=gate.gate_id,
                    position=gate.position,
                    monster_required=gate.monster_required
                )
        
        print(f"[GATE] Loaded {len(gates)} gates for char {character_id}, map {scene_data.map_name}")
    
    def record_monster_kill(self, character_id: int, map_name: str) -> List[int]:
        """Record a monster kill and check if any gates should open.
        
        Returns list of gate IDs that opened.
        """
        opened_gates = []
        gates = self.get_gates_for_character(character_id, map_name)
        
        for gate in gates.values():
            if not gate.is_open:
                # Record kill and check if gate should open
                if gate.record_kill():
                    opened_gates.append(gate.gate_id)
        
        return opened_gates
    
    def open_gate_by_id(self, character_id: int, map_name: str, gate_id: int) -> bool:
        """Force open a specific gate by ID.
        
        Returns True if the gate was opened (or was already open).
        """
        gates = self.get_gates_for_character(character_id, map_name)
        gate = gates.get(gate_id)
        
        if not gate:
            print(f"[GATE] Gate {gate_id} not found for char {character_id}, map {map_name}")
            return False
        
        if gate.is_open:
            return True  # Already open
        
        gate.is_open = True
        print(f"[GATE] Gate {gate_id} opened by trigger!")
        return True
    
    def is_gate_open(self, character_id: int, map_name: str, gate_id: int) -> bool:
        """Check if a specific gate is open."""
        gates = self.get_gates_for_character(character_id, map_name)
        gate = gates.get(gate_id)
        return gate.is_open if gate else False
    
    def get_all_gate_states(self, character_id: int, map_name: str) -> List[dict]:
        """Get state of all gates for a character on a map."""
        gates = self.get_gates_for_character(character_id, map_name)
        
        return [
            {
                'gate_id': gate.gate_id,
                'position': gate.position,
                'is_open': gate.is_open,
                'monsters_killed': gate.monsters_killed,
                'monster_required': gate.monster_required
            }
            for gate in gates.values()
        ]
    
    def cleanup_character(self, character_id: int):
        """Clean up all gates for a character."""
        if character_id in self._gates:
            del self._gates[character_id]
