#!/usr/bin/env python3
"""
Akaneiro Demon Hunters - Complete Local Game Server (TCP)
Handles all 65 client request protocol messages with SQLite persistence.

Protocol format:
  [4 bytes body size][2 bytes message type][body]
  
Message types:
  0 = ePacketGameLogic (actual game protocol messages)
  1 = ePacketHeartBeatPing
  2 = ePacketHeartBeatPong

Game logic packet body:
  [4 bytes method ID][payload...]
"""

import socket
import struct
import threading
import time
import json
import sys
import signal
import sqlite3
import os
import random

# Use script directory for database path so it works from any working directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Protocol message IDs (from ProtocolGameServer_Client.cs)
USER_LOGIN = 0x0ce102e4
USER_LOGIN_OK = 0x57aaeebc
USER_LOGIN_FAILED = 0x751085d9
USER_CREATE_CHARACTER = 0x4a7e8568
USER_CREATE_CHARACTER_OK = 0x3b5d1160
USER_CREATE_CHARACTER_FAILED = 0x1d6213bd
USER_SELECT_CHARACTER = 0x453c0ad8
USER_SELECT_CHARACTER_OK = 0x25f31250
USER_SELECT_CHARACTER_FAILED = 0x6fb2ffad
ENTER_SCENE = 0x17e15f02
ENTER_SCENE_OK = 0x52ca05ea
MAP_LOAD_OK = 0x31b7ac64
CHARACTER_START_INFO = 0x4f8580ad
TUTORIAL_ENTER_REQ = 0x2119e24e
TUTORIAL_ENTER_ACK = 0x21156da9
ACCEPT_MISSION = 0x2671513a
ACCEPT_MISSION_OK = 0x23e31e2
PING_REQUEST = 0x4417ca2b
PING_REQUEST_ACK = 0x3bfd8f66
GET_PLAYER_MAIL = 0x2488106c
GET_PLAYER_MAIL_RESULT = 0x41301fcd
REQUEST_DAY_REWARD = 0x3bd47c8a
REQUEST_DAY_REWARD_OK = 0x3710a792
GET_FRIEND_REWARD = 0x460f4251
HAS_ASSIGNED_TALENT_POINT_REQ = 0x7ab097d0
HAS_ASSIGNED_TALENT_POINT_ACK = 0x7aac232b

# Additional protocol IDs for complete implementation
BUY_CHAR_SLOT_REQUEST = 0x239521db
BUY_CHAR_SLOT_RESULT = 0x2e769d19
BUY_CONSUME_ITEM = 0x30d43d37
BUY_CONSUME_ITEM_SUCC_ACK = 0x5f3ca0e8
BUY_ITEM = 0x58dbf93f
BUY_ITEM_SUCC_ACK = 0x4bbfb540
BUY_PET = 0x4fd494e7
BUY_PET_ACK = 0xd3edb3a
CHANGE_GENDER_REQ = 0x1b3da913
CHANGE_GENDER_RESULT = 0x7f198b8c
CHANGE_NAME_REQ = 0x734db755
CHANGE_NAME_RESULT = 0x9e00782
CHAT_REQUEST = 0x272d1175
CHAT_REQUEST_ACK = 0x1824fb34
CRAFTING_ITEM = 0x316d3259
CRAFTING_ITEM_OK = 0x51108549
DEL_ITEM = 0x25ca37a4
DELETE_MAIL = 0x574cf938
DELETE_MAIL_RESULT = 0x50e4f8b9
EQUIP_ITEM = 0x735dc30d
GET_DAY_REWARD = 0x69d41337
GET_DAY_REWARD_RESULT = 0x317566e0
GET_GIFT_REQ = 0x2924f5ba
GET_GIFT_ACK = 0x29208115
GET_LEADERBOARD_INFO = 0x7dba1753
UPDATE_LEADERBOARD_INFO = 0x1a864980
GET_MAIL_ALL = 0x3cc4874a
GET_MAIL_ALL_RESULT = 0x26c54bfb
GET_MAIL_ITEM = 0x19a5bcd6
GET_MAIL_ITEM_RESULT = 0x686f73a7
GET_MAIL_PET = 0x3cc87144
GET_MAIL_PET_RESULT = 0x94fee5
GET_REDEEM_GIFT = 0xc693488
GET_REDEEM_GIFT_RESULT = 0x6b5caf89
GET_WELL_DATA = 0x84618f0
GET_WELL_DATA_RESULT = 0x183543b1
LEAVE_WORLD = 0x26917cc5
MISSION_FAIL_REQ = 0x371cf36e
MISSION_FAIL_ACK = 0x37187ec9
MISSION_LIST_REQ = 0xa821e
MISSION_LIST_ACK = 0x60d79
MISSION_PROCESS_REQ = 0x6bea46f9
SEND_MISSION_PROCESS = 0x6a572951
OPEN_MAIL = 0x5f28d4e7
PROCESS_FRIEND_REWARD = 0x453bc86e
PROCESS_REDEEM_GIFT = 0x73d1bffd
PROCESS_REDEEM_GIFT_RESULT = 0x1ac4bcb6
REQUEST_BAG_INFO = 0x103f2625
SEND_BAG_INFO = 0x79d003d4
REQUEST_PLAYER_CONSUME_SHOP_INFO = 0x4e24fd8a
SEND_SHOP_CONSUME_ITEMINFO = 0x8b9884d
REQUEST_PLAYER_SHOP_INFO = 0x1987204e
SEND_SHOP_ITEMINFO = 0x1ec3c8fd
ROLE_MASTERY_LIST_REQ = 0x6036f375
ROLE_MASTERY_LIST_ACK = 0x60327ed0
ROLE_PET_LIST_REQ = 0x13677115
ROLE_PET_LIST_ACK = 0x1362fc70
SALE_ITEM = 0x68671bdc
SEND_MAIL = 0x2130aaa1
SEND_MAIL_RESULT = 0x7e52edba
SPEED_UP_COOL_DOWN = 0x4864d33
SPEED_UP_COOL_DOWN_RESULT = 0x3cdc217c
SPLIT_ITEM = 0x46d93073
STUDY_ABILITY = 0x7f2b6d23
STUDY_ABILITY_SUCCEED = 0x3d121e4f
SWAP_ITEM = 0x6228180c
UNEQUIP_ITEM = 0x62488be4
UPGRADE_WELL = 0x6cb9f2d0
UPGRADE_WELL_RESULT = 0x61139291
USER_DEL_CHARACTER = 0x40213e67
USER_DEL_CHARACTER_RESULT = 0x59651290
USER_LOGOUT = 0x172610eb
ASSIGN_TALENT_REQ = 0x2853dda9
ASSIGN_TALENT_ACK = 0x284f6904
BUY_ALL_AREA_BY_KARMA_REQ = 0x5cec63db
BUY_ALL_AREA_BY_KARMA_ACK = 0x5ce7ef36
BUY_STASH = 0x14d0a31d
BUY_STASH_ACK = 0x54db3ec
BUY_THREAT_LEVEL_BY_KARMA = 0x3e35273
BUY_THREAT_LEVEL_BY_KARMA_ACK = 0x2dc6bafe
CHOOSE_PET = 0x121a7bce
CHOOSE_PET_ACK = 0x5eb32417
CONVERSATION_NPC_CHECK_REQ = 0xb3c9e4a
CONVERSATION_NPC_CHECK_ACK = 0xb3829a5
DECREASE_COOL_DOWN = 0x17c116df
DECREASE_COOL_DOWN_ACK = 0x7f792462
EXPLORETASKCOMPLETE_REQ = 0x291e724f
EXPLORETASKCOMPLETE_ACK = 0x2919fdaa
MASTERY_LVLUP_REQ = 0x3086dbca
MASTERY_LVLUP_ACK = 0x30826725
PROTECTTASKBEGIN_REQ = 0x614b1783
PROTECTTASKEND_REQ = 0x6d99ca21
ROLE_ATTRIB_REQ = 0x27a7fc3c
UNLOCK_AREA_REQ = 0x1265c537
UNLOCK_AREA_ACK = 0x12615092
USE_ITEM = 0x2563040
USER_RECONNECT = 0x5469770e
USER_CREATE_ACCOUNT_CHARACTER = 0x2c75d66d
RELOAD_MAP = 0x3fa4968b
GET_MAIL_KARMA = 0x4062b379
GET_MAIL_KARMA_RESULT = 0x414734d2
GET_MAIL_CRYSTAL = 0x225817af
GET_MAIL_CRYSTAL_RESULT = 0x381d898
DELETE_MAIL_ITEM = 0x5e47601b
GET_MAIL_ALL_ITEMS = 0x4122465a
GET_MAIL_ALL_ITEMS_RESULT = 0x360af08b
GET_MAIL_ALL_PETS = 0x6af25936
DELETE_MAIL_PET = 0x1c15e3db
GET_WELL_KARMA = 0x36be3f7a
GET_WELL_KARMA_RESULT = 0xf577cab
UPDATE_EVENT = 0x6afada73

# Battle protocol method IDs (from ProtocolBattle_Client.cs)
ACTIVE_TRIGGER_REQ = 0x15b12682
ALLY_NPC_ENTER = 0x5cdcbee1
ALLY_REGENERATE = 0x33aaa61e
ALLY_UPDATE_MOVE_REQUEST = 0x51da0fa7
BEGIN_USE_SKILL = 0x1987c5a1
BREAK_SING = 0x21d334b8
BREAKABLE_ACTOR_ENTER = 0x3ee28776
BULLET_HIT = 0x62a70a23
CHARACTER_PRIVATE_INFO_UPDATE = 0x2de31e13
CHARACTER_START_INFO_BATTLE = 0x4f8580ad
CHARACTER_UPDATE = 0x43050760
CREATE_ALLY_NPC_REQUEST = 0x56785124
ENEMY_REWARD_REQ = 0x27f66af5
ENTER_SCENE_BATTLE = 0x17e15f02
ENTER_SCENE_OK_BATTLE = 0x52ca05ea
FRIEND_ALLY_ENTER = 0x7ce44418
GET_FRIEND_LIST = 0x738db628
GET_FRIEND_LIST_RESULT = 0x150a7029
ITEM_ENTER = 0x72e321bf
MAP_LOAD_OK_BATTLE = 0x31b7ac64
MOVE_UNIT = 0x528e2717
OBJECT_ENTER_TEST = 0x1a749d91
OBJECT_LEAVE = 0x15bd062a
PICKUP_ITEM_FAILED = 0x60274b82
PICKUP_ITEM_REQ = 0x44e05119
PICKUP_ITEM_SUCC_ACK = 0x1cf304d2
PICKUP_MONEY_REQ = 0x65513c7c
PICKUP_MONEY_RESULT = 0x503c611f
PLAYER_CHANGE_WEAPON = 0x5851e5d3
PLAYER_CHANGE_WEAPON_OK = 0xa077643
PLAYER_FIRE_REQ = 0x3d5da371
PLAYER_REGENERATE = 0x71fc5c6b
PLAYER_REVIVE_NUM_NTF = 0x169774ca
PLAYER_USE_COOL_WEAPON_REQ = 0x4cb913e5
REVIVE_REQ = 0x4235c33b
REVIVE_RESULT = 0x307f69c4
RUSH_HIT = 0x3ecf5335
SELECT_FRIEND_ALLY = 0x44e1eaf8
SELECT_FRIEND_ALLY_RESULT = 0x7a052479
SERIAL_KILL_OVER = 0x1977050
SET_KNOCK_BACK_SPEED = 0x7b9f97cc
SET_MOVE_TYPE = 0x19b3c9af
SET_MOVE_TYPE_FAIL = 0x31230f51
SET_MOVE_TYPE_RESULT = 0x7901ba98
SET_OBJECT_POSITION = 0x287c23c8
SET_OBJECT_VEC_POSITION = 0x665715f6
SET_SKILL_SHORTCUT = 0x14bbe8bf
SKILL_OBJECT_ACTIVE = 0x30c00e78
SKILL_OBJECT_ENTER = 0x5c94540e
SPAWNNER_KILLED = 0x2ec62427
SPEECH_RESULT = 0x66f3225
STOP_BEGIN_USE_SKILL = 0x27b5cf97
SYNC_CUR_TIME = 0x2cc63fdc
TELE_PORT_MOVE_RESULT = 0x510a4277
TRAP_HIT = 0x7ac343b4
TRIGGER_ALL = 0x1d00931f
TRIGGER_ANIMATION_RESULT = 0x49a12493
UPDATE_ANIMATION = 0x1ef9479d
UPDATE_ANIMATION_NOTIFY = 0x2d3baad6
UPDATE_MOVE_FAIL = 0x16e5dc8a
UPDATE_MOVE_REQUEST = 0x3f03a05b
UPDATE_MOVE_RESULT = 0x890dc99
UPDATE_SERIAL_KILL_NUM = 0x47208f05
UPDATE_STATUS_EFFECT = 0x3df0eca
USE_ALLY_NORMAL_ATTACK = 0x1f2b374c
USE_ALLY_SKILL = 0xb899ec0
USE_FIGHT_SKILL = 0x3198ed6e
USE_FIGHT_SKILL_FAILED = 0xbebe2d3
USE_FIGHT_SKILL_RESULT = 0x1dafac7f
USE_NORMAL_ATTACK = 0x2a9c698
USE_NORMAL_ATTACK_FAILED = 0x7de4656d
USE_NORMAL_ATTACK_RESULT = 0xfa82f19
MONEY_ENTER = 0x6a74b232
MONSTER_ENTER = 0x1f480d0c
NPC_ENTER = 0x123144fd

# Remaining protocol method IDs for completeness
ACCEPT_MISSION_FAIL = 0x5a06c44c
ADD_EXP_NTF = 0x32147f5a
ADD_NEW_ABILITY_NOTIFY = 0x39db31aa
ADD_NEW_MASTERY_NOTIFY = 0x72bad093
BROADCAST_CRAFTING_ITEM_OK = 0x212e9bec
BUY_ITEM_FAILED = 0x173a71fc
CHANGE_CHARACTER_ATTRIB_NTF = 0x42c0dc03
CHAT_FAILED = 0x4f88fe4b
CHAT_RESPONSE = 0x2ca9aef3
CRAFTING_ITEM_FAILED = 0x7a4473b0
DEL_ITEM_FAILED = 0x732e7c99
EQUIP_ERROR_FAILED = 0x2ab4fe9f
LEVEL_UP = 0x4f3cc0df
MATERIAL_MAIL_NOTIFY = 0x6cae9cf5
MISSION_AREA_INFO_ACK = 0x3b7de398
MISSION_COMPLETE_NTF = 0x26549011
MISSION_FAILED_NTF = 0x5113944d
NEW_REDEEM_GIFT = 0x566671a
NOTIFY_ITEM_DESTROY = 0xf602bc8
NOTIFY_ITEM_SWAP = 0x50234afd
NOTIFY_ITEM_UPDATE = 0xa69ab9f
PET_RENT_TIME_END_NTF = 0x799dc100
RECV_NEW_MAIL = 0x6436a28b
REQUEST_DAY_REWARD_FAILED = 0x7986258f
ROLE_FREE_PET_LIST_NTF = 0x6d05a30b
SALE_ITEM_FAILED = 0x7749d811
SELECT_DAY_REWARD_NTF = 0x6b4efbab
SEND_FRIEND_REWARD_INFO = 0x68f84591
SEND_SHOP_RAREITEM_TRACK_INFO = 0x37bbf3a8
SEND_SKILL_INFO = 0x32ed0165
SERVER_SYSTEM_TIME_NOTIFY = 0x5f8961be
SPLIT_ITEM_FAILED = 0x1572b910
STUDY_ABILITY_FAILED = 0x1046ba40
SWAP_ITEM_FAILED = 0x1df0acc1
UNEQUIP_ERROR_FAILED = 0x43c8227c
UPDATE_BADGE = 0x3381131c
UPDATE_BASE_ATTR = 0x208eaf25
UPDATE_CACHE_MONEY_INFO = 0x6c6c2bfd
UPDATE_CHAR_STAT_DATA = 0x60142937
UPDATE_COOL_DOWN = 0x6ed5ea2
UPDATE_ELEMENT_ATTR = 0xc80f536
UPDATE_ELEMENT_CHANCE = 0x528d3069
UPDATE_EVENT = 0x6afada73
UPDATE_JOULE = 0x2f3791f2
UPDATE_MONEY_INFO = 0x325af991
UPDATE_REVIVE_NUM = 0x44223cd2
UPDATE_TUTORIAL_INFO = 0x37d29a47
USER_CHARACTER_INFO = 0x7e535d9e
USER_RECONNECT_NOTIFY = 0x569f4c9f
YOU_CHEAT = 0x1b96589a
BRANCH_COMPLETE_NTF = 0x4db32f63
MISSION_SHOP_NTF = 0x34359f48
TASK_COMPLETE_NTF = 0x55cecf90

