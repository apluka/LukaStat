#Hand crafted by yours truely :)
#i cant remember any of the things you need to update or install so im sure you can paste it into mrgpt like you losers usually do #DADDYDEVLUKA
#the ui also needs fixing, there was an error caused by some telnet byte which i think i fixed but fuck knows
import socket
import threading
import time
import psutil
import platform
import subprocess
from collections import deque

# === CONFIG ===
HOST = '0.0.0.0'
PORT = 1337
UI_FILE = 'ui.txt'
HELP_FILE = 'help.txt'
UDP_DUMP_PORT = 6000
MAX_DUMP_ENTRIES = 10
START_TIME = time.time()

udp_dump = deque(maxlen=MAX_DUMP_ENTRIES)


def recv_line(conn, buffer):
    """
    Read from conn until a newline (\n) is found.
    Return (line_stripped, leftover_buffer_bytes).
    If connection closes, return ('', b'').
    """
    while True:
        if b'\n' in buffer:
            line, sep, rest = buffer.partition(b'\n')
            return line.decode(errors='ignore').strip(), rest
        chunk = conn.recv(1024)
        if not chunk:
            # Connection closed
            return '', b''
        buffer += chunk


def human_readable(bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} PB"


def load_file(file_path):
    try:
        with open(file_path) as f:
            return f.read()
    except:
        return f"Could not load {file_path}"


def collect_stats():
    counters = psutil.net_io_counters()
    return {
        'incoming': human_readable(counters.bytes_recv),
        'outgoing': human_readable(counters.bytes_sent),
        'pps_in': counters.packets_recv,
        'pps_out': counters.packets_sent,
        'connections': len(psutil.net_connections()),
        'uptime': time.strftime("%H:%M:%S", time.gmtime(time.time() - START_TIME)),
        'hostname': platform.node(),
        'ip': "51.38.84.62",
        'time': time.strftime("%Y-%m-%d %H:%M:%S"),
        'dump': "\n".join(udp_dump) if udp_dump else "No UDP packets yet."
    }


def geo_lookup(ip):
    try:
        subprocess.check_output(['ping', '-c', '1', ip], stderr=subprocess.DEVNULL, timeout=3)
        return f"\033[36mGeo lookup: {ip} is reachable (ping ok)\033[0m"
    except:
        return f"\033[31mGeo lookup: {ip} unreachable or offline\033[0m"


def icmp_ping(ip):
    try:
        out = subprocess.check_output(['ping', '-c', '1', ip], stderr=subprocess.STDOUT, timeout=3).decode()
        return f"\033[36mPing to {ip} successful:\n{out}\033[0m"
    except subprocess.CalledProcessError as e:
        return f"\033[31mPing failed:\n{e.output.decode(errors='ignore')}\033[0m"
    except Exception as e:
        return f"\033[31mPing error: {str(e)}\033[0m"


def tcp_ping(ip, port):
    try:
        port = int(port)
        with socket.create_connection((ip, port), timeout=3):
            return f"\033[36mTCP Ping to {ip}:{port} successful\033[0m"
    except Exception as e:
        return f"\033[31mTCP Ping failed: {e}\033[0m"


def show_ui(conn):
    stats = collect_stats()
    template = load_file(UI_FILE)
    for key, val in stats.items():
        template = template.replace(f'<<${key}>>', str(val))
    # Clear screen + move cursor home
    conn.sendall(b'\033[2J\033[H')
    conn.sendall(template.encode() + b'\n')


def handle_client(conn, addr):
    print(f"[DEBUG] Connection from {addr}")
    buffer = b''
    try:
        show_ui(conn)
        conn.sendall(b"\033[35mType 'help' to see available commands.\033[0m\n")
        while True:
            conn.sendall(b"\n\033[32m> \033[0m")
            cmd_line, buffer = recv_line(conn, buffer)
            if not cmd_line:
                break
            print(f"[DEBUG] Command received: '{cmd_line}'")
            parts = cmd_line.split()
            if not parts:
                continue
            cmd = parts[0].lower()
            args = parts[1:]

            if cmd == 'exit':
                break
            elif cmd == 'help':
                conn.sendall(load_file(HELP_FILE).encode() + b'\n')
            elif cmd == 'clear':
                show_ui(conn)
            elif cmd == 'geo' and len(args) == 1:
                conn.sendall(geo_lookup(args[0]).encode() + b'\n')
            elif cmd == 'ping' and len(args) == 1:
                conn.sendall(icmp_ping(args[0]).encode() + b'\n')
            elif cmd == 'tcpping' and len(args) == 2:
                conn.sendall(tcp_ping(args[0], args[1]).encode() + b'\n')
            else:
                conn.sendall(b"\033[31mUnknown command or wrong usage. Type 'help'\033[0m\n")
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
    finally:
        conn.close()
        print(f"[DEBUG] Connection closed for {addr}")


def start_tcp_server():
    print(f"Starting CNC on {HOST}:{PORT}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


def udp_listener():
    print(f"Starting UDP dump listener on port {UDP_DUMP_PORT}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, UDP_DUMP_PORT))
    while True:
        data, addr = sock.recvfrom(1024)
        udp_dump.appendleft(f"{addr[0]}:{addr[1]} -> {len(data)} bytes")


if __name__ == "__main__":
    threading.Thread(target=udp_listener, daemon=True).start()
    start_tcp_server()
