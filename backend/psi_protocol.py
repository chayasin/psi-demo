import hashlib
import pickle
import tenseal as ts
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# SECP256R1 Curve Parameters (for manual point reconstruction)
P = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff
A = -3
B = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b

class PSIProtocol:
    def __init__(self):
        self.curve = ec.SECP256R1()
        self.private_key = ec.generate_private_key(self.curve)

    def hash_to_curve_public_key(self, data: str) -> ec.EllipticCurvePublicKey:
        """
        Maps a string to a PublicKey on the curve. This is effectively H(x) * G.
        """
        digest = hashes.Hash(hashes.SHA256())
        digest.update(data.encode('utf-8'))
        h = digest.finalize()
        scalar = int.from_bytes(h, 'big')
        N = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551
        scalar = scalar % N
        return ec.derive_private_key(scalar, self.curve, default_backend()).public_key()

    def apply_private_key(self, public_key_or_point_bytes) -> bytes:
        """
        Performs ECDH: Returns x-coordinate of (MyPriv * InputPub).
        Result is bytes.
        """
        if isinstance(public_key_or_point_bytes, bytes):
            public_key = self._bytes_to_public_key(public_key_or_point_bytes)
        else:
            public_key = public_key_or_point_bytes

        shared_key = self.private_key.exchange(ec.ECDH(), public_key)
        return shared_key

    def _bytes_to_public_key(self, x_bytes: bytes) -> ec.EllipticCurvePublicKey:
        """
        Reconstructs a PublicKey from just the X-coordinate bytes.
        Solves y^2 = x^3 + ax + b for y.
        """
        x = int.from_bytes(x_bytes, 'big')
        rhs = (pow(x, 3, P) + A*x + B) % P
        y = pow(rhs, (P + 1) // 4, P)

        if (y*y) % P != rhs:
            raise ValueError("Point not on curve")

        public_numbers = ec.EllipticCurvePublicNumbers(x, y, self.curve)
        return public_numbers.public_key(default_backend())

    def serialize(self, val) -> bytes:
        if isinstance(val, bytes):
            return val
        return pickle.dumps(val)

    def deserialize(self, data: bytes):
        return pickle.loads(data)

class SecureAggregator:
    def __init__(self):
        pass

    @staticmethod
    def create_context():
        context = ts.context(
            ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=8192,
            coeff_mod_bit_sizes=[60, 40, 40, 60]
        )
        context.global_scale = 2**40
        context.generate_galois_keys()
        return context

    @staticmethod
    def encrypt_vector(context, vector: list):
        return ts.ckks_vector(context, vector)

    @staticmethod
    def deserialize_context(data: bytes):
        return ts.context_from(data)

    @staticmethod
    def deserialize_vector(context, data: bytes):
        return ts.ckks_vector_from(context, data)