# Database setup - use script directory for consistent location
DB_PATH = os.path.join(SCRIPT_DIR, "akaneiro_local.db")

def init_db():
    """Initialize SQLite database with all required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Accounts table - supports both Steam and web (email/password) logins
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            steam_id TEXT UNIQUE,
            email TEXT UNIQUE,
            password TEXT DEFAULT '',
            nickname TEXT DEFAULT 'Player',
            karma INTEGER DEFAULT 1000,
            gold INTEGER DEFAULT 5000,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Characters table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            nickname TEXT NOT NULL,
            style INTEGER DEFAULT 0,
            sex INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            status INTEGER DEFAULT 0,
            is_tutorial BOOLEAN DEFAULT 1,
            current_map TEXT DEFAULT 'Hub_Village',
            x REAL DEFAULT 0.0,
            y REAL DEFAULT 0.0,
            z REAL DEFAULT 0.0,
            hp INTEGER DEFAULT 100,
            max_hp INTEGER DEFAULT 100,
            mp INTEGER DEFAULT 50,
            max_mp INTEGER DEFAULT 50,
            power INTEGER DEFAULT 10,
            defense INTEGER DEFAULT 5,
            skill INTEGER DEFAULT 5,
            phy_atk INTEGER DEFAULT 8,
            damage_reduction INTEGER DEFAULT 2,
            critical INTEGER DEFAULT 1,
            hp_recover INTEGER DEFAULT 1,
            mp_recover INTEGER DEFAULT 1,
            move_speed INTEGER DEFAULT 300,
            attack_speed INTEGER DEFAULT 100,
            critical_damage INTEGER DEFAULT 150,
            creation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    ''')
    
    # Items table (inventory)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            slot INTEGER DEFAULT -1,
            FOREIGN KEY (character_id) REFERENCES characters(id)
        )
    ''')
    
    # Missions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS missions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            mission_id INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            progress INTEGER DEFAULT 0,
            FOREIGN KEY (character_id) REFERENCES characters(id)
        )
    ''')
    
    # Mail table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            sender TEXT DEFAULT 'System',
            subject TEXT DEFAULT '',
            body TEXT DEFAULT '',
            read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (character_id) REFERENCES characters(id)
        )
    ''')
    
    # Pets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            pet_type TEXT DEFAULT 'basic',
            level INTEGER DEFAULT 1,
            FOREIGN KEY (character_id) REFERENCES characters(id)
        )
    ''')
    
    # Mastery table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mastery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            mastery_type TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            FOREIGN KEY (character_id) REFERENCES characters(id)
        )
    ''')
    
    # Talent table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS talent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            prowess INTEGER DEFAULT 0,
            fortitude INTEGER DEFAULT 0,
            cunning INTEGER DEFAULT 0,
            left_points INTEGER DEFAULT 0,
            FOREIGN KEY (character_id) REFERENCES characters(id)
        )
    ''')
    
    # Well data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS well_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            speed_level INTEGER DEFAULT 1,
            time_level INTEGER DEFAULT 1,
            lid_level INTEGER DEFAULT 1,
            begin_time INTEGER DEFAULT 0,
            FOREIGN KEY (character_id) REFERENCES characters(id)
        )
    ''')
    
    # Leaderboard table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            score INTEGER DEFAULT 0,
            rank INTEGER DEFAULT 999,
            FOREIGN KEY (character_id) REFERENCES characters(id)
        )
    ''')
    
    # Shop items table (static data)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            price INTEGER NOT NULL,
            currency TEXT DEFAULT 'gold'
        )
    ''')
    
    # Insert some default shop items
    cursor.execute("SELECT COUNT(*) FROM shop_items")
    if cursor.fetchone()[0] == 0:
        shop_data = [
            ('weapon', 1001, 500), ('weapon', 1002, 1000), ('weapon', 1003, 2000),
            ('armor', 2001, 400), ('armor', 2002, 800), ('armor', 2003, 1500),
            ('accessory', 3001, 200), ('accessory', 3002, 400),
            ('potion_hp', 4001, 50), ('potion_mp', 4002, 50),
        ]
        for item_type, item_id, price in shop_data:
            cursor.execute("INSERT INTO shop_items (item_type, item_id, price) VALUES (?, ?, ?)", 
                          (item_type, item_id, price))
    
    conn.commit()
    conn.close()
    print(f"Database initialized: {DB_PATH}")

# Global flag for clean shutdown
running = True

def signal_handler(sig, frame):
    global running
    print("\nShutting down game server...")
    running = False

class PacketWriter:
    """Builds binary protocol packets matching C# Packet class behavior."""
    
    def __init__(self):
        self.data = bytearray()
    
    def write_int(self, v):
        self.data.extend(struct.pack('<i', v))
    
    def write_float(self, v):
        self.data.extend(struct.pack('<f', float(v)))
    
    def write_uint(self, v):
        self.data.extend(struct.pack('<I', v))

    def write_uint64(self, v):
        self.data.extend(struct.pack('<Q', v))
    
    def write_short(self, v):
        self.data.extend(struct.pack('<h', v))
    
    def write_ushort(self, v):
        self.data.extend(struct.pack('<H', v))
    
    def write_byte(self, v):
        self.data.append(v & 0xff)
    
    def write_bool(self, v):
        self.write_byte(1 if v else 0)
    
    def write_string(self, s):
        if s is None:
            s = ""
        encoded = s.encode('utf-8')
        self.write_int(len(encoded))
        self.data.extend(encoded)
    
    def write_long(self, v):
        self.data.extend(struct.pack('<q', v))
    
    def get_bytes(self):
        return bytes(self.data)

def make_game_packet(method_id, body_writer=None):
    """Create a complete game logic packet with framing."""
    # Build inner payload: [method ID][body]
    inner = PacketWriter()
    inner.write_int(method_id)
    if body_writer:
        inner_data = body_writer.get_bytes()
        inner.data.extend(inner_data)
    
    inner_bytes = inner.get_bytes()
    
    # Frame it: [4 bytes size][2 bytes type=0 (game logic)][body]
    framed = PacketWriter()
    framed.write_int(len(inner_bytes))
    framed.write_short(0)  # ePacketGameLogic
    framed.data.extend(inner_bytes)
    
    return framed.get_bytes()

def make_heartbeat_pong():
    """Create heartbeat pong response."""
    pkt = PacketWriter()
    pkt.write_int(0)  # body size
    pkt.write_short(2)  # ePacketHeartBeatPong
    return pkt.get_bytes()

def build_packet(method_id, body):
    """Alias for make_game_packet - builds a game logic packet."""
    if isinstance(body, bytes):
        pw = PacketWriter()
        pw.data.extend(body)
        body = pw
    return make_game_packet(method_id, body)

# Store current account context for character creation
current_account_id = None
current_character_id = None
current_map_name = ""

# Spawn positions for each map (x, y, z)
# Positions extracted from XML Scene_Objs in akaneiro-client-compiled/assetbundles/XML/SCENE/
SPAWN_POSITIONS = {
    "Hub_Village": (81.35, 2.05, 84.85),
    "Hub_Village_Tutorial": (51.39, 6.98, 99.23),
    # Area 1 - Shigemori River
    "A1_M1": (100.0, 2.0, 100.0), "A1_M2": (100.0, 2.0, 100.0),
    "A1_M3": (100.0, 2.0, 100.0), "A1_M4": (100.0, 2.0, 100.0),
    # Area 2 - Jawbone Ravine
    "A2_M1": (100.0, 2.0, 100.0), "A2_M2": (100.0, 2.0, 100.0),
    "A2_M3": (100.0, 2.0, 100.0), "A2_M4": (100.0, 2.0, 100.0),
    # Area 3 - Bloodroot Cemetery
    "A3_M1": (100.0, 2.0, 100.0), "A3_M2": (100.0, 2.0, 100.0),
    "A3_M3": (100.0, 2.0, 100.0), "A3_M4": (100.0, 2.0, 100.0),
    # Area 4 - Bloodfang Fort
    "A4_M1": (100.0, 2.0, 100.0), "A4_M2": (100.0, 2.0, 100.0),
    "A4_M3": (100.0, 2.0, 100.0), "A4_M4": (100.0, 2.0, 100.0),
    # Area 5 - Shivering Pines
    "A5_M1": (100.0, 2.0, 100.0), "A5_M2": (100.0, 2.0, 100.0), "A5_M3": (100.0, 2.0, 100.0),
    # Area 6 - Yurei Caverns
    "A6_M1": (100.0, 2.0, 100.0), "A6_M2": (100.0, 2.0, 100.0), "A6_M3": (100.0, 2.0, 100.0),
    # Area 7 - Melon Fields
    "A7_M1": (100.0, 2.0, 100.0), "A7_M2": (100.0, 2.0, 100.0), "A7_M3": (100.0, 2.0, 100.0),
    # Area 8 - Temple Depths
    "A8_M1": (100.0, 2.0, 100.0), "A8_M2": (100.0, 2.0, 100.0), "A8_M3": (100.0, 2.0, 100.0),
    # Special maps
    "TWILIGHT": (100.0, 2.0, 100.0),
}
DEFAULT_SPAWN = (100.0, 2.0, 100.0)

def parse_string(data, offset):
    """Parse a length-prefixed UTF-8 string from data at offset. Returns (string, new_offset)."""
    if offset + 4 > len(data):
        return None, offset
    length = struct.unpack_from('<i', data, offset)[0]
    offset += 4
    if offset + length > len(data):
        return None, offset
    s = data[offset:offset+length].decode('utf-8')
    return s, offset + length

def parse_map_int_int(data, offset):
    """Parse a mapIntInt (Dictionary<int,int>) from data at offset. Returns (dict, new_offset)."""
    if offset + 4 > len(data):
        return None, offset
    count = struct.unpack_from('<i', data, offset)[0]
    offset += 4
    result = {}
    for _ in range(count):
        if offset + 8 > len(data):
            return None, offset
        key = struct.unpack_from('<i', data, offset)[0]
        value = struct.unpack_from('<i', data, offset+4)[0]
        result[key] = value
        offset += 8
    return result, offset

def get_or_create_account(account_identifier):
    """Get existing account or create new one. Supports Steam ID or email.
    Returns (account_id, karma)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Try to find existing account by Steam ID first
    cursor.execute("SELECT id, karma FROM accounts WHERE steam_id = ?", (account_identifier,))
    row = cursor.fetchone()
    
    if not row:
        # Try to find by email (web login)
        cursor.execute("SELECT id, karma FROM accounts WHERE email = ?", (account_identifier,))
        row = cursor.fetchone()
    
    if row:
        account_id, karma = row
        print(f"Existing account found: {account_id} (karma={karma})")
    else:
        # Create new account - determine if Steam or web based on format
        if '@' in account_identifier:
            # Web login with email
            cursor.execute(
                "INSERT INTO accounts (email, password) VALUES (?, ?)",
                (account_identifier, 'password')  # Default password for now
            )
            print(f"New web account created: {cursor.lastrowid} for email={account_identifier}")
        else:
            # Steam login
            cursor.execute(
                "INSERT INTO accounts (steam_id) VALUES (?)",
                (account_identifier,)
            )
            print(f"New Steam account created: {cursor.lastrowid} for steam_id={account_identifier}")
        
        account_id = cursor.lastrowid
        karma = 1000
    
    conn.commit()
    conn.close()
    return account_id, karma

def get_characters_for_account(account_id):
    """Get all characters for an account. Returns list of character dicts."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, nickname, style, sex, level, exp, status, is_tutorial, creation_time "
        "FROM characters WHERE account_id = ?",
        (account_id,)
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    chars = []
    for row in rows:
        chars.append({
            'id': row[0],
            'nickname': row[1],
            'style': row[2],
            'sex': row[3],
            'level': row[4],
            'exp': row[5],
            'status': row[6],
            'is_tutorial': bool(row[7]),
            'creation_time': row[8]
        })
    
    return chars

