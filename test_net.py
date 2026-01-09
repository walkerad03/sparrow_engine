import socket
import threading
import time
import sys

# Configuration
HOST_IP = "127.0.0.1"
HOST_PORT = 5000
CLIENT_PORT = 0  # Let OS decide


def run_host():
    print(f"[HOST] Starting on {HOST_IP}:{HOST_PORT}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Windows Fix: Sometimes binding to "" (empty) fails to match 127.0.0.1 correctly
    # We bind explicitly to localhost for this test.
    try:
        sock.bind((HOST_IP, HOST_PORT))
    except Exception as e:
        print(f"[HOST] Failed to bind: {e}")
        return

    sock.settimeout(1.0)  # Non-blocking with timeout
    print("[HOST] Listening...")

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            print(f"[HOST] Received '{data.decode()}' from {addr}")

            # Send Reply
            reply = f"WELCOME {addr}"
            sock.sendto(reply.encode(), addr)
            print(f"[HOST] Sent '{reply}' to {addr}")
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[HOST] Error: {e}")
            break


def run_client():
    # Give host a moment to start
    time.sleep(1)

    print(f"[CLIENT] Starting...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST_IP, 0))  # Bind to localhost to match host family

    server_addr = (HOST_IP, HOST_PORT)
    sock.settimeout(2.0)

    for i in range(5):
        msg = f"HELLO_{i}"
        print(f"[CLIENT] Sending '{msg}' to {server_addr}")
        sock.sendto(msg.encode(), server_addr)

        try:
            data, addr = sock.recvfrom(1024)
            print(f"[CLIENT] SUCCESS! Received '{data.decode()}' from {addr}")
            return  # Test Passed
        except socket.timeout:
            print("[CLIENT] Timed out waiting for response...")
        except ConnectionResetError:
            print("[CLIENT] Connection Reset! (Port closed or Firewall block)")

        time.sleep(1)

    print("[CLIENT] FAILED: No response received after 5 attempts.")


if __name__ == "__main__":
    # Run both in threads to simulate separate processes
    t_host = threading.Thread(target=run_host, daemon=True)
    t_host.start()

    run_client()
