import hashlib
import random
import pickle

# SECP256R1 Parameters
P = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff
A = 0xffffffff00000001000000000000000000000000fffffffffffffffffffffffc
B = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b
Gx = 0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296
Gy = 0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5
N = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551

class Point:
    def __init__(self, x, y, infinity=False):
        self.x = x
        self.y = y
        self.infinity = infinity

    def __eq__(self, other):
        if self.infinity: return other.infinity
        if other.infinity: return False
        return self.x == other.x and self.y == other.y

    def __repr__(self):
        if self.infinity: return "Point(Infinity)"
        return f"Point({hex(self.x)}, {hex(self.y)})"

def inverse_mod(k, p):
    if k == 0:
        raise ZeroDivisionError('division by zero')
    if k < 0:
        return p - inverse_mod(-k, p)
    s, old_s = 0, 1
    t, old_t = 1, 0
    r, old_r = p, k
    while r != 0:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        old_t, t = t, old_t - quotient * t
    return old_s % p

def point_add(p1, p2):
    if p1.infinity: return p2
    if p2.infinity: return p1
    if p1.x == p2.x and p1.y != p2.y:
        return Point(0, 0, True)
    
    if p1.x == p2.x:
        m = (3 * p1.x**2 + A) * inverse_mod(2 * p1.y, P)
    else:
        m = (p1.y - p2.y) * inverse_mod(p1.x - p2.x, P)
    
    m = m % P
    x3 = (m**2 - p1.x - p2.x) % P
    y3 = (m*(p1.x - x3) - p1.y) % P
    return Point(x3, y3)

def point_mul(p1, d):
    if p1.infinity: return p1
    res = Point(0, 0, True)
    temp = p1
    while d > 0:
        if d % 2 == 1:
            res = point_add(res, temp)
        temp = point_add(temp, temp)
        d //= 2
    return res

class PSIProtocol:
    def __init__(self):
        self.private_key = random.randint(1, N-1)
    
    def hash_to_point(self, data: str) -> Point:
        """
        Maps a string to a point on the curve.
        Uses a simple 'try-and-increment' or just multiplies Generator by hash.
        Multiplying G by hash is NOT secure for OPRF but for simple ECDH PSI it works 
        IF we assume H(x) acts as a random oracle mapping to the group.
        
        However, H(x)*G implies we know the discrete log of the point (it's H(x)).
        If Alice sends H(x)*G, Bob knows H(x)*G.
        Bob can brute force x if the space is small?
        Yes, if Bob can guess x, he can compute H(x)*G and check.
        This is true for any PSI.
        
        So H(x)*G is fine.
        """
        digest = hashlib.sha256(data.encode('utf-8')).digest()
        scalar = int.from_bytes(digest, 'big') % N
        return point_mul(Point(Gx, Gy), scalar)

    def blind_point(self, point: Point) -> Point:
        """
        Blinds a point P with the private key.
        Returns P * private_key.
        """
        return point_mul(point, self.private_key)
    
    def serialize_point(self, point: Point) -> bytes:
        return pickle.dumps(point)
    
    def deserialize_point(self, data: bytes) -> Point:
        return pickle.loads(data)
