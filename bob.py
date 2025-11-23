import socket
import pandas as pd
from psi_protocol import PSIProtocol
from data_generator import generate_data
import network_utils
from tqdm import tqdm
import threading
import time
import phe.paillier as paillier

class BobServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.thread = None
        self.psi = PSIProtocol()
        self.df_bob = None
        self.logs = []

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        print(entry)
        self.logs.append(entry)

    def generate_data(self):
        self.log("Generating data for Bob...")
        _, self.df_bob = generate_data()
        self.log(f"Bob has {len(self.df_bob)} rows.")
        return self.df_bob

    def start(self):
        if self.running:
            return
        
        if self.df_bob is None:
            self.generate_data()

        self.running = True
        self.thread = threading.Thread(target=self._listen_loop)
        self.thread.daemon = True
        self.thread.start()
        self.log(f"Server started on {self.host}:{self.port}")

    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.log("Server stopped.")

    def _listen_loop(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                self.socket = s
                s.bind((self.host, self.port))
                s.listen()
                
                while self.running:
                    try:
                        s.settimeout(1.0) # Check running flag every second
                        conn, addr = s.accept()
                        self.log(f"Connected by {addr}")
                        t = threading.Thread(target=self._handle_client, args=(conn, addr))
                        t.start()
                    except socket.timeout:
                        continue
                    except OSError:
                        break
        except Exception as e:
            self.log(f"Server Error: {e}")
        finally:
            self.running = False

    def _handle_client(self, conn, addr):
        try:
            while True:
                msg = network_utils.recv_msg(conn)
                if not msg:
                    break
                
                command = msg.get("command")
                
                if command == "PSI":
                    self.log(f"PSI Request from {addr}")
                    alice_points = msg.get("points")
                    
                    # Compute A^b
                    alice_blinded_by_bob = [self.psi.blind_point(p) for p in alice_points]
                    network_utils.send_msg(conn, {"points": alice_blinded_by_bob})
                    
                    # Send B = H(y)^b
                    bob_ids = self.df_bob["ID"].tolist()
                    bob_points = [self.psi.hash_to_point(uid) for uid in bob_ids]
                    bob_blinded = [self.psi.blind_point(p) for p in bob_points]
                    network_utils.send_msg(conn, {"points": bob_blinded})
                    self.log(f"PSI Protocol completed for {addr}")
                    
                elif command == "JOIN":
                    self.log(f"JOIN Request from {addr}")
                    ids_to_join = msg.get("ids")
                    mask = self.df_bob["ID"].isin(ids_to_join)
                    joined_data = self.df_bob[mask].to_dict('records')
                    network_utils.send_msg(conn, {"data": joined_data})
                    self.log(f"Sent {len(joined_data)} records to {addr}")

                elif command == "SECURE_AGGREGATION":
                    self.log(f"SECURE_AGGREGATION Request from {addr}")
                    # Receive public key and encrypted data
                    pub_key_data = msg.get("public_key")
                    public_key = paillier.PaillierPublicKey(n=pub_key_data['n'])
                    
                    encrypted_salaries_data = msg.get("encrypted_salaries")
                    # Reconstruct EncryptedNumber objects
                    encrypted_salaries = {}
                    for uid, enc_val in encrypted_salaries_data.items():
                        encrypted_salaries[uid] = paillier.EncryptedNumber(public_key, int(enc_val))
                    
                    self.log(f"Received {len(encrypted_salaries)} encrypted salaries.")
                    
                    # Perform Homomorphic Addition: Enc(Salary) + Bonus
                    # We need to match IDs.
                    # df_bob has ID, Department, Bonus
                    
                    # Filter Bob's data to only those in the encrypted list
                    mask = self.df_bob["ID"].isin(encrypted_salaries.keys())
                    bob_subset = self.df_bob[mask]
                    
                    # Group by Department
                    grouped_sums = {} # Department -> EncryptedSum
                    
                    count = 0
                    for index, row in bob_subset.iterrows():
                        uid = row["ID"]
                        department = row["Department"]
                        bonus = row["Bonus"]
                        
                        if uid in encrypted_salaries:
                            enc_salary = encrypted_salaries[uid]
                            # Homomorphic Addition: Enc(Salary) + Bonus
                            enc_total = enc_salary + bonus
                            
                            if department not in grouped_sums:
                                grouped_sums[department] = enc_total
                            else:
                                grouped_sums[department] = grouped_sums[department] + enc_total
                            count += 1
                            
                    self.log(f"Aggregated {count} records into {len(grouped_sums)} departments.")
                    
                    # Serialize results
                    # We send back the ciphertext (integer)
                    serialized_results = {dept: str(enc_sum.ciphertext()) for dept, enc_sum in grouped_sums.items()}
                    
                    network_utils.send_msg(conn, {"results": serialized_results})
                    self.log("Sent aggregated results to Alice.")
                    
                elif command == "EXIT":
                    self.log(f"Client {addr} disconnected.")
                    break
                    
        except Exception as e:
            self.log(f"Error handling client {addr}: {e}")
        finally:
            conn.close()

# For backward compatibility if run directly
if __name__ == "__main__":
    server = BobServer()
    server.generate_data()
    server.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