def handle_user_login(account, user_type, client_type, password, token):
    """Handle UserLogin request and send On_UserLoginOK response."""
    print(f"UserLogin: account={account}, type={user_type}, client={client_type}")
    
    try:
        # Get or create account in database
        account_id, karma = get_or_create_account(account)
        
        # Build SAccountInfo with real data from DB
        account_info = PacketWriter()
        account_info.write_string(account)           # account
        account_info.write_string("123456")          # password (mock)
        account_info.write_string(f"Player{account_id}")  # nickName
        account_info.write_int(account_id)           # id
        account_info.write_int(0)                    # gender (0=female, 1=male)
        account_info.write_int(0)                    # type
        account_info.write_int(user_type)            # userType
        account_info.write_int(0)                    # points
        account_info.write_string("2026-01-01")      # createTime (mock)
        account_info.write_int(0)                    # status (0=normal)
        account_info.write_int(0)                    # statusChangeTime
        account_info.write_int(0)                    # totalOnlineTime
        account_info.write_int(0)                    # todayOnlineTime
        account_info.write_string("127.0.0.1")       # lastLoginIP
        account_info.write_int(int(time.time()))     # lastLoginTime
        account_info.write_string("127.0.0.1")       # currentIP
        account_info.write_int(0)                    # lastCharID
        account_info.write_int(0)                    # friendVersion
        account_info.write_int(0)                    # FK
        account_info.write_int(karma)                # SK (karma from DB)
        account_info.write_int(1)                    # level
        account_info.write_int(3)                    # curCharSlotNum (3 slots)
        account_info.write_int(0)                    # reviveNum
        
        # mapEvent: [count][key,value pairs]
        account_info.write_int(0)  # empty event data
        
        # SWellData: speedLevel, timeLevel, lidLevel, beginTime
        account_info.write_int(1)   # speedLevel
        account_info.write_int(1)   # timeLevel
        account_info.write_int(1)   # lidLevel
        account_info.write_long(0)  # beginTime
        
        account_info.write_int(0)   # isGetRevivalCard
        
        # Get character list from DB and serialize it
        chars = get_characters_for_account(account_id)
        print(f"UserLogin: Found {len(chars)} characters for account {account_id}")
        for c in chars:
            print(f"  Char {c['id']}: {c['nickname']} (level={c['level']}, style={c['style']})")
        char_list = PacketWriter()
        char_list.write_int(len(chars))  # count of characters
        
        for char in chars:
            # Serialize each SCharacterInfoLogin
            char_list.write_int(char['id'])
            char_list.write_string(char['nickname'])
            char_list.write_int(0)              # badgeNum
            char_list.write_int(char['sex'])
            char_list.write_int(char['style'])
            char_list.write_int(char['level'])
            char_list.write_uint64(char['exp'])  # uint64 exp
            # creation_time is a string from DB, convert to timestamp
            try:
                ct = int(time.mktime(time.strptime(char['creation_time'], "%Y-%m-%d %H:%M:%S")))
            except:
                ct = int(time.time())
            char_list.write_int(ct)             # creationTime (NatureTime)
            char_list.write_int(char['status'])
            
            # equipinfo: vectorSItemuuid [count][items] - character's equipped items
            try:
                eq_conn = sqlite3.connect(DB_PATH)
                eq_cursor = eq_conn.cursor()
                eq_cursor.execute(
                    "SELECT item_type, item_id, slot FROM items WHERE character_id = ? AND slot < 100",
                    (char['id'],)
                )
                equipped_items = eq_cursor.fetchall()
                eq_conn.close()
                
                char_list.write_int(len(equipped_items))  # count
                for item_type, item_id, db_slot in equipped_items:
                    client_slot = EQUIPMENT_SLOTS.get(item_type, db_slot)
                    prefab_id = get_prefab_id(item_id, char['style'])
                    char_list.write_int(client_slot)    # slotPart
                    char_list.write_int(item_id)        # itemID
                    char_list.write_int(1)              # itemLevel
                    char_list.write_int(0)              # gemID
                    char_list.write_int(0)              # elementID
                    char_list.write_int(0)              # enchantID
                    char_list.write_int(prefab_id)      # prefabID
            except Exception as e:
                print(f"Error building equipinfo for char {char['id']}: {e}")
                char_list.write_int(0)  # fallback to empty
            
            char_list.write_bool(char['is_tutorial'])
            
            # attrVec: vectorAttrChange - base stats for display on select screen
            attrs = [
                (0, 100),   # CurHP = 100
                (1, 50),    # CurMP = 50
                (2, 100),   # MaxHP = 100
                (3, 50),    # MaxMP = 50
                (4, 10),    # Power = 10
                (5, 5),     # Defense = 5
                (6, 5),     # Skill = 5
                (7, 8),     # PhyAtk = 8
                (8, 2),     # DamageReduction = 2
                (9, 1),     # Critical = 1
                (10, 1),    # HPRecover = 1
                (11, 1),    # MPRecover = 1
                (12, 300),  # MoveSpeed = 3.0 * 100 (scaled int)
                (13, 100),  # AttackSpeed = 1.0 * 100 (scaled int)
                (14, 150),  # CriticalDamage = 1.5 * 100 (scaled int)
            ]
            print(f"Sending attrVec for char {char['id']} ({char['nickname']}): {len(attrs)} attrs")
            char_list.write_int(len(attrs))  # count
            for attr_type, value in attrs:
                char_list.write_int(attr_type)  # EAttributeType as int
                char_list.write_int(value)      # Always int
        
        # Build On_UserLoginOK response
        body = PacketWriter()
        body.write_bool(False)  # reconnected = false
        body.data.extend(account_info.get_bytes())
        body.data.extend(char_list.get_bytes())
        
        packet = make_game_packet(USER_LOGIN_OK, body)
        print(f"Login response built, size={len(packet)}")
        return packet
    except Exception as e:
        print(f"Error building login response: {e}")
        import traceback
        traceback.print_exc()
        # Return a minimal failure packet
        fail_body = PacketWriter()
        fail_body.write_int(1)  # error code
        return make_game_packet(USER_LOGIN_FAILED, fail_body)

# Class-specific starter items mapping
# style=1=Prowess, style=2=Fortitude, style=4=Cunning
CLASS_STARTER_ITEMS = {
    1: {  # Prowess - melee fighters
        'weapon': 1001,   # Katana (balanced one-handed)
        'helm': 2001,
        'breastplate': 2002,
        'breeches': 2003,
    },
    2: {  # Fortitude - tanks/support
        'weapon': 1003,   # Club (reliable one-handed)
        'helm': 2001,
        'breastplate': 2002,
        'breeches': 2003,
    },
    4: {  # Cunning - stealth/range
        'weapon': 1008,   # Sickle (fast attack speed)
        'helm': 2001,
        'breastplate': 2002,
        'breeches': 2003,
    },
}

# Equipment slot mapping - stores CLIENT indices directly
# Client uses: 0=helm, 1=necklace, 2=chest, 3=cloak, 4=ring, 6/7=weapons, 8=legs
EQUIPMENT_SLOTS = {
    'weapon': 6,      # One-handed weapon slot (client index 6)
    'weapon_2h': 7,   # Two-handed weapon slot (client index 7)
    'helm': 0,        # Head slot (client index 0)
    'necklace': 1,    # Neck/Necklace slot (client index 1)
    'breastplate': 2, # Chest slot (client index 2)
    'cloak': 3,       # Back/Cloak slot (client index 3)
    'ring': 4,        # Ring slot (client index 4)
    'breeches': 8,    # Legs slot (client index 8)
}

# Armor class base prefabIDs based on CSV (ArmorAttribute.Prefab.EN.txt)
# Light (style=4/Cunning): 101, Medium (style=3/Fortitude): 301, Heavy (style=2/Prowess): 401
ARMOR_CLASS_BASE = {
    1: 401,  # Prowess - Heavy (SAM01)
    2: 301,  # Fortitude - Medium (SLD01) 
    3: 301,  # Default to Medium
    4: 101,  # Cunning - Light (MNK01)
}

# Weapon prefabIDs from WeaponAttribute.prefab.EN.txt (level 1-6 uses prefabID=1)
WEAPON_LEVEL_1_PREFABID = 1  # WPN01 for levels 1-6

def get_prefab_id(item_id, style=1):
    """Calculate prefab ID from item ID for equipment/3D models.
    
    Weapons: prefab_id = CSV prefabID (1 for level 1)
    Armor: prefab_id = class_base (from CSV prefabID)
    Used for equipped items and NotifyItemUpdate.
    """
    if item_id >= 1000 and item_id < 2000:
        # Weapon - use CSV prefabID
        return WEAPON_LEVEL_1_PREFABID  # WPN01 for levels 1-6
    elif item_id >= 2000 and item_id < 3000:
        # Armor - use CSV prefabID based on class style
        base = ARMOR_CLASS_BASE.get(style, 401)  # Default to Heavy
        return base
    return 1

def get_inventory_prefab_id(item_id):
    """Calculate prefab ID for inventory icons (small sequential IDs).
    
    Inventory icons use small prefab IDs (like 1) to match _UI_CS_ItemPrefabs entries.
    """
    return 1

def handle_user_create_character(nickname, style, sex):
    """Handle UserCreateCharacter and send On_UserCreateCharacterOK with real DB storage."""
    global current_account_id
    print(f"Creating character: {nickname} (style={style}, sex={sex})")
    
    # Store character in database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if character name already exists for this account
        cursor.execute(
            "SELECT id FROM characters WHERE account_id = ? AND nickname = ?",
            (current_account_id, nickname)
        )
        existing = cursor.fetchone()
        if existing:
            print(f"Character name '{nickname}' already exists for account {current_account_id}")
            # Return eCreateCharacter_AlreadyNickName error (code 60)
            fail_body = PacketWriter()
            fail_body.write_int(60)  # EServerErrorType::eCreateCharacter_AlreadyNickName
            return make_game_packet(USER_CREATE_CHARACTER_FAILED, fail_body)
        
        cursor.execute(
            "INSERT INTO characters (account_id, nickname, style, sex) VALUES (?, ?, ?, ?)",
            (current_account_id, nickname, style, sex)
        )
        char_id = cursor.lastrowid
        
        # Initialize talent data for new character
        cursor.execute(
            "INSERT INTO talent (character_id, left_points) VALUES (?, 0)",
            (char_id,)
        )
        
        # Initialize well data
        cursor.execute(
            "INSERT INTO well_data (character_id) VALUES (?)",
            (char_id,)
        )
        
        # Give class-specific starting items
        starter_items = CLASS_STARTER_ITEMS.get(style, CLASS_STARTER_ITEMS[1])  # Default to Prowess if unknown style
        print(f"Starter items for style={style}: {starter_items}")
        
        for item_key, item_id in starter_items.items():
            slot = EQUIPMENT_SLOTS[item_key]
            cursor.execute(
                "INSERT INTO items (character_id, item_type, item_id, quantity, slot) VALUES (?, ?, ?, 1, ?)",
                (char_id, item_key, item_id, slot)
            )
        
        # Give starting gold to account
        cursor.execute(
            "UPDATE accounts SET gold = 500 WHERE id = ?",
            (current_account_id,)
        )
        
        conn.commit()
        print(f"Character saved to DB: id={char_id} with class-specific starter items")
    except Exception as e:
        print(f"Error saving character to DB: {e}")
        # Return generic error
        fail_body = PacketWriter()
        fail_body.write_int(1)  # EServerErrorType::eUnknownError
        return make_game_packet(USER_CREATE_CHARACTER_FAILED, fail_body)
    finally:
        conn.close()
    
    try:
        # Build SCharacterInfoLogin response
        char_info = PacketWriter()
        char_info.write_int(char_id)         # ID (real DB character ID)
        char_info.write_string(nickname)     # nickname
        char_info.write_int(0)               # badgeNum
        char_info.write_int(sex)             # sex (ESex serialized as int)
        char_info.write_int(style)           # style (class)
        char_info.write_int(1)               # level
        char_info.write_uint64(0)            # Exp (uint64)
        char_info.write_int(int(time.time()))  # creationTime (NatureTime = seconds since epoch)
        char_info.write_int(0)               # status
        
        # equipinfo: vectorSItemuuid [count][items]
        # Each itemuuid has 7 fields:
        # slotPart, itemID, itemLevel, gemID, elementID, enchantID, prefabID
        def write_item_uuid(slot_part, item_id, item_level=1, gem_id=0, element_id=0, enchant_id=0, prefab_id=0):
            char_info.write_int(slot_part)    # slotPart (equipment slot)
            char_info.write_int(item_id)      # itemID
            char_info.write_int(item_level)   # itemLevel
            char_info.write_int(gem_id)       # gemID
            char_info.write_int(element_id)   # elementID
            char_info.write_int(enchant_id)   # enchantID
            char_info.write_int(prefab_id)    # prefabID
        
        # Send equipment with correct prefab IDs from resources.assets analysis
        starter_items = CLASS_STARTER_ITEMS.get(style, CLASS_STARTER_ITEMS[1])
        equip_count = len(starter_items)
        char_info.write_int(equip_count)  # equipinfo count
        for item_key, item_id in starter_items.items():
            slot = EQUIPMENT_SLOTS[item_key]
            prefab_id = get_prefab_id(item_id, style)
            write_item_uuid(slot, item_id, prefab_id=prefab_id)
            print(f"  Equipment: {item_key} (item_id={item_id}, prefab_id={prefab_id}, slot={slot})")
        
        char_info.write_bool(True)           # isTutorial (new chars start tutorial)
        
        # attrVec: vectorAttrChange [count][changes] - empty for now
        char_info.write_int(0)  # count=0
        
        packet = make_game_packet(USER_CREATE_CHARACTER_OK, char_info)
        print(f"Created response packet, size={len(packet)}")
        return packet
    except Exception as e:
        print(f"Error building create character response: {e}")
        import traceback
        traceback.print_exc()
        # Return a minimal failure packet
        fail_body = PacketWriter()
        fail_body.write_int(1)  # error code
        return make_game_packet(USER_CREATE_CHARACTER_FAILED, fail_body)

def handle_user_select_character(character_id):
    """Handle UserSelectCharacter and send On_UserSelectCharacterOK + skill info."""
    global current_account_id, current_character_id
    print(f"UserSelectCharacter: character_id={character_id}")
    
    packets = []
    
    try:
        # Look up character in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nickname, style, sex, level, exp, status, is_tutorial, creation_time "
            "FROM characters WHERE id = ? AND account_id = ?",
            (character_id, current_account_id)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            print(f"Character {character_id} not found for account {current_account_id}")
            fail_body = PacketWriter()
            fail_body.write_int(1)  # error code
            packets.append(make_game_packet(USER_SELECT_CHARACTER_FAILED, fail_body))
            return packets
        
        char_id, nickname, style, sex, level, exp, status, is_tutorial, creation_time = row
        current_character_id = char_id
        print(f"Loading character: {nickname} (id={char_id})")
        
        # Build SCharacterInfoBasic response
        char_info = PacketWriter()
        char_info.write_int(char_id)         # ID
        char_info.write_string(nickname)     # nickname
        char_info.write_int(style)           # style
        char_info.write_int(level)           # level
        char_info.write_uint64(exp)          # exp (uint64)
        char_info.write_int(sex)             # sex (ESex as int)
        char_info.write_int(0)               # Badges
        char_info.write_uint(0)              # BadgeTime (uint32)
        char_info.write_int(10)              # Armor (mock base value)
        char_info.write_int(5)               # Harm (mock base value)
        char_info.write_int(2)               # Critical (mock base value)
        
        # creationTime - parse from DB string or use current time
        try:
            ct = int(time.mktime(time.strptime(creation_time, "%Y-%m-%d %H:%M:%S")))
        except:
            ct = int(time.time())
        char_info.write_int(ct)              # creationTime (NatureTime)
        
        char_info.write_bool(False)          # firstlogin (false for returning players)
        
        # eventData: mapEvent [count][key,value pairs] - empty
        char_info.write_int(0)  # count=0
        
        # cooldownData: mapTypeCooldown [count][key,value pairs] - empty
        char_info.write_int(0)  # count=0
        
        # Build On_UserSelectCharacterOK response
        body = PacketWriter()
        body.data.extend(char_info.get_bytes())
        
        # attrVec: vectorAttrChange [count][changes] - base stats for display on select screen
        attrs = [
            (0, 100),   # CurHP = 100
            (1, 50),    # CurMP = 50
            (2, 100),   # MaxHP = 100
            (3, 50),    # MaxMP = 50
            (4, 10),    # Power = 10
            (5, 5),     # Defense = 5
            (6, 5),     # Skill = 5
            (7, 8),     # PhyAtk = 8
            (8, 2),     # DamageReduction = 2
            (9, 1),     # Critical = 1
            (10, 1),    # HPRecover = 1
            (11, 1),    # MPRecover = 1
            (12, 300),  # MoveSpeed = 3.0 * 100 (scaled int)
            (13, 100),  # AttackSpeed = 1.0 * 100 (scaled int)
            (14, 150),  # CriticalDamage = 1.5 * 100 (scaled int)
        ]
        body.write_int(len(attrs))  # count
        for attr_type, value in attrs:
            body.write_int(attr_type)  # EAttributeType as int
            body.write_int(value)      # Always int
        
        print(f"Sent USER_SELECT_CHARACTER_OK with {len(attrs)} attrs for char {char_id}")
        
        packet = make_game_packet(USER_SELECT_CHARACTER_OK, body)
        packets.append(packet)
        print(f"Sent select character OK response, size={len(packet)}")
        
        # Send basic skill info for the character
        # SPlayerSkillInfo: shortcutGroupIdx (int), skillShortcutVec (vector), skillInfoVec (vector)
        skill_body = PacketWriter()
        skill_body.write_int(0)  # shortcutGroupIdx
        
        # skillShortcutVec: empty for now
        skill_body.write_int(0)  # count=0
        
        # skillInfoVec: basic skills for level 1 character
        # Include normal attack (skillID=10001) and a basic ability
        skill_body.write_int(2)  # count=2 skills
        
        # Skill 1: Normal Attack (always available)
        skill_body.write_int(10001)  # skillID
        skill_body.write_int(1)      # level
        skill_body.write_int(0)      # skillExp
        skill_body.write_int(0)      # coldTime
        
        # Skill 2: Basic ability (varies by class, using generic ID)
        skill_body.write_int(10101)  # skillID (basic attack ability)
        skill_body.write_int(1)      # level
        skill_body.write_int(0)      # skillExp
        skill_body.write_int(5000)   # coldTime (5 seconds)
        
        packets.append(make_game_packet(SEND_SKILL_INFO, skill_body))
        print("Sent basic skill info")
        
    except Exception as e:
        print(f"Error handling UserSelectCharacter: {e}")
        import traceback
        traceback.print_exc()
        fail_body = PacketWriter()
        fail_body.write_int(1)  # error code
        packets.append(make_game_packet(USER_SELECT_CHARACTER_FAILED, fail_body))
    
    return packets

