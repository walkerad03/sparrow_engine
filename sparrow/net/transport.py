import socket
from typing import List, Tuple

from sparrow.types import Address


def create_socket(port: int = 0) -> socket.socket:
    """
    Create and bind a UDP socket.
    :param port: 0 to let OS pick (Client), or specific integer (Host).
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    try:
        sock.bind(("127.0.0.1", port))
    except OSError:
        sock.bind(("0.0.0.0", port))
    return sock


def close_socket(sock: socket.socket) -> None:
    sock.close()


def send_packet(sock: socket.socket, data: bytes, addr: Address) -> None:
    """
    Send data to address
    """
    try:
        sock.sendto(data, addr)
    except OSError as e:
        print(f"[NET] Send Failed: {e}")


def recv_packets(
    sock: socket.socket, max_size: int = 4096
) -> List[Tuple[bytes, Address]]:
    """
    Read ALL available packets in the buffer.
    Returns list of (data, sender_address).
    """
    packets: List[Tuple[bytes, Address]] = []
    try:
        while True:
            data, addr = sock.recvfrom(max_size)
            packets.append((data, addr))
    except BlockingIOError:
        pass  # No data
    except ConnectionResetError:
        pass  # Windows UDP Error
    return packets
