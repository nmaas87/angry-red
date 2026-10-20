"""Parse Missions.xml to extract mission definitions, objectives, and rewards."""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any


class MissionTrack:
    """Represents a single track objective within a task."""
    
    def __init__(self, track_type: int, object_id: int, count: int, recycle: int):
        self.track_type = track_type  # 1=collect, 2=kill enemy
        self.object_id = object_id
        self.count = count
        self.recycle = recycle  # 0=no reset, 1=resets after completion
    
    def __repr__(self):
        return f"MissionTrack(type={self.track_type}, obj={self.object_id}, count={self.count})"


class MissionTask:
    """Represents a task within a mission branch."""
    
    def __init__(self, task_id: int, trigger_id: str = "", trigger_type: int = 1):
        self.task_id = task_id
        self.trigger_id = trigger_id
        self.trigger_type = trigger_type
        self.tracks: List[MissionTrack] = []
        self.reward_exp = 0
        self.reward_karma = 0
    
    def add_track(self, track: MissionTrack):
        self.tracks.append(track)
    
    def __repr__(self):
        return f"MissionTask(id={self.task_id}, tracks={len(self.tracks)})"


class MissionBranch:
    """Represents a branch within a mission."""
    
    def __init__(self, branch_id: int, is_must_complete: bool = True):
        self.branch_id = branch_id
        self.is_must_complete = is_must_complete
        self.tasks: List[MissionTask] = []
        self.reward_exp = 0
        self.reward_karma = 0
    
    def add_task(self, task: MissionTask):
        self.tasks.append(task)
    
    def __repr__(self):
        return f"MissionBranch(id={self.branch_id}, tasks={len(self.tasks)})"


class MissionDefinition:
    """Complete mission definition parsed from XML."""
    
    def __init__(self, mission_id: int):
        self.mission_id = mission_id
        self.name = ""
        self.map_id = 0
        self.cost_badge = 0
        self.threat_up = 0
        self.threat_down = 0
        self.level = 1
        self.min_level = 1
        self.max_level = 99
        self.predecessors_mission = ""
        self.mission_time = 0
        self.branches: List[MissionBranch] = []
        self.reward_exp = 0
        self.reward_karma = 0
        self.new_mission_id = 0
    
    @property
    def all_tracks(self) -> List[MissionTrack]:
        """Get all tracks from all branches and tasks."""
        tracks = []
        for branch in self.branches:
            for task in branch.tasks:
                tracks.extend(task.tracks)
        return tracks
    
    @property
    def total_objectives(self) -> int:
        """Total number of track objectives."""
        return len(self.all_tracks)
    
    def __repr__(self):
        return f"Mission(id={self.mission_id}, name='{self.name}', branches={len(self.branches)})"