def handle_enter_scene(map_name):
    """Handle EnterScene and send On_EnterSceneOk."""
    global current_map_name
    print(f"EnterScene: map={map_name}")
    
    try:
        # Store the map name for spawn position lookup
        current_map_name = map_name
        
        # Build On_EnterSceneOk response with the same map name
        body = PacketWriter()
        body.write_string(map_name)
        
        packet = make_game_packet(ENTER_SCENE_OK, body)
        print(f"Sent EnterSceneOK response for map={map_name}")
        return packet
    except Exception as e:
        print(f"Error handling EnterScene: {e}")
        import traceback
        traceback.print_exc()
        # Return empty OK on error to keep client moving
        body = PacketWriter()
        body.write_string(map_name)
        return make_game_packet(ENTER_SCENE_OK, body)

# Equipment slot mapping: database slot -> client equipment index
# Client uses: 0=helm, 1=necklace, 2=chest, 3=cloak, 4=ring, 6/7=weapons, 8=legs
# EQUIPMENT_SLOTS now stores CLIENT indices directly - no mapping needed



def build_bag_info():
    """Build SBagGroup response with character's items.
    
    Returns a SEND_BAG_INFO packet or None if no items found.
    Equipped items go in BOTH equipbag (for model rebuild) and basebag (for inventory).
    Unequipped items only go in basebag.
    """
    body = PacketWriter()
    
    def write_empty_bag(bag_id):
        body.write_byte(bag_id)
        body.write_uint(0)
        body.write_bool(False)
        body.write_int(0)
    
    # Get character style for correct prefab IDs
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        char_id = current_character_id if current_character_id else 1
        cursor.execute("SELECT style FROM characters WHERE id = ?", (char_id,))
        char_row = cursor.fetchone()
        char_style = char_row[0] if char_row else 1
        conn.close()
    except:
        char_style = 1
    
    def write_item(item_id, db_id=0, slot=0, enchant=0, element=0, gem=0, count=1):
        """Write SItemInfo structure with correct prefab IDs based on item type."""
        prefab_id = get_prefab_id(item_id, char_style)  # Use style-aware prefab ID
        body.write_int(item_id)       # ID
        body.write_int(prefab_id)     # perfrab
        body.write_uint(1)            # level
        body.write_ushort(0)          # ItemGuid.worldID
        body.write_ushort(0)          # ItemGuid.gameID
        body.write_int(db_id if db_id else item_id)  # ItemGuid.serialID
        body.write_int(enchant)       # enchant
        body.write_int(element)       # element
        body.write_int(gem)           # gem
        body.write_uint(slot)         # slot
        body.write_uint(count)        # count
        body.write_string("")         # property
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        char_id = current_character_id if current_character_id else 1
        
        cursor.execute(
            "SELECT id, item_type, item_id, quantity, slot FROM items WHERE character_id = ?",
            (char_id,)
        )
        all_items = cursor.fetchall()
        conn.close()
        
        print(f"Building bag info for char {char_id}: {len(all_items)} items")
        
        # Separate equipped vs unequipped items
        # Equipped items have slot 0-8 (equipment slots), unequipped have slot >= 100
        equipped_items = [item for item in all_items if item[4] < 100]
        unequipped_items = [item for item in all_items if item[4] >= 100]
        
        print(f"  Equipped: {len(equipped_items)}, Unequipped: {len(unequipped_items)}")
        
        # equipbag (bagID=0): Send equipped items so InitPlayerModelEquips() can rebuild model
        body.write_byte(0)
        body.write_uint(11)  # max equipment slots
        body.write_bool(False)
        body.write_int(len(equipped_items))
        for idx, item in enumerate(equipped_items):
            # item[4] is already the client equipment slot index (from EQUIPMENT_SLOTS)
            write_item(item[2], db_id=item[0], slot=item[4], count=item[3])
        
        # basebag (bagID=1): main inventory - send ALL items here
        body.write_byte(1)
        body.write_uint(20)  # inventory capacity
        body.write_bool(False)
        body.write_int(len(all_items))
        for idx, item in enumerate(all_items):
            write_item(item[2], db_id=item[0], slot=idx, count=item[3])
    except Exception as e:
        print(f"Error building bag info: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # bankbag (bagID=2), stashbag (bagID=3) - empty
    write_empty_bag(2)
    write_empty_bag(3)
    
    return make_game_packet(SEND_BAG_INFO, body)

def handle_map_load_ok():
    """Handle MapLoadOK and send CharacterStartInfo + spawn NPCs/monsters."""
    print(f"MapLoadOK received for map={current_map_name} - sending CharacterStartInfo")
    
    packets = []
    
    try:
        # Build SCharacterStartInfo
        char_start = PacketWriter()
        char_start.write_int(1001)  # objectID (player's unique ID in scene)
        
        # Spawn position based on current map
        spawn = SPAWN_POSITIONS.get(current_map_name, DEFAULT_SPAWN)
        print(f"Spawning at {spawn} for map {current_map_name}")
        char_start.write_float(spawn[0])   # x
        char_start.write_float(spawn[1])   # y
        char_start.write_float(spawn[2])   # z
        
        # attrVec: vectorAttrChange - basic attributes for a level 1 character
        attrs = [
            (0, 100),   # CurHP = 100
            (1, 50),    # CurMP = 50
            (2, 100),   # MaxHP = 100
            (3, 50),    # MaxMP = 50
            (4, 10),    # Power = 10
            (5, 5),     # Defense = 5
            (6, 5),     # Skill = 5
            (7, 8),     # PhyAtk = 8
            (8, 2),     # DamageReduction = 2
            (9, 1),     # Critical = 1
            (10, 1),    # HPRecover = 1
            (11, 1),    # MPRecover = 1
            (12, 300),  # MoveSpeed = 3.0 * 100 (scaled int)
            (13, 100),  # AttackSpeed = 1.0 * 100 (scaled int)
            (14, 150),  # CriticalDamage = 1.5 * 100 (scaled int)
        ]
        
        char_start.write_int(len(attrs))  # count
        for attr_type, value in attrs:
            char_start.write_int(attr_type)  # EAttributeType as int
            char_start.write_int(value)      # Always int
        
        packet = make_game_packet(CHARACTER_START_INFO, char_start)
        packets.append(packet)
        print(f"Sent CharacterStartInfo, size={len(packet)}")
        
        # Send money info (karma/FK) to client
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT karma FROM accounts WHERE id = ?", (current_account_id,))
            row = cursor.fetchone()
            karma = row[0] if row else 1000
            fk = 0  # FK not implemented yet
            
            # Also get character XP for ADD_EXP_NTF
            cursor.execute("SELECT exp FROM characters WHERE id = ?", (current_character_id,))
            char_row = cursor.fetchone()
            xp = char_row[0] if char_row else 0
            conn.close()
        except:
            karma = 1000
            fk = 0
            xp = 0
        
        money_body = PacketWriter()
        money_body.write_int(karma)   # Karma
        money_body.write_int(fk)      # FK
        packets.append(make_game_packet(UPDATE_MONEY_INFO, money_body))
        print(f"Sent money info: karma={karma}, fk={fk}")
        
        # Send XP update to client
        exp_body = PacketWriter()
        exp_body.write_int(1)         # catalog (1 = normal XP)
        exp_body.write_uint64(xp)     # current XP value
        packets.append(make_game_packet(ADD_EXP_NTF, exp_body))
        print(f"Sent XP update: xp={xp}")
        
        # Send bag info proactively (client never sends RequestBagInfo)
        bag_info = build_bag_info()
        if bag_info:
            packets.append(bag_info)
            print("Sent bag info proactively")
        
        # Spawn NPCs and monsters based on map
        if current_map_name == "Hub_Village_Tutorial":
            # Spawn tutorial NPC (MISSIONPC type = 1001) near spawn point
            # Bounty Master should be close to player but slightly offset to guide them
            npc_body = PacketWriter()
            npc_body.write_int(2001)      # objectID for NPC
            npc_body.write_int(1001)      # npcID = MISSIONPC (Bounty Master)
            npc_body.write_float(spawn[0] + 5.0)   # x (slightly right of player)
            npc_body.write_float(spawn[1])         # y
            npc_body.write_float(spawn[2] - 3.0)   # z (slightly in front of player)
            packets.append(make_game_packet(NPC_ENTER, npc_body))
            print("Spawned tutorial NPC (Bounty Master)")
            
            # Spawn wolf monster automatically when entering tutorial map
            # Position based on user-provided coordinates: (60.18, 7.81, 84.71)
            wolf_body = PacketWriter()
            wolf_body.write_int(3002)      # unique objectID for wolf
            wolf_body.write_int(3001)      # npcID = wolf monster
            wolf_body.write_float(60.18)   # x
            wolf_body.write_float(7.81)    # y
            wolf_body.write_float(84.71)   # z
            wolf_body.write_int(50)        # hp = 50
            wolf_body.write_int(100)       # moveSpeed = 100
            wolf_body.write_bool(True)     # bRayCast = true
            packets.append(make_game_packet(MONSTER_ENTER, wolf_body))
            print("Spawned tutorial wolf monster")
        
        elif current_map_name == "Hub_Village":
            # Spawn village NPCs: Mission NPC, Shop NPC, Mail NPC, Day Reward NPC
            # Positions based on typical hub village layout - vendors spread around the central area
            npc_positions = [
                (1001, spawn[0] + 15.0, spawn[2] + 10.0),   # MISSIONPC - center-right
                (1002, spawn[0] - 15.0, spawn[2] + 10.0),   # SHOPNPC - center-left
                (1003, spawn[0] + 10.0, spawn[2] - 10.0),   # SHOPNPC2 - south-right
                (1004, spawn[0] - 10.0, spawn[2] - 10.0),   # SHOPNPC3 - south-left
                (1005, spawn[0], spawn[2] + 20.0),          # MAILNPC - north center
                (1006, spawn[0] + 25.0, spawn[2]),          # DAYREWARDNPC - east
            ]
            
            for i, (npc_id, x, z) in enumerate(npc_positions):
                npc_body = PacketWriter()
                npc_body.write_int(2001 + i)    # unique objectID for each NPC
                npc_body.write_int(npc_id)      # npcID
                npc_body.write_float(x)
                npc_body.write_float(spawn[1])
                npc_body.write_float(z)
                packets.append(make_game_packet(NPC_ENTER, npc_body))
            print(f"Spawned {len(npc_positions)} village NPCs")
        
    except Exception as e:
        print(f"Error building CharacterStartInfo: {e}")
        import traceback
        traceback.print_exc()
    
    return packets

def handle_tutorial_enter_req(char_id):
    """Handle TutorialEnterReq and send TutorialEnterAck."""
    print(f"TutorialEnterReq: charID={char_id}")
    body = PacketWriter()
    body.write_int(char_id)   # charID
    body.write_int(0)         # returnCode (0=success)
    response = make_game_packet(TUTORIAL_ENTER_ACK, body)
    return response

def handle_accept_mission(npc_id, mission_id):
    """Handle AcceptMission and send AcceptMissionOk + MISSION_LIST_ACK."""
    print(f"AcceptMission: npcID={npc_id}, missionID={mission_id}")
    
    # Store mission in database
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO missions (character_id, mission_id, status) VALUES (?, ?, 'active')",
                (current_character_id, mission_id)
            )
            conn.commit()
        except Exception as e:
            print(f"Error storing mission: {e}")
        finally:
            conn.close()
    
    # Send AcceptMissionOk
    body = PacketWriter()
    body.write_int(1)  # returnCode=1 (success)
    response = make_game_packet(ACCEPT_MISSION_OK, body)
    
    # Also send MISSION_LIST_ACK with the newly accepted mission
    list_body = PacketWriter()
    list_body.write_int(1)  # count of missions
    
    # Build SAcceptMissionRelate for mission 5011
    list_body.write_int(mission_id)           # missionID
    list_body.write_int(0)                    # IsHaveCompleted (0=no)
    list_body.write_bool(True)                # IsHaveTriggered (true - mission is active)
    list_body.write_int(1)                    # star rating
    list_body.write_int(0)                    # lastPassTime
    list_body.write_int(2)                    # canAcceptMaxLvl
    
    list_response = make_game_packet(MISSION_LIST_ACK, list_body)
    
    # Send both responses
    return [response, list_response]

def handle_ping_request():
    """Handle PingRequest and send PingRequestAck."""
    print("Ping request")
    response = make_game_packet(PING_REQUEST_ACK, PacketWriter())
    return response

def handle_get_player_mail():
    """Handle GetPlayerMail and send empty mail list."""
    print("GetPlayerMail")
    
    # Check for actual mail in DB
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, sender, subject, body, read FROM mail WHERE character_id = ?",
                (current_character_id,)
            )
            rows = cursor.fetchall()
            
            body = PacketWriter()
            body.write_int(len(rows))  # count
            
            for row in rows:
                mail_id, sender, subject, mail_body, read = row
                body.write_int(mail_id)
                body.write_string(sender)
                body.write_string(subject)
                body.write_string(mail_body)
                body.write_bool(bool(read))
            
            conn.close()
            return make_game_packet(GET_PLAYER_MAIL_RESULT, body)
        except Exception as e:
            print(f"Error getting mail: {e}")
            conn.close()
    
    # Default: empty list
    body = PacketWriter()
    body.write_int(0)  # count=0 (empty mail list)
    response = make_game_packet(GET_PLAYER_MAIL_RESULT, body)
    return response

def handle_request_day_reward():
    """Handle RequestDayReward and send success with reward status data."""
    print("RequestDayReward")
    
    # Send day reward status: 4 days, first 2 claimed (1), last 2 not claimed (0)
    body = PacketWriter()
    body.write_int(0)           # dayID
    body.write_long(int(time.time()))  # daytime
    body.write_int(0)           # returnCode (eSuccess)
    
    # dayRewardStatusVec: vector of ints indicating claim status
    # Each int represents one day's reward status (1=claimed, 0=not claimed)
    body.write_int(4)           # count=4 days
    body.write_int(1)           # Day 1: claimed
    body.write_int(1)           # Day 2: claimed
    body.write_int(0)           # Day 3: not claimed (available)
    body.write_int(0)           # Day 4: not claimed (available)
    
    response = make_game_packet(REQUEST_DAY_REWARD_OK, body)
    return response

