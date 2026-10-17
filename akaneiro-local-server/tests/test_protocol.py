#!/usr/bin/env python3
"""
Test script to verify protocol handling between client and server.
Starts both servers, simulates a login flow, and validates responses.
"""

import socket
import struct
import threading
import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from auth_server import AuthHandler, HTTPServer as AuthHTTPServer
from game_server import handle_client, make_game_packet, USER_LOGIN_OK

def write_int(buf, v):
    buf.extend(struct.pack('<i', v))

def write_short(buf, v):
    buf.extend(struct.pack('<h', v))

def write_string(buf, s):
    encoded = s.encode('utf-8')
    write_int(buf, len(encoded))
    buf.extend(encoded)

def make_user_login_packet(account="test@example.com", password="123456"):
    """Create a UserLogin game logic packet."""
    # Build payload: [method ID][account][userType][clientType][password][token]
    payload = bytearray()
    write_int(payload, 0x0ce102e4)  # USER_LOGIN method ID
    write_string(payload, account)
    write_int(payload, 0)  # userType
    write_int(payload, 0)  # clientType
    write_string(payload, password)
    write_string(payload, "")  # token
    
    # Frame as game logic packet: [size][type=0][payload]
    framed = bytearray()
    write_int(framed, len(payload))
    write_short(framed, 0)  # ePacketGameLogic
    framed.extend(payload)
    
    return bytes(framed)

def test_auth_server():
    """Test HTTP auth server."""
    print("Testing auth server...")
    
    server = AuthHTTPServer(('127.0.0.1', 8081), AuthHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    time.sleep(0.5)
    
    # Simulate client request
    import urllib.request
    data = "email=test@example.com&password=123456&game=akaneiro&other=v1".encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:8081/login', data=data)
    
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode('utf-8')
            print(f"  Auth response: {body}")
            
            # Verify it contains expected fields
            assert '"uid"' in body, "Missing uid field"
            assert '"ip"' in body, "Missing ip field"
            assert '127.0.0.1' in body, "Wrong IP address"
            print("  [OK] Auth server test passed")
    except Exception as e:
        print(f"  [FAIL] Auth server test failed: {e}")
        return False
    finally:
        server.shutdown()
    
    return True

def test_game_server():
    """Test TCP game server protocol handling."""
    print("Testing game server...")
    
    # Create a mock socket pair to simulate client connection
    import socketserver
    
    class TestGameServer(socketserver.TCPServer):
        allow_reuse_address = True
        
        def handle_client_connection(self, conn, addr):
            handle_client(conn, addr)
    
    server = TestGameServer(('127.0.0.1', 8080), None)
    
    # Start accepting connections in background
    def accept_loop():
        while True:
            try:
                conn, addr = server.get_request()
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
            except Exception:
                break
    
    thread = threading.Thread(target=accept_loop)
    thread.daemon = True
    thread.start()
    time.sleep(0.5)
    
    # Connect as client
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', 8080))
        
        # Send UserLogin packet
        login_packet = make_user_login_packet()
        sock.sendall(login_packet)
        print(f"  Sent UserLogin packet ({len(login_packet)} bytes)")
        
        # Wait for response
        data = sock.recv(4096)
        if not data:
            print("  [FAIL] No response received")
            return False
        
        print(f"  Received {len(data)} bytes")
        
        # Parse response - should be On_UserLoginOK (method ID 0x57aaeebc)
        body_size, msg_type = struct.unpack_from('<ih', data, 0)
        print(f"  Response: body_size={body_size}, msg_type={msg_type}")
        
        if msg_type != 0:
            print("  [FAIL] Expected game logic packet (type 0)")
            return False
        
        method_id = struct.unpack_from('<i', data, 6)[0]
        print(f"  Method ID: 0x{method_id:x}")
        
        if method_id != USER_LOGIN_OK:
            print(f"  [FAIL] Expected UserLoginOK (0x{USER_LOGIN_OK:x})")
            return False
        
        # Verify response contains account info (reconnected bool + strings)
        offset = 10  # past framing and method ID
        reconnected = data[offset]
        print(f"  Reconnected: {bool(reconnected)}")
        
        # Read account string length
        if offset + 5 <= len(data):
            acc_len = struct.unpack_from('<i', data, offset+1)[0]
            if offset + 5 + acc_len <= len(data):
                account = data[offset+5:offset+5+acc_len].decode('utf-8')
                print(f"  Account in response: {account}")
        
        print("  [OK] Game server test passed")
        
    except Exception as e:
        print(f"  [FAIL] Game server test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            sock.close()
        except:
            pass
        server.server_close()
    
    return True

def main():
    print("=== Akaneiro Protocol Test ===\n")
    
    auth_ok = test_auth_server()
    time.sleep(0.5)
    game_ok = test_game_server()
    
    print("\n=== Results ===")
    if auth_ok and game_ok:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())