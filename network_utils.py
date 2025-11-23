import socket
import struct
import pickle

def send_msg(sock, data):
    """
    Sends data (any picklable object) over the socket.
    Prefixes with 4-byte length.
    """
    serialized = pickle.dumps(data)
    length = len(serialized)
    sock.sendall(struct.pack('!I', length))
    sock.sendall(serialized)

def recv_msg(sock):
    """
    Receives data from the socket.
    """
    # Read length
    raw_len = recvall(sock, 4)
    if not raw_len:
        return None
    length = struct.unpack('!I', raw_len)[0]
    # Read data
    data = recvall(sock, length)
    if not data:
        return None
    return pickle.loads(data)

def recvall(sock, n):
    """
    Helper to receive exactly n bytes.
    """
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data
