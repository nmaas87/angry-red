"""Spawn manager for mission-specific monsters."""

import random
from typing import Dict, List, Optional, Tuple
from .parser import MonsterParser, load_monsters_xml


class SpawnPoint:
    """Represents a location where a monster can spawn."""
    
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z
    
    def get_position(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


class SpawnedMonster:
    """Represents a spawned monster instance."""
    
    def __init__(self, monster_id: int, spawn_point: SpawnPoint, uuid: int):
        self.monster_id = monster_id
        self.spawn_point = spawn_point
        self.uuid = uuid  # Unique identifier for this instance
        self.is_alive = True
        self.health = 100  # Will be set from monster definition
    
    def __repr__(self):
        return f"SpawnedMonster(id={self.monster_id}, uuid={self.uuid})"


class SpawnManager:
    """Manages spawning and tracking of mission monsters."""
    
    def __init__(self, parser: MonsterParser = None):
        self._parser = parser or load_monsters_xml()
        
        # Map: (character_id, map_name) -> {monster_id: [SpawnedMonster]}
        self._active_spawns: Dict[int, Dict[str, Dict[int, List[SpawnedMonster]]]] = {}
        
        # Track kills per character/mission/task
        # Format: {character_id: {mission_id: {task_id: {track_index: current_count}}}}
        self._kill_tracker: Dict[int, Dict[int, Dict[int, Dict[int, int]]]] = {}
    
    def get_monsters_for_mission(self, mission_id: int) -> List[Tuple[int, int]]:
        """Get list of (monster_id, count) needed for a mission.
        
        Returns unique monster IDs with total counts from all tracks.
        """
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from mission_parser import parse_missions_xml
        
        parser = parse_missions_xml()
        mission = parser.get_mission(mission_id)
        
        if not mission:
            return []
        
        # Count monsters needed per ID
        monster_counts: Dict[int, int] = {}
        
        for track in mission.all_tracks:
            if track.track_type == 2:  # Kill objective
                monster_id = track.object_id
                count = track.count
                monster_counts[monster_id] = monster_counts.get(monster_id, 0) + count
        
        return [(mid, cnt) for mid, cnt in monster_counts.items()]
    
    def spawn_monsters_for_mission(self, character_id: int, map_name: str, mission_id: int):
        """Spawn monsters needed for a specific mission on a map."""
        if character_id not in self._active_spawns:
            self._active_spawns[character_id] = {}
        
        if map_name not in self._active_spawns[character_id]:
            self._active_spawns[character_id][map_name] = {}
        
        # Get monsters needed for this mission
        monster_specs = self.get_monsters_for_mission(mission_id)
        
        if not monster_specs:
            return []
        
        spawned = []
        for monster_id, count in monster_specs:
            # Log missing monsters but continue spawning
            if not self._parser.get_monster(monster_id):
                print(f"[WARN] Monster ID {monster_id} not found in Monster.xml - using default stats")
            
            # Check if we already have these monsters spawned
            existing = self._active_spawns[character_id][map_name].get(monster_id, [])
            alive_count = sum(1 for m in existing if m.is_alive)
            
            if alive_count < count:
                # Spawn missing monsters
                for i in range(count - alive_count):
                    spawn_point = self._generate_spawn_point(map_name, monster_id)
                    uuid = self._generate_uuid()
                    
                    spawned_monster = SpawnedMonster(monster_id, spawn_point, uuid)
                    spawned.append(spawned_monster)
        
        if spawned:
            print(f"Spawned {len(spawned)} monsters for char {character_id}, map {map_name}, mission {mission_id}")
            
            # Store spawns
            for monster in spawned:
                if monster.monster_id not in self._active_spawns[character_id][map_name]:
                    self._active_spawns[character_id][map_name][monster.monster_id] = []
                self._active_spawns[character_id][map_name][monster.monster_id].append(monster)
            
            # Initialize kill tracker for this mission/task
            if character_id not in self._kill_tracker:
                self._kill_tracker[character_id] = {}
            if mission_id not in self._kill_tracker[character_id]:
                self._kill_tracker[character_id][mission_id] = {}
        
        return spawned
    
    def record_kill(self, character_id: int, monster_uuid: int) -> List[Tuple[int, int, int]]:
        """Record a monster kill and check for task completion.
        
        Returns list of (mission_id, branch_id, task_id) that completed.
        """
        completed_tasks = []
        
        # Find which spawned monster was killed
        monster_to_remove = None
        for char_spawns in self._active_spawns.get(character_id, {}).values():
            for monsters_by_id in char_spawns.values():
                for monster in monsters_by_id:
                    if monster.uuid == monster_uuid and monster.is_alive:
                        monster.is_alive = False
                        monster_to_remove = monster
                        break
        
        if not monster_to_remove:
            return []
        
        # Find which missions this monster ID is tracking
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from mission_parser import parse_missions_xml
        
        parser = parse_missions_xml()
        mission_id = None
        
        # Check kill tracker for active missions
        if character_id in self._kill_tracker:
            for mid, tasks in self._kill_tracker[character_id].items():
                mission = parser.get_mission(mid)
                if not mission:
                    continue
                
                # Check if this monster ID is tracked in any task
                branch_idx = 0
                for branch in mission.branches:
                    task_idx = 0
                    for task in branch.tasks:
                        track_idx = 0
                        for track in task.tracks:
                            if track.track_type == 2 and track.object_id == monster_to_remove.monster_id:
                                # This is the tracked objective!
                                current_count = tasks.get(task.task_id, {}).get(track_idx, 0)
                                tasks[task.task_id][track_idx] = current_count + 1
                                
                                # Check if task completed
                                if current_count + 1 >= track.count:
                                    completed_tasks.append((mid, branch.branch_id, task.task_id))
                                    
                                track_idx += 1
                        
                        task_idx += 1
                    
                    branch_idx += 1
        
        return completed_tasks
    
    def _generate_spawn_point(self, map_name: str, monster_id: int) -> SpawnPoint:
        """Generate a spawn point for a monster.
        
        In production, this would read from scene data or use predefined spawn points.
        For now, generate random positions near the center of the map.
        """
        # Simple random spawn near origin (will be improved with real spawn data)
        x = random.uniform(-10.0, 10.0)
        y = random.uniform(0.0, 5.0)  # Height variation
        z = random.uniform(-10.0, 10.0)
        
        return SpawnPoint(x, y, z)
    
    def _generate_uuid(self) -> int:
        """Generate a unique UUID for a spawned monster."""
        import hashlib
        import time
        
        # Simple UUID generation based on timestamp and random
        uuid_str = f"{time.time()}{random.random()}"
        return int(hashlib.md5(uuid_str.encode()).hexdigest()[:8], 16)
    
    def get_alive_monsters(self, character_id: int, map_name: str) -> List[SpawnedMonster]:
        """Get all alive monsters for a character on a map."""
        if character_id not in self._active_spawns:
            return []
        
        if map_name not in self._active_spawns[character_id]:
            return []
        
        monsters = []
        for monsters_by_id in self._active_spawns[character_id][map_name].values():
            monsters.extend([m for m in monsters_by_id if m.is_alive])
        
        return monsters
    
    def cleanup_character(self, character_id: int):
        """Clean up all spawns and trackers for a character."""
        if character_id in self._active_spawns:
            del self._active_spawns[character_id]
        if character_id in self._kill_tracker:
            del self._kill_tracker[character_id]
