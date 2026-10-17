#!/usr/bin/env python3
"""
Akaneiro Demon Hunters - Local Auth Server (HTTP)
Handles both NormalClientVersion login and Steam client authorization.

Endpoints:
  POST /login                    - Normal client login (email/password)
  POST /client/steam/user/authorize - Steam client auth (session ticket)
  POST /client/steam/user/refresh   - Steam token refresh
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys

class AuthHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        print(f"POST {self.path}: {body[:100]}")
        
        # Parse form data
        params = {}
        for pair in body.split('&'):
            if '=' in pair:
                k, v = pair.split('=', 1)
                params[k] = v
        
        if self.path == '/login':
            # Normal client login (email/password)
            email = params.get('email', 'unknown')
            print(f"Normal login: {email}")
            
            response = json.dumps({
                "uid": "1001",
                "message": "success",
                "ip": "127.0.0.1:8080",
                "gameCode": "local_token_abc123",
                "key": "local_key_xyz789"
            })
            
        elif self.path == '/client/steam/user/authorize':
            # Steam client authorization
            ticket = params.get('ticket', 'unknown')
            print(f"Steam authorize: ticket={ticket[:20]}...")
            
            # Steam client expects {"success": {"token": "...", "server": "..."}}
            response = json.dumps({
                "success": {
                    "token": "local_steam_token_123",
                    "server": "127.0.0.1:8080"
                }
            })
            
        elif self.path == '/client/steam/user/refresh':
            # Steam token refresh (called every 30 min)
            steam_id = params.get('steam_id', 'unknown')
            print(f"Steam refresh: steam_id={steam_id}")
            
            # Client expects {"success": {{"token": "..."}}}
            response = json.dumps({
                "success": {
                    "token": "local_steam_token_123"
                }
            })
            
        elif self.path == '/client/steam/dlc/validate':
            # DLC validation - client sends DLC IDs, we say they're all owned
            steam_id = params.get('steam_id', 'unknown')
            token = params.get('token', '')
            character = params.get('character', '')
            dlcs = params.get('dlcs', '')
            print(f"DLC validate: steam_id={steam_id}, token=token{token}, character={character}, dlcs={dlcs}")
            
            # Client expects {"success": {{"msg": "..."}}}
            response = json.dumps({
                "success": {
                    "msg": "Ok"
                }
            })
        elif self.path.startswith('/client.php'):
            # Web client login endpoint - parse mod from URL query string
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            query_params = parse_qs(parsed.query)
            mod = query_params.get('mod', [''])[0]
            email = params.get('email', 'unknown')
            password = params.get('password', '')
            print(f"Web client {mod}: email={email}")
            
            if mod == 'login':
                # Web login - return success with game server info
                # Format: uid:X,token:X,ip:"X.X.X.X:PORT",gameCode:X,key:X
                response = "uid:\"1002\",token:\"local_web_token_abc123\",ip:\"127.0.0.1:8080\",gameCode:\"local_web_gamecode_abc123\",key:\"local_web_key_xyz789\""
            elif mod == 'recharge':
                # Payment/recharge endpoint
                response = json.dumps({"success": True})
            else:
                response = json.dumps({"status": "ok"})
        elif self.path == '/client/steam/transaction/init':
            # Transaction init (in-game purchases)
            steam_id = params.get('steam_id', 'unknown')
            item_id = params.get('item_id', '')
            print(f"Transaction init: steam_id={steam_id}, item_id={item_id}")
            response = json.dumps({
                "success": {
                    "msg": "Transaction initialized"
                }
            })
        elif self.path == '/client/steam/transaction/complete':
            # Transaction complete
            steam_id = params.get('steam_id', 'unknown')
            order_id = params.get('order_id', '')
            print(f"Transaction complete: steam_id={steam_id}, order_id={order_id}")
            response = json.dumps({
                "success": {
                    "msg": "Transaction completed"
                }
            })
        else:
            # Unknown endpoint - return generic success
            print(f"Unknown endpoint: {self.path}")
            response = json.dumps({"status": "ok"})
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
        
        print(f"  -> {response}")
    
    def do_GET(self):
        # Handle any GET requests (version checks, etc.)
        print(f"GET {self.path}")
        response = json.dumps({"status": "ok"})
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def log_message(self, format, *args):
        pass  # Suppress default logging

def main():
    port = 80
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    
    server = HTTPServer(('0.0.0.0', port), AuthHandler)
    print(f"Akaneiro local auth server listening on port {port}")
    
    if port == 80:
        print("Note: Running on port 80 for Steam client compatibility.")
        print("If you get 'Address already in use', stop other web servers or")
        print("run with a different port and adjust hosts file accordingly.")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()

if __name__ == '__main__':
    main()