def handle_get_friend_reward():
    """Handle GetFriendReward and send empty map."""
    print("GetFriendReward")
    
    body = PacketWriter()
    body.write_int(0)  # count=0 (empty map)
    
    response = make_game_packet(0x68f84591, body)  # SendFriendRewardInfo
    return response

def handle_has_assigned_talent_point_req():
    """Handle HasAssignedTalentPointReq and send zeros for new character."""
    print("HasAssignedTalentPointReq")
    
    # Check DB for talent data
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT prowess, fortitude, cunning, left_points FROM talent WHERE character_id = ?",
                (current_character_id,)
            )
            row = cursor.fetchone()
            
            if row:
                body = PacketWriter()
                body.write_int(row[0])  # prowess
                body.write_int(row[1])  # fortitude
                body.write_int(row[2])  # cunning
                body.write_int(row[3])  # left_points
                conn.close()
                return make_game_packet(HAS_ASSIGNED_TALENT_POINT_ACK, body)
        except Exception as e:
            print(f"Error getting talent data: {e}")
        finally:
            conn.close()
    
    # Default: zeros for new character
    body = PacketWriter()
    body.write_int(0)  # prowess
    body.write_int(0)  # fortitude
    body.write_int(0)  # cunning
    body.write_int(0)  # left_points
    
    response = make_game_packet(HAS_ASSIGNED_TALENT_POINT_ACK, body)
    return response

# New handlers for complete implementation

def handle_buy_char_slot_request():
    """Handle BuyCharSlotRequest - allow buying additional character slots."""
    print("BuyCharSlotRequest")
    
    body = PacketWriter()
    body.write_int(1)  # success
    
    response = make_game_packet(BUY_CHAR_SLOT_RESULT, body)
    return response

def handle_buy_consume_item(item_id, quantity):
    """Handle BuyConsumeItem - buy consumable items."""
    print(f"BuyConsumeItem: item={item_id}, qty={quantity}")
    
    # Add item to inventory (mock)
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO items (character_id, item_type, item_id, quantity) VALUES (?, 'consumable', ?, ?)",
                (current_character_id, item_id, quantity)
            )
            conn.commit()
        except Exception as e:
            print(f"Error adding consumable item: {e}")
        finally:
            conn.close()
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(BUY_CONSUME_ITEM_SUCC_ACK, body)
    return response

def handle_buy_item(item_id):
    """Handle BuyItem - buy equipment items."""
    print(f"BuyItem: item={item_id}")
    
    # Add item to inventory (mock)
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO items (character_id, item_type, item_id, quantity) VALUES (?, 'equipment', ?, 1)",
                (current_character_id, item_id)
            )
            conn.commit()
        except Exception as e:
            print(f"Error adding equipment item: {e}")
        finally:
            conn.close()
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(BUY_ITEM_SUCC_ACK, body)
    return response

def handle_buy_pet(pet_id):
    """Handle BuyPet - buy a pet."""
    print(f"BuyPet: pet={pet_id}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO pets (character_id, pet_type) VALUES (?, 'basic')",
                (current_character_id,)
            )
            conn.commit()
        except Exception as e:
            print(f"Error adding pet: {e}")
        finally:
            conn.close()
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(BUY_PET_ACK, body)
    return response

def handle_change_gender_req(gender):
    """Handle ChangeGenderReq."""
    print(f"ChangeGenderReq: gender={gender}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE characters SET sex = ? WHERE id = ?",
                (gender, current_character_id)
            )
            conn.commit()
        except Exception as e:
            print(f"Error changing gender: {e}")
        finally:
            conn.close()
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(CHANGE_GENDER_RESULT, body)
    return response

def handle_change_name_req(name):
    """Handle ChangeNameReq."""
    print(f"ChangeNameReq: name={name}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE characters SET nickname = ? WHERE id = ?",
                (name, current_character_id)
            )
            conn.commit()
        except Exception as e:
            print(f"Error changing name: {e}")
        finally:
            conn.close()
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(CHANGE_NAME_RESULT, body)
    return response

def handle_chat_request(channel, message):
    """Handle ChatRequest."""
    print(f"ChatRequest: channel={channel}, msg={message}")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(CHAT_REQUEST_ACK, body)
    return response

def handle_crafting_item(recipe_id):
    """Handle CraftingItem."""
    print(f"CraftingItem: recipe={recipe_id}")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(CRAFTING_ITEM_OK, body)
    return response

def handle_del_item(item_uuid):
    """Handle DelItem."""
    print(f"DelItem: uuid={item_uuid}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM items WHERE character_id = ? AND id = ?",
                (current_character_id, item_uuid)
            )
            conn.commit()
        except Exception as e:
            print(f"Error deleting item: {e}")
        finally:
            conn.close()
    
    # No response needed for DelItem
    
def handle_delete_mail(mail_id):
    """Handle DeleteMail."""
    print(f"DeleteMail: id={mail_id}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM mail WHERE character_id = ? AND id = ?",
                (current_character_id, mail_id)
            )
            conn.commit()
        except Exception as e:
            print(f"Error deleting mail: {e}")
        finally:
            conn.close()
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(DELETE_MAIL_RESULT, body)
    return response

# NotifyItemUpdate method ID (server pushes this to client when items change)
NOTIFY_ITEM_UPDATE = 0xa69ab9f

# Equipment slot mapping for client display
# Client uses different indices than our database slots
CLIENT_EQUIP_SLOTS = {
    0: 'helm',       # Head
    1: 'necklace',   # Neck
    2: 'chest',      # Chest
    3: 'cloak',      # Cloak (NOT legs!)
    4: 'ring',       # Ring
    6: 'weapon_1h',  # One-handed weapon (main hand)
    7: 'weapon_2h',  # Two-handed weapon
    8: 'legs',       # Legs/Breeches (NOT cloak!)
}

# Map from client part index to valid item types that can go in that slot
# Based on actual client behavior observed during testing:
CLIENT_PART_TO_ITEM_TYPES = {
    0: ['helm'],           # Slot 0 - Helm (client sends part=0 for helm items)
    1: ['necklace'],       # Slot 1 - Necklace (client sends part=1 for necklace items)
    2: ['breastplate'],    # Slot 2 - Chest/Breastplate
    3: ['cloak'],          # Slot 3 - Cloak (client index 3 = cloak, NOT legs!)
    4: ['ring'],           # Slot 4 - Ring
    6: ['weapon'],         # Slot 6 - Weapon (1h/2h)
    7: ['weapon'],         # Slot 7 - Two-handed weapon
    8: ['breeches'],       # Slot 8 - Legs/Breeches (client index 8 = legs, NOT cloak!)
}

def handle_equip_item(part, bag_id, slot):
    """Handle EquipItem - equip item to character.
    
    In Akaneiro, equipped items STAY in inventory but are marked as equipped.
    The client tracks what's equipped separately from the inventory list.
    We do NOT change the item's database slot when equipping.
    
    Args:
        part: Equipment slot index (0-8 for various slots)
        bag_id: Source bag ID (2 = inventory/basebag)
        slot: Slot number in source bag (inventory position 0,1,2,3...)
    
    Returns:
        List of packets to send back to client
    """
    print(f"EquipItem: part={part}, bagID={bag_id}, slot={slot}")
    packets = []
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # Get character style for prefab ID calculation
            cursor.execute("SELECT style FROM characters WHERE id = ?", (current_character_id,))
            char_row = cursor.fetchone()
            char_style = char_row[0] if char_row else 1
            
            # Get all items for this character ordered by their inventory position
            # Items stay at their original inventory slots (0,1,2,3...).
            # We do NOT change the slot when equipping.
            cursor.execute(
                "SELECT id, item_type, item_id, quantity, slot FROM items WHERE character_id = ? ORDER BY slot ASC",
                (current_character_id,)
            )
            all_items = cursor.fetchall()
            
            print(f"Total items in inventory: {len(all_items)}")
            for i, item in enumerate(all_items):
                print(f"  Inventory pos {i}: db_id={item[0]}, type={item[1]}, id={item[2]}, slot={item[4]}")
            
            # Validate that the requested part index is valid
            if part not in CLIENT_PART_TO_ITEM_TYPES:
                print(f"Invalid equipment slot part={part}")
                return packets
            
            # Get allowed item types for this slot
            allowed_types = CLIENT_PART_TO_ITEM_TYPES[part]
            print(f"Slot {part} allows: {allowed_types}")
            
            if slot < len(all_items):
                # Find the item at inventory position 'slot'
                item_db_id, item_type, item_id, quantity, original_slot = all_items[slot]
                print(f"Item at pos {slot}: db_id={item_db_id}, type={item_type}, id={item_id}")
                
                # Validate that this item type can go in the requested slot
                if item_type not in allowed_types:
                    print(f"ERROR: Item type '{item_type}' cannot equip to slot {part} (allowed: {allowed_types})")
                    return packets
                
                print(f"Equipping item {item_db_id} ({item_type}, id={item_id}) to equipment slot {part}")
                
                # Send full bag info update so client rebuilds character model with equipped items
                # This triggers InitPlayerModelEquips() on the NGUI path which attaches 3D models
                bag_info = build_bag_info()
                if bag_info:
                    packets.append(bag_info)
                    print(f"Sent full bag info after equip")
            else:
                print(f"Inventory position {slot} out of range ({len(all_items)} items total)")
        except Exception as e:
            print(f"Error equipping item: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()
    
    return packets
    
def handle_get_day_reward(day_id):
    """Handle GetDayReward."""
    print(f"GetDayReward: day={day_id}")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    body.write_int(0)  # reward count (empty)
    
    response = make_game_packet(GET_DAY_REWARD_RESULT, body)
    return response

def handle_get_gift_req(gift_id):
    """Handle GetGiftReq."""
    print(f"GetGiftReq: gift={gift_id}")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(GET_GIFT_ACK, body)
    return response

def handle_get_leaderboard_info():
    """Handle GetLeaderboardInfo."""
    print("GetLeaderboardInfo")
    
    body = PacketWriter()
    body.write_int(0)  # count=0 (empty leaderboard)
    
    response = make_game_packet(UPDATE_LEADERBOARD_INFO, body)
    return response

def handle_get_mail_all():
    """Handle GetMailAll."""
    print("GetMailAll")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, sender, subject, body, read FROM mail WHERE character_id = ?",
                (current_character_id,)
            )
            rows = cursor.fetchall()
            
            body = PacketWriter()
            body.write_int(len(rows))  # count
            
            for row in rows:
                mail_id, sender, subject, mail_body, read = row
                body.write_int(mail_id)
                body.write_string(sender)
                body.write_string(subject)
                body.write_string(mail_body)
                body.write_bool(bool(read))
            
            conn.close()
            return make_game_packet(GET_MAIL_ALL_RESULT, body)
        except Exception as e:
            print(f"Error getting all mail: {e}")
            conn.close()
    
    # Default: empty list
    body = PacketWriter()
    body.write_int(0)  # count=0
    
    response = make_game_packet(GET_MAIL_ALL_RESULT, body)
    return response

def handle_get_mail_item(mail_id):
    """Handle GetMailItem."""
    print(f"GetMailItem: mail={mail_id}")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(GET_MAIL_ITEM_RESULT, body)
    return response

def handle_get_mail_pet(mail_id):
    """Handle GetMailPet."""
    print(f"GetMailPet: mail={mail_id}")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(GET_MAIL_PET_RESULT, body)
    return response

def handle_get_redeem_gift(code):
    """Handle GetRedeemGift."""
    print(f"GetRedeemGift: code={code}")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(GET_REDEEM_GIFT_RESULT, body)
    return response

def handle_get_well_data():
    """Handle GetWellData."""
    print("GetWellData")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT speed_level, time_level, lid_level, begin_time FROM well_data WHERE character_id = ?",
                (current_character_id,)
            )
            row = cursor.fetchone()
            
            if row:
                body = PacketWriter()
                body.write_int(row[0])  # speed_level
                body.write_int(row[1])  # time_level
                body.write_int(row[2])  # lid_level
                body.write_long(row[3])  # begin_time
                conn.close()
                return make_game_packet(GET_WELL_DATA_RESULT, body)
        except Exception as e:
            print(f"Error getting well data: {e}")
        finally:
            conn.close()
    
    # Default values
    body = PacketWriter()
    body.write_int(1)  # speed_level
    body.write_int(1)  # time_level
    body.write_int(1)  # lid_level
    body.write_long(0)  # begin_time
    
    response = make_game_packet(GET_WELL_DATA_RESULT, body)
    return response

def handle_leave_world():
    """Handle LeaveWorld."""
    print("LeaveWorld")
    
    # No specific response needed
    
def handle_mission_fail_req(mission_id):
    """Handle MissionFailReq."""
    print(f"MissionFailReq: mission={mission_id}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE missions SET status = 'failed' WHERE character_id = ? AND mission_id = ?",
                (current_character_id, mission_id)
            )
            conn.commit()
        except Exception as e:
            print(f"Error updating mission status: {e}")
        finally:
            conn.close()
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(MISSION_FAIL_ACK, body)
    return response

def handle_mission_list_req():
    """Handle MissionListReq and send MISSION_LIST_ACK with mission data."""
    print("MissionListReq")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # Get all missions for this character
            cursor.execute(
                "SELECT mission_id, status, progress FROM missions WHERE character_id = ?",
                (current_character_id,)
            )
            rows = cursor.fetchall()
            
            body = PacketWriter()
            body.write_int(len(rows))  # count of missions
            
            for row in rows:
                mission_id = row[0]
                status = row[1]  # 'active', 'completed', etc.
                progress = row[2]
                
                # Build SAcceptMissionRelate structure:
                body.write_int(mission_id)           # missionID
                body.write_int(0 if status == 'active' else 1)  # IsHaveCompleted (0=no, 1=yes)
                body.write_bool(status == 'active')  # IsHaveTriggered (true if active)
                body.write_int(1)                    # star (default 1 for tutorial)
                body.write_int(0)                    # lastPassTime
                body.write_int(2)                    # canAcceptMaxLvl
            
            conn.close()
            return make_game_packet(MISSION_LIST_ACK, body)
        except Exception as e:
            print(f"Error getting mission list: {e}")
            import traceback
            traceback.print_exc()
            conn.close()
    
    # Default: empty list
    body = PacketWriter()
    body.write_int(0)  # count=0
    
    response = make_game_packet(MISSION_LIST_ACK, body)
    return response

