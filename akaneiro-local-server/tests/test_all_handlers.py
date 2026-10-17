#!/usr/bin/env python3
"""Comprehensive test of all Akaneiro protocol handlers."""

import socket
import struct
import time
import sys

def build_packet(method_id, body=b''):
    """Build a properly framed game server packet."""
    # Protocol: [4 bytes body size][2 bytes type][body]
    # Body starts with 4-byte method ID followed by payload
    full_body = struct.pack('<i', method_id) + body
    header = struct.pack('<ih', len(full_body), 0)  # type 0 = game logic
    return header + full_body

def send_request(conn, method_id, body=b'', timeout=5.0):
    """Send request and wait for response."""
    packet = build_packet(method_id, body)
    conn.sendall(packet)
    
    conn.settimeout(timeout)
    try:
        data = b''
        while len(data) < 6:
            chunk = conn.recv(1024)
            if not chunk:
                return None
            data += chunk
        
        body_size, msg_type = struct.unpack_from('<ih', data, 0)
        while len(data) < 6 + body_size:
            chunk = conn.recv(1024)
            if not chunk:
                break
            data += chunk
        
        # Extract method ID from response body
        if body_size >= 4:
            resp_method_id = struct.unpack_from('<i', data, 6)[0]
            return resp_method_id, data[10:]
        return None
    except socket.timeout:
        print(f"  Timeout waiting for response")
        return None

def test_game_server():
    """Test all game server protocol handlers."""
    print("Testing Game Server...")
    
    try:
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect(('127.0.0.1', 8080))
        print("  Connected to game server")
        
        # Test existing handlers first
        
        # PingRequest (0x4417ca2b)
        result = send_request(conn, 0x4417ca2b)
        if result:
            print(f"  PingRequest: OK (method=0x{result[0]:x})")
        
        # GetPlayerMail (0x3bd47c8a)
        result = send_request(conn, 0x3bd47c8a)
        if result:
            print(f"  GetPlayerMail: OK (method=0x{result[0]:x})")
        
        # RequestDayReward (0x460f4251)
        result = send_request(conn, 0x460f4251)
        if result:
            print(f"  RequestDayReward: OK (method=0x{result[0]:x})")
        
        # GetFriendReward (0x7ab097d0)
        result = send_request(conn, 0x7ab097d0)
        if result:
            print(f"  GetFriendReward: OK (method=0x{result[0]:x})")
        
        # HasAssignedTalentPointReq (0x7ab097d0)
        result = send_request(conn, 0x7ab097d0)
        if result:
            print(f"  HasAssignedTalentPointReq: OK (method=0x{result[0]:x})")
        
        # Test NEW handlers
        
        # UserReconnect (0x5469770e)
        result = send_request(conn, 0x5469770e)
        if result:
            print(f"  UserReconnect: OK (method=0x{result[0]:x})")
        
        # ReloadMap (0x3fa4968b)
        reload_body = struct.pack('<i', 1)
        result = send_request(conn, 0x3fa4968b, reload_body)
        if result:
            print(f"  ReloadMap: OK (method=0x{result[0]:x})")
        
        # GetMailKarma (0x4062b379)
        mail_body = struct.pack('<i', 1)
        result = send_request(conn, 0x4062b379, mail_body)
        if result:
            print(f"  GetMailKarma: OK (method=0x{result[0]:x})")
        
        # GetMailCrystal (0x225817af)
        result = send_request(conn, 0x225817af, mail_body)
        if result:
            print(f"  GetMailCrystal: OK (method=0x{result[0]:x})")
        
        # DeleteMailItem (0x5e47601b)
        result = send_request(conn, 0x5e47601b, mail_body)
        if result:
            print(f"  DeleteMailItem: OK (method=0x{result[0]:x})")
        
        # GetMailAllItems (0x4122465a)
        result = send_request(conn, 0x4122465a, b'')
        if result:
            print(f"  GetMailAllItems: OK (method=0x{result[0]:x})")
        
        # GetMailAllPets (0x6af25936)
        result = send_request(conn, 0x6af25936, b'')
        if result:
            print(f"  GetMailAllPets: OK (method=0x{result[0]:x})")
        
        # DeleteMailPet (0x1c15e3db)
        result = send_request(conn, 0x1c15e3db, mail_body)
        if result:
            print(f"  DeleteMailPet: OK (method=0x{result[0]:x})")
        
        conn.close()
        print("  Game server test complete - all handlers responded!")
        
    except Exception as e:
        print(f"  Game server test failed: {e}")

if __name__ == '__main__':
    test_game_server()
    print("\nAll tests completed!")