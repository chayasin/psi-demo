import socket
import pandas as pd
from psi_protocol import PSIProtocol
from data_generator import generate_data
import network_utils
from tqdm import tqdm
import time

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

        self.log("Starting PSI Protocol...")
        alice_ids = self.df_alice["ID"].tolist()
        
        # 1. Blind Items
        alice_points = []
        total = len(alice_ids)
        for i, uid in enumerate(alice_ids):
            pt = self.psi.hash_to_point(uid)
            blinded = self.psi.blind_point(pt)
            alice_points.append(blinded)
            if progress_callback and i % 10 == 0:
                progress_callback(i / total)
        
        if progress_callback: progress_callback(1.0)

        # 2. Send to Bob
        self.log("Sending blinded items to Bob...")
        network_utils.send_msg(self.socket, {"command": "PSI", "points": alice_points})
        
        # 3. Receive A^b
        self.log("Waiting for Bob's response...")
        msg = network_utils.recv_msg(self.socket)
        alice_blinded_by_bob = msg["points"]
        
        # 4. Receive B
        msg = network_utils.recv_msg(self.socket)
        bob_blinded = msg["points"]
        
        # 5. Compute B^a
        self.log("Computing final intersection...")
        bob_blinded_by_alice = [self.psi.blind_point(p) for p in bob_blinded]
        
        # 6. Intersect
        bob_set = set()
        for p in bob_blinded_by_alice:
            bob_set.add(self.psi.serialize_point(p))
            
        self.intersection_ids = []
        for i, p in enumerate(alice_blinded_by_bob):
            serialized = self.psi.serialize_point(p)
            if serialized in bob_set:
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
        self.joined_data = pd.merge(self.df_alice, df_bob_data, on="ID")
        return self.joined_data

    def run_aggregation(self):
        if self.joined_data is None:
            self.log("Cannot aggregate: No joined data.")
            return None

        self.log("Aggregating data...")
        self.joined_data["TotalComp"] = self.joined_data["Salary"] + self.joined_data["Bonus"]
        self.aggregated_data = self.joined_data.groupby("Department")["TotalComp"].sum().reset_index()
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