def handle_mission_process_req(mission_id):
    """Handle MissionProcessReq."""
    print(f"MissionProcessReq: mission={mission_id}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # Increment progress
            cursor.execute(
                "UPDATE missions SET progress = progress + 1 WHERE character_id = ? AND mission_id = ?",
                (current_character_id, mission_id)
            )
            
            # Check if completed
            cursor.execute(
                "SELECT progress FROM missions WHERE character_id = ? AND mission_id = ?",
                (current_character_id, mission_id)
            )
            row = cursor.fetchone()
            
            if row and row[0] >= 10:  # Arbitrary completion threshold
                cursor.execute(
                    "UPDATE missions SET status = 'completed' WHERE character_id = ? AND mission_id = ?",
                    (current_character_id, mission_id)
                )
            
            conn.commit()
        except Exception as e:
            print(f"Error updating mission progress: {e}")
        finally:
            conn.close()
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(SEND_MISSION_PROCESS, body)
    return response

def handle_open_mail(mail_id):
    """Handle OpenMail."""
    print(f"OpenMail: id={mail_id}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE mail SET read = 1 WHERE character_id = ? AND id = ?",
                (current_character_id, mail_id)
            )
            conn.commit()
        except Exception as e:
            print(f"Error marking mail as read: {e}")
        finally:
            conn.close()
    
    # No specific response needed
    
def handle_process_friend_reward():
    """Handle ProcessFriendReward."""
    print("ProcessFriendReward")
    
    # No specific response needed
    
def handle_process_redeem_gift(code):
    """Handle ProcessRedeemGift."""
    print(f"ProcessRedeemGift: code={code}")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(PROCESS_REDEEM_GIFT_RESULT, body)
    return response

def handle_request_bag_info():
    """Handle RequestBagInfo - send full SBagGroup with character's actual inventory.
    
    Note: Client never sends this request, but we keep the handler for completeness.
    Bag info is now sent proactively in handle_map_load_ok().
    """
    print("RequestBagInfo (fallback - bag info should have been sent proactively)")
    return build_bag_info()


def handle_request_player_consume_shop_info():
    """Handle RequestPlayerConsumeShopInfo."""
    print("RequestPlayerConsumeShopInfo")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT item_id, price FROM shop_items WHERE item_type IN ('potion_hp', 'potion_mp')"
        )
        rows = cursor.fetchall()
        
        body = PacketWriter()
        body.write_int(len(rows))  # count
        
        for row in rows:
            body.write_int(row[0])  # item_id
            body.write_int(row[1])  # price
        
        conn.close()
        return make_game_packet(SEND_SHOP_CONSUME_ITEMINFO, body)
    except Exception as e:
        print(f"Error getting consume shop info: {e}")
        conn.close()
    
    # Default: empty list
    body = PacketWriter()
    body.write_int(0)  # count=0
    
    response = make_game_packet(SEND_SHOP_CONSUME_ITEMINFO, body)
    return response

def handle_request_player_shop_info():
    """Handle RequestPlayerShopInfo."""
    print("RequestPlayerShopInfo")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT item_id, price FROM shop_items WHERE item_type IN ('weapon', 'armor', 'accessory')"
        )
        rows = cursor.fetchall()
        
        body = PacketWriter()
        body.write_int(len(rows))  # count
        
        for row in rows:
            body.write_int(row[0])  # item_id
            body.write_int(row[1])  # price
        
        conn.close()
        return make_game_packet(SEND_SHOP_ITEMINFO, body)
    except Exception as e:
        print(f"Error getting shop info: {e}")
        conn.close()
    
    # Default: empty list
    body = PacketWriter()
    body.write_int(0)  # count=0
    
    response = make_game_packet(SEND_SHOP_ITEMINFO, body)
    return response

def handle_role_mastery_list_req():
    """Handle RoleMasteryListReq."""
    print("RoleMasteryListReq")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT mastery_type, level FROM mastery WHERE character_id = ?",
                (current_character_id,)
            )
            rows = cursor.fetchall()
            
            body = PacketWriter()
            body.write_int(len(rows))  # count
            
            for row in rows:
                body.write_string(row[0])  # mastery_type
                body.write_int(row[1])  # level
            
            conn.close()
            return make_game_packet(ROLE_MASTERY_LIST_ACK, body)
        except Exception as e:
            print(f"Error getting mastery list: {e}")
            conn.close()
    
    # Default: empty list
    body = PacketWriter()
    body.write_int(0)  # count=0
    
    response = make_game_packet(ROLE_MASTERY_LIST_ACK, body)
    return response

def handle_role_pet_list_req():
    """Handle RolePetListReq."""
    print("RolePetListReq")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, pet_type, level FROM pets WHERE character_id = ?",
                (current_character_id,)
            )
            rows = cursor.fetchall()
            
            body = PacketWriter()
            body.write_int(len(rows))  # count
            
            for row in rows:
                body.write_int(row[0])  # pet id
                body.write_string(row[1])  # pet_type
                body.write_int(row[2])  # level
            
            conn.close()
            return make_game_packet(ROLE_PET_LIST_ACK, body)
        except Exception as e:
            print(f"Error getting pet list: {e}")
            conn.close()
    
    # Default: empty list
    body = PacketWriter()
    body.write_int(0)  # count=0
    
    response = make_game_packet(ROLE_PET_LIST_ACK, body)
    return response

def handle_sale_item(item_uuid):
    """Handle SaleItem."""
    print(f"SaleItem: uuid={item_uuid}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM items WHERE character_id = ? AND id = ?",
                (current_character_id, item_uuid)
            )
            conn.commit()
        except Exception as e:
            print(f"Error selling item: {e}")
        finally:
            conn.close()
    
    # No specific response needed
    
def handle_send_mail(to_char_id, subject, body_text):
    """Handle SendMail."""
    print(f"SendMail: to={to_char_id}, subject={subject}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO mail (character_id, sender, subject, body) VALUES (?, ?, ?, ?)",
                (to_char_id, f"Player{current_account_id}", subject, body_text)
            )
            conn.commit()
        except Exception as e:
            print(f"Error sending mail: {e}")
        finally:
            conn.close()
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(SEND_MAIL_RESULT, body)
    return response

def handle_speed_up_cool_down(cooldown_type):
    """Handle SpeedUpCoolDown."""
    print(f"SpeedUpCoolDown: type={cooldown_type}")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(SPEED_UP_COOL_DOWN_RESULT, body)
    return response

