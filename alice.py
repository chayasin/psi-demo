import socket
import pandas as pd
from psi_protocol import PSIProtocol, SecureAggregator
from data_generator import generate_data
import network_utils
from tqdm import tqdm
import time
import tenseal as ts

class AliceClient:
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.socket = None
        self.psi = PSIProtocol()
        self.df_alice = None
        self.intersection_ids = []
        self.joined_data = None
        self.aggregated_data = None
        self.logs = []

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        print(entry)
        self.logs.append(entry)

    def generate_data(self):
        self.log("Generating data for Alice...")
        self.df_alice, _ = generate_data()
        self.log(f"Alice has {len(self.df_alice)} rows.")
        return self.df_alice

    def connect(self):
        self.log(f"Connecting to Bob at {self.host}:{self.port}...")
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.log("Connected successfully.")
            return True
        except Exception as e:
            self.log(f"Connection failed: {e}")
            return False

    def run_psi(self, progress_callback=None):
        if not self.socket:
            self.log("Not connected.")
            return None

        self.log("Starting PSI Protocol (Optimized Cryptography)...")
        alice_ids = self.df_alice["ID"].tolist()
        
        # 1. Blind Items (H(x)^a)
        # Note: In optimized protocol, this is ECDH half-step: a * H(x)
        alice_blinded = []
        total = len(alice_ids)
        for i, uid in enumerate(alice_ids):
            # Map to curve
            pt = self.psi.hash_to_curve_public_key(uid)
            # Apply private key (ECDH) -> returns x-coord bytes
            blinded = self.psi.apply_private_key(pt)
            alice_blinded.append(blinded)
            if progress_callback and i % 10 == 0:
                progress_callback(i / total)
        
        if progress_callback: progress_callback(1.0)

        # 2. Send to Bob
        self.log("Sending blinded items to Bob...")
        network_utils.send_msg(self.socket, {"command": "PSI", "points": alice_blinded})
        
        # 3. Receive A^b (Alice's items blinded by Bob)
        self.log("Waiting for Bob's response...")
        msg = network_utils.recv_msg(self.socket)
        alice_blinded_by_bob = msg["points"]
        
        # 4. Receive B^b (Bob's items blinded by Bob)
        # Bob calculates H(y)^b and sends it.
        # Actually Bob sends H(y)^b. Alice computes (H(y)^b)^a.
        msg = network_utils.recv_msg(self.socket)
        bob_blinded = msg["points"]
        
        # 5. Compute B^ba = (H(y)^b)^a
        self.log("Computing final intersection...")
        bob_blinded_by_alice = []
        for p in bob_blinded:
            # p is x-coord bytes from Bob.
            # We treat it as public key and apply 'a'.
            val = self.psi.apply_private_key(p)
            bob_blinded_by_alice.append(val)
        
        # 6. Intersect
        # Intersection is where A^ab == B^ba ?
        # Alice sent A^a. Bob returned (A^a)^b = A^ab.
        # Bob sent B^b. Alice computed (B^b)^a = B^ba.
        # If A=B, then A^ab == B^ba (commutativity).
        
        bob_set = set(bob_blinded_by_alice)
            
        self.intersection_ids = []
        for i, val in enumerate(alice_blinded_by_bob):
            if val in bob_set:
                self.intersection_ids.append(alice_ids[i])
        
        self.log(f"Intersection found: {len(self.intersection_ids)} items.")
        return self.intersection_ids

    def run_join(self):
        if not self.socket or not self.intersection_ids:
            self.log("Cannot join: No connection or no intersection.")
            return None

        self.log("Requesting data for intersection...")
        network_utils.send_msg(self.socket, {"command": "JOIN", "ids": self.intersection_ids})
        
        msg = network_utils.recv_msg(self.socket)
        bob_data = msg["data"]
        self.log(f"Received {len(bob_data)} records from Bob.")
        
        df_bob_data = pd.DataFrame(bob_data)
        if not df_bob_data.empty:
            self.joined_data = pd.merge(self.df_alice, df_bob_data, on="ID")
        else:
             self.joined_data = self.df_alice[self.df_alice["ID"].isin(self.intersection_ids)]
             
        return self.joined_data

    def run_aggregation(self):
        if self.joined_data is None:
            self.log("Cannot aggregate: No joined data.")
            return None

        self.log("Aggregating data...")
        self.joined_data["TotalComp"] = self.joined_data["Salary"] + self.joined_data["Bonus"]
        self.aggregated_data = self.joined_data.groupby("Department")["TotalComp"].sum().reset_index()
        return self.aggregated_data

    def run_secure_aggregation(self, progress_callback=None):
        if not self.socket or not self.intersection_ids:
            self.log("Cannot run secure aggregation: No connection or no intersection.")
            return None

        self.log("Starting Secure Aggregation (TenSEAL CKKS)...")
        
        # 1. Generate Context
        context = SecureAggregator.create_context()
        
        # 2. Prepare Data
        # Sort IDs to ensure alignment
        sorted_ids = sorted(self.intersection_ids)
        alice_subset = self.df_alice[self.df_alice["ID"].isin(sorted_ids)].set_index("ID")
        alice_subset = alice_subset.reindex(sorted_ids)
        salaries = alice_subset["Salary"].tolist()
        
        # 3. Encrypt Vector
        self.log(f"Encrypting {len(salaries)} salaries...")
        enc_salaries = SecureAggregator.encrypt_vector(context, salaries)
        
        # 4. Send to Bob
        self.log("Sending Encrypted Vectors to Bob...")
        payload = {
            "command": "SECURE_AGGREGATION",
            "context": context.serialize(save_secret_key=False),
            "enc_salaries": enc_salaries.serialize(),
            "ids": sorted_ids # Necessary for alignment
        }
        network_utils.send_msg(self.socket, payload)
        
        # 5. Receive Results
        self.log("Waiting for Bob's Aggregation...")
        msg = network_utils.recv_msg(self.socket)
        serialized_results = msg["results"]
        
        # 6. Decrypt
        self.log("Decrypting Results...")
        decrypted_results = []
        
        for dept, enc_sum_bytes in serialized_results.items():
            enc_sum = ts.ckks_vector_from(context, enc_sum_bytes)
            # Decrypt returns a list (vector). Since we summed to a single value (conceptually)
            # Or if Bob summed by mask, the result likely has the sum in the first slot or as a single element vector?
            # If Bob did 'sum()', it returns a CKKSVector with 1 element.
            val = enc_sum.decrypt()[0]
            decrypted_results.append({"Department": dept, "TotalComp": val})
            
        self.aggregated_data = pd.DataFrame(decrypted_results)
        self.log("Secure Aggregation Complete.")
        return self.aggregated_data

    def close(self):
        if self.socket:
            network_utils.send_msg(self.socket, {"command": "EXIT"})
            self.socket.close()
            self.socket = None
            self.log("Disconnected.")

# For backward compatibility
if __name__ == "__main__":
    client = AliceClient()
    client.generate_data()
    if client.connect():
        client.run_psi()
        client.run_join()
        print(client.run_aggregation())
        client.close()