class MissionParser:
    """Parse and cache mission data from Missions.xml."""
    
    def __init__(self, xml_path: str = None):
        self._missions: Dict[int, MissionDefinition] = {}
        self._xml_path = xml_path
        
        if xml_path:
            self.load(xml_path)
    
    def load(self, xml_path: str) -> Dict[int, MissionDefinition]:
        """Parse Missions.xml and return mission definitions."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            for mission_elem in root.findall('Mission'):
                mission = self._parse_mission(mission_elem)
                if mission:
                    self._missions[mission.mission_id] = mission
            
            print(f"Loaded {len(self._missions)} missions from {xml_path}")
            return self._missions
        
        except Exception as e:
            print(f"Error loading missions from {xml_path}: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _parse_mission(self, mission_elem) -> Optional[MissionDefinition]:
        """Parse a single Mission XML element."""
        # Get mission ID
        id_elem = mission_elem.find('ID')
        if id_elem is None or 'value' not in id_elem.attrib:
            return None
        
        mission_id = int(id_elem.attrib['value'])
        mission = MissionDefinition(mission_id)
        
        # Parse basic fields
        def get_int(elem, tag, default=0):
            el = elem.find(tag)
            if el is not None and 'value' in el.attrib:
                return int(el.attrib['value'])
            return default
        
        def get_str(elem, tag, default=""):
            el = elem.find(tag)
            if el is not None and 'value' in el.attrib:
                return el.attrib['value']
            return default
        
        mission.name = get_str(mission_elem, 'Name')
        mission.map_id = get_int(mission_elem, 'MapID')
        mission.cost_badge = get_int(mission_elem, 'CostBadge')
        mission.threat_up = get_int(mission_elem, 'ThreatUpValue')
        mission.threat_down = get_int(mission_elem, 'ThreatDownValue')
        mission.level = get_int(mission_elem, 'MissionLevel')
        mission.min_level = get_int(mission_elem, 'Minlevel')
        mission.max_level = get_int(mission_elem, 'Maxlevel')
        mission.predecessors_mission = get_str(mission_elem, 'PredecessorsMission')
        mission.mission_time = get_int(mission_elem, 'MissionTime')
        mission.reward_exp = get_int(mission_elem, 'MissionRewardExp')
        mission.reward_karma = get_int(mission_elem, 'MissionRewardKarma')
        # NewMissionID can be multiple IDs separated by semicolons
        new_mission_str = get_str(mission_elem, 'NewMissionID')
        if new_mission_str and ';' in new_mission_str:
            mission.new_mission_id = int(new_mission_str.split(';')[0])  # Take first ID
        else:
            mission.new_mission_id = int(new_mission_str) if new_mission_str else 0
        
        # Parse branches
        for branch_elem in mission_elem.findall('Branch'):
            branch = self._parse_branch(branch_elem)
            if branch:
                mission.branches.append(branch)
        
        return mission
    
    def _parse_branch(self, branch_elem) -> Optional[MissionBranch]:
        """Parse a Branch XML element."""
        branch_id_elem = branch_elem.find('BranchID')
        if branch_id_elem is None or 'value' not in branch_id_elem.attrib:
            return None
        
        branch = MissionBranch(
            branch_id=int(branch_id_elem.attrib['value']),
            is_must_complete=branch_elem.find('isBranchMustComplete').attrib.get('value', 'True') == 'True'
        )
        
        # Parse branch reward
        reward_elem = branch_elem.find('Reward')
        if reward_elem is not None:
            content = reward_elem.find('BranchRewardContent')
            if content is not None:
                branch.reward_exp = int(content.attrib.get('Exp', '0'))
                branch.reward_karma = int(content.attrib.get('karma', '0'))
        
        # Parse tasks
        for task_elem in branch_elem.findall('Task'):
            task = self._parse_task(task_elem)
            if task:
                branch.tasks.append(task)
        
        return branch
    
    def _parse_task(self, task_elem) -> Optional[MissionTask]:
        """Parse a Task XML element."""
        task_id_elem = task_elem.find('TaskID')
        if task_id_elem is None or 'value' not in task_id_elem.attrib:
            return None
        
        # Handle semicolon-separated values
        def parse_multi_int(val, default=1):
            if val and ';' in val:
                return int(val.split(';')[0])  # Take first value
            try:
                return int(val) if val else default
            except ValueError:
                return default
        
        task = MissionTask(
            task_id=int(task_id_elem.attrib['value']),
            trigger_id=task_elem.find('TriggerId').attrib.get('value', ''),
            trigger_type=parse_multi_int(task_elem.find('TriggerType').attrib.get('value'), 1)
        )
        
        # Parse mission tracks
        for track_elem in task_elem.findall('.//trackContent'):
            track = MissionTrack(
                track_type=int(track_elem.attrib.get('trackType', '0')),
                object_id=int(track_elem.attrib.get('objectId', '0')),
                count=int(track_elem.attrib.get('count', '0')),
                recycle=int(track_elem.attrib.get('recycle', '0'))
            )
            task.add_track(track)
        
        # Parse task reward
        reward_elem = task_elem.find('Reward')
        if reward_elem is not None:
            content = reward_elem.find('TaskRewardContent')
            if content is not None:
                task.reward_exp = int(content.attrib.get('Exp', '0'))
                task.reward_karma = int(content.attrib.get('karma', '0'))
        
        return task
    
    def get_mission(self, mission_id: int) -> Optional[MissionDefinition]:
        """Get a specific mission by ID."""
        return self._missions.get(mission_id)
    
    def get_missions_by_map(self, map_id: int) -> List[MissionDefinition]:
        """Get all missions for a specific map."""
        return [m for m in self._missions.values() if m.map_id == map_id]
    
    def get_missions_for_player_level(self, player_level: int) -> List[MissionDefinition]:
        """Get all missions available for a player's level."""
        return [
            m for m in self._missions.values()
            if m.min_level <= player_level <= m.max_level
        ]
    
    def get_all_missions(self) -> Dict[int, MissionDefinition]:
        """Get all loaded missions."""
        return self._missions
    
    @property
    def mission_ids(self) -> List[int]:
        """Get list of all mission IDs."""
        return list(self._missions.keys())


# Module-level convenience function
_mission_parser = None

def parse_missions_xml(xml_path: str = None) -> MissionParser:
    """Load or return cached mission parser instance."""
    global _mission_parser
    
    if _mission_parser is None:
        if xml_path is None:
            # Default path - look for Missions.xml directly in this directory
            import os
            xml_path = os.path.join(os.path.dirname(__file__), 'Missions.xml')
        
        _mission_parser = MissionParser(xml_path)
    
    return _mission_parser
