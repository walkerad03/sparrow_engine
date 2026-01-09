import socket
from typing import List, Tuple

from sparrow.types import Address


class Transport:
    def __init__(self, port: int = 0):
        """
        :param port: 0 to let OS pick (Client), or specific integer (Host).
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            self.socket.bind(("127.0.0.1", port))
        except OSError:
            self.socket.bind(("0.0.0.0", port))

        self.socket.setblocking(False)
        self.port = self.socket.getsockname()[1]
        print(f"[NET] Socket bound to {self.socket.getsockname()}")

    def send(self, data: bytes, addr: Address):
        try:
            self.socket.sendto(data, addr)
        except OSError as e:
            print(f"[NET] Send Failed: {e}")

    def recv(self, max_size: int = 4096) -> List[Tuple[bytes, Address]]:
        """
        Reads ALL available packets in the buffer.
        Returns list of (data, sender_address).
        """
        packets = []
        try:
            while True:
                data, addr = self.socket.recvfrom(max_size)
                packets.append((data, addr))
        except BlockingIOError:
            pass  # No data
        except ConnectionResetError:
            pass  # Windows UDP Error
        return packets

    def close(self):
        self.socket.close()
