#!/usr/bin/env python3
"""Test only the new protocol handlers one at a time."""

import socket
import struct
import time

def build_packet(method_id, body=b''):
    """Build a properly framed game server packet."""
    full_body = struct.pack('<i', method_id) + body
    header = struct.pack('<ih', len(full_body), 0)
    return header + full_body

def test_handler(name, method_id, body=b'', timeout=3.0):
    """Test a single handler."""
    try:
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect(('127.0.0.1', 8080))
        
        packet = build_packet(method_id, body)
        conn.sendall(packet)
        
        conn.settimeout(timeout)
        try:
            data = b''
            while len(data) < 6:
                chunk = conn.recv(1024)
                if not chunk:
                    break
                data += chunk
            
            if len(data) >= 6:
                body_size, msg_type = struct.unpack_from('<ih', data, 0)
                while len(data) < 6 + body_size:
                    chunk = conn.recv(1024)
                    if not chunk:
                        break
                    data += chunk
                
                print(f"  {name}: OK (received {len(data)} bytes)")
            else:
                print(f"  {name}: INCOMPLETE RESPONSE")
        except socket.timeout:
            print(f"  {name}: TIMEOUT")
        
        conn.close()
    except Exception as e:
        print(f"  {name}: ERROR - {e}")

print("Testing new protocol handlers...")

# UserReconnect (0x5469770e)
test_handler("UserReconnect", 0x5469770e)

# ReloadMap (0x3fa4968b)
test_handler("ReloadMap", 0x3fa4968b, struct.pack('<i', 1))

# GetMailKarma (0x4062b379)
test_handler("GetMailKarma", 0x4062b379, struct.pack('<i', 1))

# GetMailCrystal (0x225817af)
test_handler("GetMailCrystal", 0x225817af, struct.pack('<i', 1))

# DeleteMailItem (0x5e47601b)
test_handler("DeleteMailItem", 0x5e47601b, struct.pack('<i', 1))

# GetMailAllItems (0x4122465a)
test_handler("GetMailAllItems", 0x4122465a, b'')

# GetMailAllPets (0x6af25936)
test_handler("GetMailAllPets", 0x6af25936, b'')

# DeleteMailPet (0x1c15e3db)
test_handler("DeleteMailPet", 0x1c15e3db, struct.pack('<i', 1))

print("\nNew handler tests complete!")