def handle_split_item(item_uuid, quantity):
    """Handle SplitItem."""
    print(f"SplitItem: uuid={item_uuid}, qty={quantity}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # Get original item
            cursor.execute(
                "SELECT quantity FROM items WHERE character_id = ? AND id = ?",
                (current_character_id, item_uuid)
            )
            row = cursor.fetchone()
            
            if row and row[0] > quantity:
                # Reduce original
                cursor.execute(
                    "UPDATE items SET quantity = quantity - ? WHERE character_id = ? AND id = ?",
                    (quantity, current_character_id, item_uuid)
                )
                
                # Create new stack
                cursor.execute(
                    "INSERT INTO items (character_id, item_type, item_id, quantity) VALUES (?, 'consumable', 0, ?)",
                    (current_character_id, quantity)
                )
            
            conn.commit()
        except Exception as e:
            print(f"Error splitting item: {e}")
        finally:
            conn.close()
    
    # No specific response needed
    
def handle_study_ability(ability_id):
    """Handle StudyAbility."""
    print(f"StudyAbility: ability={ability_id}")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(STUDY_ABILITY_SUCCEED, body)
    return response

def handle_swap_item(item_uuid1, item_uuid2):
    """Handle SwapItem."""
    print(f"SwapItem: uuid1={item_uuid1}, uuid2={item_uuid2}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # Get slots
            cursor.execute(
                "SELECT slot FROM items WHERE character_id = ? AND id = ?",
                (current_character_id, item_uuid1)
            )
            row1 = cursor.fetchone()
            
            cursor.execute(
                "SELECT slot FROM items WHERE character_id = ? AND id = ?",
                (current_character_id, item_uuid2)
            )
            row2 = cursor.fetchone()
            
            if row1 and row2:
                # Swap slots
                cursor.execute(
                    "UPDATE items SET slot = ? WHERE character_id = ? AND id = ?",
                    (row2[0], current_character_id, item_uuid1)
                )
                cursor.execute(
                    "UPDATE items SET slot = ? WHERE character_id = ? AND id = ?",
                    (row1[0], current_character_id, item_uuid2)
                )
            
            conn.commit()
        except Exception as e:
            print(f"Error swapping items: {e}")
        finally:
            conn.close()
    
    # No specific response needed
    
def handle_unequip_item(slot):
    """Handle UnequipItem."""
    print(f"UnequipItem: slot={slot}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE items SET slot = -1 WHERE character_id = ? AND slot = ?",
                (current_character_id, slot)
            )
            conn.commit()
        except Exception as e:
            print(f"Error unequipping item: {e}")
        finally:
            conn.close()
    
    # No specific response needed
    
def handle_upgrade_well(well_type):
    """Handle UpgradeWell."""
    print(f"UpgradeWell: type={well_type}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            if well_type == 0:  # speed
                cursor.execute(
                    "UPDATE well_data SET speed_level = speed_level + 1 WHERE character_id = ?",
                    (current_character_id,)
                )
            elif well_type == 1:  # time
                cursor.execute(
                    "UPDATE well_data SET time_level = time_level + 1 WHERE character_id = ?",
                    (current_character_id,)
                )
            elif well_type == 2:  # lid
                cursor.execute(
                    "UPDATE well_data SET lid_level = lid_level + 1 WHERE character_id = ?",
                    (current_character_id,)
                )
            
            conn.commit()
        except Exception as e:
            print(f"Error upgrading well: {e}")
        finally:
            conn.close()
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(UPGRADE_WELL_RESULT, body)
    return response

def handle_user_del_character(character_id):
    """Handle UserDelCharacter - delete character and associated data."""
    print(f"UserDelCharacter: id={character_id}")
    
    success = False
    if current_account_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # First, delete all items associated with this character
            cursor.execute(
                "DELETE FROM items WHERE character_id = ?",
                (character_id,)
            )
            deleted_items = cursor.rowcount
            print(f"Deleted {deleted_items} items for character {character_id}")
            
            # Delete talent data
            cursor.execute(
                "DELETE FROM talent WHERE character_id = ?",
                (character_id,)
            )
            
            # Delete well data
            cursor.execute(
                "DELETE FROM well_data WHERE character_id = ?",
                (character_id,)
            )
            
            # Finally delete the character itself
            cursor.execute(
                "DELETE FROM characters WHERE account_id = ? AND id = ?",
                (current_account_id, character_id)
            )
            deleted_rows = cursor.rowcount
            
            if deleted_rows > 0:
                success = True
                print(f"Character {character_id} and all associated data deleted successfully")
            else:
                print(f"Character {character_id} not found for account {current_account_id}")
            
            conn.commit()
        except Exception as e:
            print(f"Error deleting character: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    # Build On_UserDelCharacterResult(characterID, error)
    body = PacketWriter()
    body.write_int(character_id)  # characterID
    if success:
        body.write_int(0)  # EServerErrorType::eGS_NoError (success)
    else:
        body.write_int(1)  # EServerErrorType::eUnknownError (failure)
    
    response = make_game_packet(USER_DEL_CHARACTER_RESULT, body)
    return response

def handle_user_logout():
    """Handle UserLogout."""
    print("UserLogout")
    
    # No specific response needed
    
def handle_assign_talent_req(prowess, fortitude, cunning):
    """Handle assignTalentReq."""
    print(f"assignTalentReq: prowess={prowess}, fortitude={fortitude}, cunning={cunning}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE talent SET prowess = ?, fortitude = ?, cunning = ? WHERE character_id = ?",
                (prowess, fortitude, cunning, current_character_id)
            )
            conn.commit()
        except Exception as e:
            print(f"Error assigning talent: {e}")
        finally:
            conn.close()
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(ASSIGN_TALENT_ACK, body)
    return response

def handle_buy_all_area_by_karma_req():
    """Handle buyAllAreaByKarmaReq."""
    print("buyAllAreaByKarmaReq")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(BUY_ALL_AREA_BY_KARMA_ACK, body)
    return response

def handle_buy_stash():
    """Handle buyStash."""
    print("buyStash")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(BUY_STASH_ACK, body)
    return response

def handle_buy_threat_level_by_karma():
    """Handle buyThreatLevelByKarma."""
    print("buyThreatLevelByKarma")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(BUY_THREAT_LEVEL_BY_KARMA_ACK, body)
    return response

def handle_choose_pet(pet_id):
    """Handle choosePet."""
    print(f"choosePet: pet={pet_id}")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(CHOOSE_PET_ACK, body)
    return response

def handle_conversation_npc_check_req(npc_id):
    """Handle conversationNpcCheckReq."""
    print(f"conversationNpcCheckReq: npc={npc_id}")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(CONVERSATION_NPC_CHECK_ACK, body)
    return response

def handle_decrease_cool_down(cooldown_type):
    """Handle decreaseCoolDown."""
    print(f"decreaseCoolDown: type={cooldown_type}")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(DECREASE_COOL_DOWN_ACK, body)
    return response

def handle_exploretaskcomplete_req(task_id):
    """Handle exploretaskcompleteReq."""
    print(f"exploretaskcompleteReq: task={task_id}")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(EXPLORETASKCOMPLETE_ACK, body)
    return response

def handle_mastery_lvlup_req(mastery_type):
    """Handle masteryLvlupReq."""
    print(f"masteryLvlupReq: type={mastery_type}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # Check if mastery exists
            cursor.execute(
                "SELECT id FROM mastery WHERE character_id = ? AND mastery_type = ?",
                (current_character_id, mastery_type)
            )
            row = cursor.fetchone()
            
            if row:
                cursor.execute(
                    "UPDATE mastery SET level = level + 1 WHERE character_id = ? AND mastery_type = ?",
                    (current_character_id, mastery_type)
                )
            else:
                cursor.execute(
                    "INSERT INTO mastery (character_id, mastery_type, level) VALUES (?, ?, 2)",
                    (current_character_id, mastery_type)
                )
            
            conn.commit()
        except Exception as e:
            print(f"Error leveling up mastery: {e}")
        finally:
            conn.close()
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(MASTERY_LVLUP_ACK, body)
    return response

def handle_protecttaskbegin_req(task_id):
    """Handle protecttaskBeginReq."""
    print(f"protecttaskBeginReq: task={task_id}")
    
    # No specific response needed
    
def handle_protecttaskend_req(task_id):
    """Handle protecttaskEndReq."""
    print(f"protecttaskEndReq: task={task_id}")
    
    # No specific response needed
    
def handle_role_attrib_req():
    """Handle roleAttribReq."""
    print("roleAttribReq")
    
    # Send back character attributes (mock)
    body = PacketWriter()
    body.write_int(100)  # hp
    body.write_int(50)   # mp
    body.write_int(10)   # power
    body.write_int(5)    # defense
    
    response = make_game_packet(ROLE_ATTRIB_REQ, body)
    return response

def handle_unlock_area_req(area_id):
    """Handle unLockAreaReq."""
    print(f"unLockAreaReq: area={area_id}")
    
    body = PacketWriter()
    body.write_int(0)  # success code
    
    response = make_game_packet(UNLOCK_AREA_ACK, body)
    return response

def handle_use_item(item_uuid):
    """Handle useItem."""
    print(f"useItem: uuid={item_uuid}")
    
    if current_character_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # Get item quantity
            cursor.execute(
                "SELECT quantity FROM items WHERE character_id = ? AND id = ?",
                (current_character_id, item_uuid)
            )
            row = cursor.fetchone()
            
            if row and row[0] > 1:
                cursor.execute(
                    "UPDATE items SET quantity = quantity - 1 WHERE character_id = ? AND id = ?",
                    (current_character_id, item_uuid)
                )
            else:
                cursor.execute(
                    "DELETE FROM items WHERE character_id = ? AND id = ?",
                    (current_character_id, item_uuid)
                )
            
            conn.commit()
        except Exception as e:
            print(f"Error using item: {e}")
        finally:
            conn.close()
    
    # No specific response needed

def parse_user_login(body):
    """Parse UserLogin request payload."""
    offset = 0
    
    # Read account string: [4 bytes length][bytes]
    if offset + 4 > len(body):
        return None
    acc_len = struct.unpack_from('<i', body, offset)[0]
    offset += 4
    if offset + acc_len > len(body):
        return None
    account = body[offset:offset+acc_len].decode('utf-8')
    offset += acc_len
    
    # Read userType (int)
    if offset + 4 > len(body):
        return None
    user_type = struct.unpack_from('<i', body, offset)[0]
    offset += 4
    
    # Read clientType (int)
    if offset + 4 > len(body):
        return None
    client_type = struct.unpack_from('<i', body, offset)[0]
    offset += 4
    
    # Read password string
    if offset + 4 > len(body):
        return None
    pwd_len = struct.unpack_from('<i', body, offset)[0]
    offset += 4
    if offset + pwd_len > len(body):
        return None
    password = body[offset:offset+pwd_len].decode('utf-8')
    offset += pwd_len
    
    # Read token string
    if offset + 4 > len(body):
        return None
    tok_len = struct.unpack_from('<i', body, offset)[0]
    offset += 4
    if offset + tok_len > len(body):
        return None
    token = body[offset:offset+tok_len].decode('utf-8')
    
    return {
        'account': account,
        'user_type': user_type,
        'client_type': client_type,
        'password': password,
        'token': token
    }

def handle_client(conn, addr):
    """Handle a single client connection."""
    print(f"Client connected: {addr}")
    
    buffer = bytearray()
    
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            
            buffer.extend(data)
            
            # Process complete packets from buffer
            while len(buffer) >= 6:
                # Read body size and message type
                body_size, msg_type = struct.unpack_from('<ih', bytes(buffer), 0)
                
                if len(buffer) < 6 + body_size:
                    break  # Wait for more data
                
                packet_body = buffer[6:6+body_size]
                buffer = buffer[6+body_size:]
                
                if msg_type == 1:  # ePacketHeartBeatPing
                    print(f"Heartbeat ping from {addr}")
                    conn.sendall(make_heartbeat_pong())
                    
                elif msg_type == 0:  # ePacketGameLogic
                    # Parse method ID
                    if len(packet_body) >= 4:
                        method_id = struct.unpack_from('<i', packet_body, 0)[0]
                        print(f"Received game logic packet from {addr}: method=0x{method_id:x}, body_size={len(packet_body)}")
                        
                        if method_id == USER_LOGIN:
                            global current_account_id
                            login_data = parse_user_login(packet_body[4:])
                            if login_data:
                                # Store account context for later character creation
                                current_account_id, _ = get_or_create_account(login_data['account'])
                                response = handle_user_login(
                                    login_data['account'],
                                    login_data['user_type'],
                                    login_data['client_type'],
                                    login_data['password'],
                                    login_data['token']
                                )
                                print(f"Sending login response, size={len(response)}")
                                conn.sendall(response)
                                print("Login response sent.")
                            else:
                                print(f"Failed to parse UserLogin from {addr}")
                        elif method_id == USER_CREATE_CHARACTER:
                            # Parse SCharacterCreationData: nickname, style, avatarTraits (map), sex
                            offset = 4
                            nickname, offset = parse_string(packet_body, offset)
                            if offset + 4 > len(packet_body):
                                print(f"Failed to parse UserCreateCharacter from {addr}")
                            else:
                                style = struct.unpack_from('<i', packet_body, offset)[0]
                                offset += 4
                                avatar_traits, offset = parse_map_int_int(packet_body, offset)
                                if offset + 4 > len(packet_body):
                                    print(f"Failed to parse UserCreateCharacter sex from {addr}")
                                else:
                                    sex = struct.unpack_from('<i', packet_body, offset)[0]
                                    print(f"UserCreateCharacter: nickname={nickname}, style={style}, sex={sex}")
                                    response = handle_user_create_character(nickname, style, sex)
                                    print(f"Sending create character response, size={len(response)}")
                                    conn.sendall(response)
                                    print("Response sent.")
                        elif method_id == USER_SELECT_CHARACTER:
                            # Parse character ID (int)
                            if len(packet_body) < 8:
                                print(f"Failed to parse UserSelectCharacter from {addr}")
                            else:
                                character_id = struct.unpack_from('<i', packet_body, 4)[0]
                                print(f"UserSelectCharacter: character_id={character_id}")
                                responses = handle_user_select_character(character_id)
                                for resp in responses:
                                    conn.sendall(resp)
                        elif method_id == ENTER_SCENE:
                            # Parse map name (string)
                            offset = 4
                            if offset + 4 > len(packet_body):
                                print(f"Failed to parse EnterScene from {addr}")
                            else:
                                map_name, _ = parse_string(packet_body, offset)
                                print(f"EnterScene: map={map_name}")
                                response = handle_enter_scene(map_name)
                                conn.sendall(response)
                        elif method_id == MAP_LOAD_OK:
                            # Client finished loading the scene - send CharacterStartInfo + spawn entities
                            print(f"MapLoadOK from {addr}")
                            responses = handle_map_load_ok()
                            for resp in responses:
                                conn.sendall(resp)
                        elif method_id == TUTORIAL_ENTER_REQ:
                            # Client requests to enter tutorial, send ack
                            if len(packet_body) < 8:
                                print(f"Failed to parse TutorialEnterReq from {addr}")
                            else:
                                char_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_tutorial_enter_req(char_id)
                                conn.sendall(response)
                        elif method_id == ACCEPT_MISSION:
                            # Client accepts a mission
                            if len(packet_body) < 12:
                                print(f"Failed to parse AcceptMission from {addr}")
                            else:
                                npc_id = struct.unpack_from('<i', packet_body, 4)[0]
                                mission_id = struct.unpack_from('<i', packet_body, 8)[0]
                                response = handle_accept_mission(npc_id, mission_id)
                                # Handle both single packet and list of packets
                                if isinstance(response, list):
                                    for resp in response:
                                        conn.sendall(resp)
                                else:
                                    conn.sendall(response)
                        elif method_id == PING_REQUEST:
                            # Client periodic ping - respond with ack
                            response = handle_ping_request()
                            conn.sendall(response)
                        elif method_id == GET_PLAYER_MAIL:
                            # Client requests mail list
                            response = handle_get_player_mail()
                            conn.sendall(response)
                        elif method_id == REQUEST_DAY_REWARD:
                            # Client requests daily reward
                            response = handle_request_day_reward()
                            conn.sendall(response)
                        elif method_id == GET_FRIEND_REWARD:
                            # Client requests friend reward info
                            response = handle_get_friend_reward()
                            conn.sendall(response)
                        elif method_id == HAS_ASSIGNED_TALENT_POINT_REQ:
                            # Client asks if talent points have been assigned
                            response = handle_has_assigned_talent_point_req()
                            conn.sendall(response)
                        
                        # New handlers for complete implementation
                        elif method_id == BUY_CHAR_SLOT_REQUEST:
                            response = handle_buy_char_slot_request()
                            conn.sendall(response)
                        elif method_id == BUY_CONSUME_ITEM:
                            if len(packet_body) >= 12:
                                item_id = struct.unpack_from('<i', packet_body, 4)[0]
                                quantity = struct.unpack_from('<i', packet_body, 8)[0]
                                response = handle_buy_consume_item(item_id, quantity)
                                conn.sendall(response)
                        elif method_id == BUY_ITEM:
                            if len(packet_body) >= 8:
                                item_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_buy_item(item_id)
                                conn.sendall(response)
                        elif method_id == BUY_PET:
                            if len(packet_body) >= 8:
                                pet_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_buy_pet(pet_id)
                                conn.sendall(response)
                        elif method_id == CHANGE_GENDER_REQ:
                            if len(packet_body) >= 8:
                                gender = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_change_gender_req(gender)
                                conn.sendall(response)
                        elif method_id == CHANGE_NAME_REQ:
                            offset = 4
                            name, _ = parse_string(packet_body, offset)
                            if name is not None:
                                response = handle_change_name_req(name)
                                conn.sendall(response)
                        elif method_id == CHAT_REQUEST:
                            # Parse channel and message (simplified)
                            response = handle_chat_request(0, "")
                            conn.sendall(response)
                        elif method_id == CRAFTING_ITEM:
                            if len(packet_body) >= 8:
                                recipe_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_crafting_item(recipe_id)
                                conn.sendall(response)
                        elif method_id == DEL_ITEM:
                            if len(packet_body) >= 8:
                                item_uuid = struct.unpack_from('<i', packet_body, 4)[0]
                                handle_del_item(item_uuid)
                        elif method_id == DELETE_MAIL:
                            if len(packet_body) >= 8:
                                mail_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_delete_mail(mail_id)
                                conn.sendall(response)
                        elif method_id == EQUIP_ITEM:
                            # Packet format: [methodID(4)][part(1)][bagID(1)][slot(4)]
                            if len(packet_body) >= 9:
                                part = struct.unpack_from('B', packet_body, 4)[0]   # equipment slot
                                bag_id = struct.unpack_from('B', packet_body, 5)[0]  # bag ID (2=inventory)
                                slot = struct.unpack_from('<I', packet_body, 6)[0]   # slot in bag
                                print(f"EquipItem: part={part}, bagID={bag_id}, slot={slot}")
                                result_packets = handle_equip_item(part, bag_id, slot)
                                if result_packets:
                                    for pkt in result_packets:
                                        conn.sendall(pkt)
                        elif method_id == GET_DAY_REWARD:
                            if len(packet_body) >= 8:
                                day_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_get_day_reward(day_id)
                                conn.sendall(response)
                        elif method_id == GET_GIFT_REQ:
                            if len(packet_body) >= 8:
                                gift_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_get_gift_req(gift_id)
                                conn.sendall(response)
                        elif method_id == GET_LEADERBOARD_INFO:
                            response = handle_get_leaderboard_info()
                            conn.sendall(response)
                        elif method_id == GET_MAIL_ALL:
                            response = handle_get_mail_all()
                            conn.sendall(response)
                        elif method_id == GET_MAIL_ITEM:
                            if len(packet_body) >= 8:
                                mail_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_get_mail_item(mail_id)
                                conn.sendall(response)
                        elif method_id == GET_MAIL_PET:
                            if len(packet_body) >= 8:
                                mail_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_get_mail_pet(mail_id)
                                conn.sendall(response)
                        elif method_id == GET_REDEEM_GIFT:
                            offset = 4
                            code, _ = parse_string(packet_body, offset)
                            if code is not None:
                                response = handle_get_redeem_gift(code)
                                conn.sendall(response)
                        elif method_id == GET_WELL_DATA:
                            response = handle_get_well_data()
                            conn.sendall(response)
                        elif method_id == LEAVE_WORLD:
                            handle_leave_world()
                        elif method_id == MISSION_FAIL_REQ:
                            if len(packet_body) >= 8:
                                mission_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_mission_fail_req(mission_id)
                                conn.sendall(response)
                        elif method_id == MISSION_LIST_REQ:
                            response = handle_mission_list_req()
                            conn.sendall(response)
                        elif method_id == MISSION_PROCESS_REQ:
                            if len(packet_body) >= 8:
                                mission_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_mission_process_req(mission_id)
                                conn.sendall(response)
                        elif method_id == OPEN_MAIL:
                            if len(packet_body) >= 8:
                                mail_id = struct.unpack_from('<i', packet_body, 4)[0]
                                handle_open_mail(mail_id)
                        elif method_id == PROCESS_FRIEND_REWARD:
                            handle_process_friend_reward()
                        elif method_id == PROCESS_REDEEM_GIFT:
                            offset = 4
                            code, _ = parse_string(packet_body, offset)
                            if code is not None:
                                response = handle_process_redeem_gift(code)
                                conn.sendall(response)
                        elif method_id == REQUEST_BAG_INFO:
                            response = handle_request_bag_info()
                            conn.sendall(response)
                        elif method_id == REQUEST_PLAYER_CONSUME_SHOP_INFO:
                            response = handle_request_player_consume_shop_info()
                            conn.sendall(response)
                        elif method_id == REQUEST_PLAYER_SHOP_INFO:
                            response = handle_request_player_shop_info()
                            conn.sendall(response)
                        elif method_id == ROLE_MASTERY_LIST_REQ:
                            response = handle_role_mastery_list_req()
                            conn.sendall(response)
                        elif method_id == ROLE_PET_LIST_REQ:
                            response = handle_role_pet_list_req()
                            conn.sendall(response)
                        elif method_id == SALE_ITEM:
                            if len(packet_body) >= 8:
                                item_uuid = struct.unpack_from('<i', packet_body, 4)[0]
                                handle_sale_item(item_uuid)
                        elif method_id == SEND_MAIL:
                            # Simplified parsing
                            response = handle_send_mail(0, "", "")
                            conn.sendall(response)
                        elif method_id == SPEED_UP_COOL_DOWN:
                            if len(packet_body) >= 8:
                                cooldown_type = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_speed_up_cool_down(cooldown_type)
                                conn.sendall(response)
                        elif method_id == SPLIT_ITEM:
                            if len(packet_body) >= 12:
                                item_uuid = struct.unpack_from('<i', packet_body, 4)[0]
                                quantity = struct.unpack_from('<i', packet_body, 8)[0]
                                handle_split_item(item_uuid, quantity)
                        elif method_id == STUDY_ABILITY:
                            if len(packet_body) >= 8:
                                ability_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_study_ability(ability_id)
                                conn.sendall(response)
                        elif method_id == SWAP_ITEM:
                            if len(packet_body) >= 12:
                                item_uuid1 = struct.unpack_from('<i', packet_body, 4)[0]
                                item_uuid2 = struct.unpack_from('<i', packet_body, 8)[0]
                                handle_swap_item(item_uuid1, item_uuid2)
                        elif method_id == UNEQUIP_ITEM:
                            if len(packet_body) >= 8:
                                slot = struct.unpack_from('<i', packet_body, 4)[0]
                                handle_unequip_item(slot)
                        elif method_id == UPGRADE_WELL:
                            if len(packet_body) >= 8:
                                well_type = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_upgrade_well(well_type)
                                conn.sendall(response)
                        elif method_id == USER_DEL_CHARACTER:
                            if len(packet_body) >= 8:
                                character_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_user_del_character(character_id)
                                conn.sendall(response)
                        elif method_id == USER_LOGOUT:
                            handle_user_logout()
                        elif method_id == ASSIGN_TALENT_REQ:
                            if len(packet_body) >= 16:
                                prowess = struct.unpack_from('<i', packet_body, 4)[0]
                                fortitude = struct.unpack_from('<i', packet_body, 8)[0]
                                cunning = struct.unpack_from('<i', packet_body, 12)[0]
                                response = handle_assign_talent_req(prowess, fortitude, cunning)
                                conn.sendall(response)
                        elif method_id == BUY_ALL_AREA_BY_KARMA_REQ:
                            response = handle_buy_all_area_by_karma_req()
                            conn.sendall(response)
                        elif method_id == BUY_STASH:
                            response = handle_buy_stash()
                            conn.sendall(response)
                        elif method_id == BUY_THREAT_LEVEL_BY_KARMA:
                            response = handle_buy_threat_level_by_karma()
                            conn.sendall(response)
                        elif method_id == CHOOSE_PET:
                            if len(packet_body) >= 8:
                                pet_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_choose_pet(pet_id)
                                conn.sendall(response)
                        elif method_id == CONVERSATION_NPC_CHECK_REQ:
                            if len(packet_body) >= 8:
                                npc_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_conversation_npc_check_req(npc_id)
                                conn.sendall(response)
                        elif method_id == DECREASE_COOL_DOWN:
                            if len(packet_body) >= 8:
                                cooldown_type = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_decrease_cool_down(cooldown_type)
                                conn.sendall(response)
                        elif method_id == EXPLORETASKCOMPLETE_REQ:
                            if len(packet_body) >= 8:
                                task_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_exploretaskcomplete_req(task_id)
                                conn.sendall(response)
                        elif method_id == MASTERY_LVLUP_REQ:
                            offset = 4
                            mastery_type, _ = parse_string(packet_body, offset)
                            if mastery_type is not None:
                                response = handle_mastery_lvlup_req(mastery_type)
                                conn.sendall(response)
                        elif method_id == PROTECTTASKBEGIN_REQ:
                            if len(packet_body) >= 8:
                                task_id = struct.unpack_from('<i', packet_body, 4)[0]
                                handle_protecttaskbegin_req(task_id)
                        elif method_id == PROTECTTASKEND_REQ:
                            if len(packet_body) >= 8:
                                task_id = struct.unpack_from('<i', packet_body, 4)[0]
                                handle_protecttaskend_req(task_id)
                        elif method_id == ROLE_ATTRIB_REQ:
                            response = handle_role_attrib_req()
                            conn.sendall(response)
                        elif method_id == UNLOCK_AREA_REQ:
                            if len(packet_body) >= 8:
                                area_id = struct.unpack_from('<i', packet_body, 4)[0]
                                response = handle_unlock_area_req(area_id)
                                conn.sendall(response)
                        elif method_id == USE_ITEM:
                            if len(packet_body) >= 8:
                                item_uuid = struct.unpack_from('<i', packet_body, 4)[0]
                                handle_use_item(item_uuid)
                        elif method_id == USER_RECONNECT:
                            # Client reconnecting - just acknowledge
                            print(f"UserReconnect from {addr}")
                            response = build_packet(USER_LOGIN_OK, struct.pack('<ii', 1, 0))
                            conn.sendall(response)
                        elif method_id == USER_CREATE_ACCOUNT_CHARACTER:
                            if len(packet_body) >= 24:
                                steam_id_str = packet_body[4:20].decode('ascii').strip('\x00')
                                nickname = packet_body[20:36].decode('ascii').strip('\x00')
                                style = struct.unpack_from('<i', packet_body, 36)[0]
                                sex = struct.unpack_from('<i', packet_body, 40)[0]
                                print(f"UserCreateAccountCharacter: steam_id={steam_id_str}, nickname={nickname}")
                                response = handle_user_create_character(steam_id_str, nickname, style, sex)
                                conn.sendall(response)
                        elif method_id == RELOAD_MAP:
                            if len(packet_body) >= 4:
                                print(f"ReloadMap from {addr}")
                                # Send empty map data
                                response = build_packet(RELOAD_MAP_RESULT, b'')
                                conn.sendall(response)
                        elif method_id == GET_MAIL_KARMA:
                            if len(packet_body) >= 4:
                                print(f"GetMailKarma from {addr}")
                                # Return success with karma amount
                                response = build_packet(GET_MAIL_KARMA_RESULT, struct.pack('<ii', 1, 100))
                                conn.sendall(response)
                        elif method_id == GET_MAIL_CRYSTAL:
                            if len(packet_body) >= 4:
                                print(f"GetMailCrystal from {addr}")
                                # Return success with crystal amount
                                response = build_packet(GET_MAIL_CRYSTAL_RESULT, struct.pack('<ii', 1, 50))
                                conn.sendall(response)
                        elif method_id == DELETE_MAIL_ITEM:
                            if len(packet_body) >= 4:
                                print(f"DeleteMailItem from {addr}")
                                # Return success
                                response = build_packet(DELETE_MAIL_ACK, struct.pack('<i', 1))
                                conn.sendall(response)
                        elif method_id == GET_MAIL_ALL_ITEMS:
                            if len(packet_body) >= 4:
                                print(f"GetMailAllItems from {addr}")
                                # Return empty item list
                                response = build_packet(GET_MAIL_ALL_ITEMS_RESULT, struct.pack('<i', 0))
                                conn.sendall(response)
                        elif method_id == GET_MAIL_ALL_PETS:
                            if len(packet_body) >= 4:
                                print(f"GetMailAllPets from {addr}")
                                # Return empty pet list
                                response = build_packet(GET_MAIL_PET_RESULT, struct.pack('<i', 0))
                                conn.sendall(response)
                        elif method_id == DELETE_MAIL_PET:
                            if len(packet_body) >= 4:
                                print(f"DeleteMailPet from {addr}")
                                # Return success
                                response = build_packet(DELETE_MAIL_ACK, struct.pack('<i', 1))
                                conn.sendall(response)
                        
                        # Battle protocol handlers
                        elif method_id == MOVE_UNIT:
                            if len(packet_body) >= 4:
                                print(f"MoveUnit from {addr}")
                                # Echo back position update acknowledgment with expected format
                                # Client expects: [int result][float x][float y][float z]
                                resp_body = struct.pack('<ifff', 1, 0.0, 0.0, 0.0)
                                response = build_packet(UPDATE_MOVE_RESULT, resp_body)
                                conn.sendall(response)
                        elif method_id == UPDATE_MOVE_REQUEST:
                            if len(packet_body) >= 16:  # At least x,y,z floats (4 bytes each)
                                # Parse position from packet: [4 bytes method][12 bytes pos(x,y,z)]
                                px = struct.unpack_from('<f', packet_body, 4)[0]
                                py = struct.unpack_from('<f', packet_body, 8)[0]
                                pz = struct.unpack_from('<f', packet_body, 12)[0]
                                print(f"[POSITION] Player at ({px:.2f}, {py:.2f}, {pz:.2f}) on map '{current_map_name}'")
                                # Acknowledge movement update with position echo
                                resp_body = struct.pack('<ifff', 1, px, py, pz)
                                response = build_packet(UPDATE_MOVE_RESULT, resp_body)
                                conn.sendall(response)
                            else:
                                print(f"UpdateMoveRequest: packet too small ({len(packet_body)} bytes) from {addr}")
                        elif method_id == PICKUP_ITEM_REQ:
                            if len(packet_body) >= 8:
                                item_uuid = struct.unpack_from('<i', packet_body, 4)[0]
                                print(f"PickupItemReq: uuid={item_uuid} from {addr}")
                                # Return success
                                response = build_packet(PICKUP_ITEM_SUCC_ACK, struct.pack('<ii', item_uuid, 1))
                                conn.sendall(response)
                        elif method_id == PICKUP_MONEY_REQ:
                            if len(packet_body) >= 8:
                                money_uuid = struct.unpack_from('<i', packet_body, 4)[0]
                                amount = struct.unpack_from('<i', packet_body, 8)[0] if len(packet_body) >= 12 else 10
                                print(f"PickupMoneyReq: uuid={money_uuid}, amount={amount} from {addr}")
                                # Return success with money collected
                                response = build_packet(PICKUP_MONEY_RESULT, struct.pack('<iii', money_uuid, amount, 1))
                                conn.sendall(response)
                        elif method_id == USE_NORMAL_ATTACK:
                            if len(packet_body) >= 4:
                                print(f"UseNormalAttack from {addr}")
                                # Return success
                                response = build_packet(USE_NORMAL_ATTACK_RESULT, struct.pack('<i', 1))
                                conn.sendall(response)
                        elif method_id == USE_FIGHT_SKILL:
                            if len(packet_body) >= 8:
                                skill_id = struct.unpack_from('<i', packet_body, 4)[0]
                                print(f"UseFightSkill: id={skill_id} from {addr}")
                                # Return success
                                response = build_packet(USE_FIGHT_SKILL_RESULT, struct.pack('<ii', skill_id, 1))
                                conn.sendall(response)
                        elif method_id == PLAYER_FIRE_REQ:
                            if len(packet_body) >= 4:
                                print(f"PlayerFireReq from {addr}")
                                # No specific response needed for fire request
                        elif method_id == BEGIN_USE_SKILL:
                            if len(packet_body) >= 8:
                                skill_id = struct.unpack_from('<i', packet_body, 4)[0]
                                print(f"BeginUseSkill: id={skill_id} from {addr}")
                                # No specific response needed
                        elif method_id == STOP_BEGIN_USE_SKILL:
                            if len(packet_body) >= 8:
                                skill_id = struct.unpack_from('<i', packet_body, 4)[0]
                                print(f"StopBeginUseSkill: id={skill_id} from {addr}")
                                # No specific response needed
                        elif method_id == REVIVE_REQ:
                            if len(packet_body) >= 4:
                                print(f"ReviveReq from {addr}")
                                # Return success - player revived
                                response = build_packet(REVIVE_RESULT, struct.pack('<i', 1))
                                conn.sendall(response)
                        elif method_id == ENEMY_REWARD_REQ:
                            if len(packet_body) >= 8:
                                enemy_uuid = struct.unpack_from('<i', packet_body, 4)[0]
                                print(f"EnemyRewardReq: uuid={enemy_uuid} from {addr}")
                                # Return success with some karma reward
                                response = build_packet(ENEMY_REWARD_REQ, struct.pack('<iii', enemy_uuid, 10, 5))
                                conn.sendall(response)
                        elif method_id == GET_FRIEND_LIST:
                            if len(packet_body) >= 4:
                                print(f"GetFriendList from {addr}")
                                # Return empty friend list
                                response = build_packet(GET_FRIEND_LIST_RESULT, struct.pack('<i', 0))
                                conn.sendall(response)
                        elif method_id == SELECT_FRIEND_ALLY:
                            if len(packet_body) >= 8:
                                ally_uuid = struct.unpack_from('<i', packet_body, 4)[0]
                                print(f"SelectFriendAlly: uuid={ally_uuid} from {addr}")
                                # Return success
                                response = build_packet(SELECT_FRIEND_ALLY_RESULT, struct.pack('<ii', ally_uuid, 1))
                                conn.sendall(response)
                        elif method_id == SET_MOVE_TYPE:
                            if len(packet_body) >= 8:
                                move_type = struct.unpack_from('<i', packet_body, 4)[0]
                                print(f"SetMoveType: type={move_type} from {addr}")
                                # Return success
                                response = build_packet(SET_MOVE_TYPE_RESULT, struct.pack('<ii', move_type, 1))
                                conn.sendall(response)
                        elif method_id == PLAYER_CHANGE_WEAPON:
                            if len(packet_body) >= 8:
                                weapon_slot = struct.unpack_from('<i', packet_body, 4)[0]
                                print(f"PlayerChangeWeapon: slot={weapon_slot} from {addr}")
                                # Return success
                                response = build_packet(PLAYER_CHANGE_WEAPON_OK, struct.pack('<ii', weapon_slot, 1))
                                conn.sendall(response)
                        elif method_id == ACTIVE_TRIGGER_REQ:
                            if len(packet_body) >= 8:
                                trigger_uuid = struct.unpack_from('<i', packet_body, 4)[0]
                                print(f"ActiveTriggerReq: uuid={trigger_uuid} from {addr}")
                                # Return success
                                response = build_packet(TRIGGER_ANIMATION_RESULT, struct.pack('<ii', trigger_uuid, 1))
                                conn.sendall(response)
                        elif method_id == GET_WELL_KARMA:
                            if len(packet_body) >= 4:
                                print(f"GetWellKarma from {addr}")
                                # Return success with karma amount
                                response = build_packet(GET_WELL_KARMA_RESULT, struct.pack('<ii', 1, 50))
                                conn.sendall(response)
                        elif method_id == SET_SKILL_SHORTCUT:
                            if len(packet_body) >= 4:
                                print(f"SetSkillShortcut from {addr}")
                                # No specific response needed
                        elif method_id == PLAYER_USE_COOL_WEAPON_REQ:
                            if len(packet_body) >= 4:
                                print(f"PlayerUseCoolWeaponReq from {addr}")
                                # No specific response needed
                        elif method_id == CREATE_ALLY_NPC_REQUEST:
                            if len(packet_body) >= 8:
                                npc_type = struct.unpack_from('<i', packet_body, 4)[0]
                                print(f"CreateAllyNpcRequest: type={npc_type} from {addr}")
                                # Return success with new NPC UUID
                                response = build_packet(CREATE_ALLY_NPC_REQUEST, struct.pack('<ii', npc_type, 999))
                                conn.sendall(response)
                        elif method_id == USE_ALLY_NORMAL_ATTACK:
                            if len(packet_body) >= 8:
                                ally_uuid = struct.unpack_from('<i', packet_body, 4)[0]
                                print(f"UseAllyNormalAttack: uuid={ally_uuid} from {addr}")
                                # No specific response needed
                        elif method_id == USE_ALLY_SKILL:
                            if len(packet_body) >= 12:
                                ally_uuid = struct.unpack_from('<i', packet_body, 4)[0]
                                skill_id = struct.unpack_from('<i', packet_body, 8)[0]
                                print(f"UseAllySkill: uuid={ally_uuid}, skill={skill_id} from {addr}")
                                # No specific response needed
                        elif method_id == ALLY_UPDATE_MOVE_REQUEST:
                            if len(packet_body) >= 8:
                                ally_uuid = struct.unpack_from('<i', packet_body, 4)[0]
                                print(f"AllyUpdateMoveRequest: uuid={ally_uuid} from {addr}")
                                # No specific response needed
                        elif method_id == SET_OBJECT_POSITION:
                            if len(packet_body) >= 4:
                                print(f"SetObjectPosition from {addr}")
                                # No specific response needed
                        elif method_id == SET_OBJECT_VEC_POSITION:
                            if len(packet_body) >= 4:
                                print(f"SetObjectVecPosition from {addr}")
                                # No specific response needed
                        elif method_id == OBJECT_ENTER_TEST:
                            if len(packet_body) >= 4:
                                print(f"ObjectEnterTest from {addr}")
                                # Return success
                                response = build_packet(OBJECT_ENTER_TEST, struct.pack('<i', 1))
                                conn.sendall(response)
                        elif method_id == OBJECT_LEAVE:
                            if len(packet_body) >= 4:
                                print(f"ObjectLeave from {addr}")
                                # No specific response needed
                        
                        # Additional client-sent protocol handlers
                        elif method_id == CHAT_RESPONSE:
                            if len(packet_body) >= 4:
                                print(f"ChatResponse from {addr}")
                                # No specific response needed
                        elif method_id == MISSION_AREA_INFO_ACK:
                            if len(packet_body) >= 4:
                                print(f"MissionAreaInfoAck from {addr}")
                                # No specific response needed
                        elif method_id == NEW_REDEEM_GIFT:
                            if len(packet_body) >= 4:
                                print(f"NewRedeemGift from {addr}")
                                # Return success
                                response = build_packet(NEW_REDEEM_GIFT, struct.pack('<i', 1))
                                conn.sendall(response)
                        elif method_id == UPDATE_EVENT:
                            if len(packet_body) >= 4:
                                event_data, _ = parse_map_int_int(packet_body, 4)
                                print(f"UpdateEvent: {event_data} from {addr}")
                                # No specific response needed - client is just updating event state
                        else:
                            print(f"Unknown method ID: 0x{method_id:x} from {addr}")
                    else:
                        print(f"Game logic packet too small from {addr}")
                        
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        conn.close()
        print(f"Client disconnected: {addr}")

def main():
    global running
    port = 8080
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    
    # Initialize database
    init_db()
    
    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', port))
    server.listen(5)
    
    print(f"Akaneiro local game server listening on port {port}")
    print("Waiting for client connection...")
    print("Press Ctrl+C to stop.")
    
    while running:
        try:
            # Use a timeout so we can check the 'running' flag periodically
            server.settimeout(1.0)
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.daemon = True
            thread.start()
        except socket.timeout:
            continue  # Check running flag again
    
    print("Game server stopped.")

if __name__ == '__main__':
    main()
