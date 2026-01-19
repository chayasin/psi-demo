import socket
import pandas as pd
from psi_protocol import PSIProtocol, SecureAggregator
from data_generator import generate_data
import network_utils
from tqdm import tqdm
import threading
import time
import tenseal as ts

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
                # Allow address reuse
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
                    alice_blinded = msg.get("points")
                    
                    # Compute A^b (Alice's items blinded by Bob)
                    alice_blinded_by_bob = []
                    for p in alice_blinded:
                         # p is x-coord bytes. Treat as PubKey.
                         res = self.psi.apply_private_key(p)
                         alice_blinded_by_bob.append(res)

                    network_utils.send_msg(conn, {"points": alice_blinded_by_bob})
                    
                    # Send B^b = H(y)^b
                    bob_ids = self.df_bob["ID"].tolist()
                    bob_points = [self.psi.hash_to_curve_public_key(uid) for uid in bob_ids]
                    bob_blinded = [self.psi.apply_private_key(p) for p in bob_points]
                    
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
                    
                    # Deserialize Context and Vector
                    context = SecureAggregator.deserialize_context(msg.get("context"))
                    enc_salaries = SecureAggregator.deserialize_vector(context, msg.get("enc_salaries"))
                    ids = msg.get("ids") # Alignment list
                    
                    self.log(f"Received encrypted salary vector size: {len(ids)}")
                    
                    # Prepare Bob's Bonuses aligned
                    bob_subset = self.df_bob[self.df_bob["ID"].isin(ids)].set_index("ID")
                    bob_subset = bob_subset.reindex(ids)
                    bonuses = bob_subset["Bonus"].tolist()
                    departments = bob_subset["Department"].tolist()
                    
                    # Homomorphic Addition: Enc(Salary) + Bonus
                    enc_total = enc_salaries + bonuses
                    
                    # Aggregate by Department
                    grouped_sums = {}
                    unique_depts = set(departments)
                    
                    for dept in unique_depts:
                         # Create mask for this department
                         mask = [1 if d == dept else 0 for d in departments]
                         # Enc(Total) * Mask -> keeps only dept values, others 0
                         # Sum() -> Sum of dept values
                         enc_dept = enc_total * mask
                         enc_dept_sum = enc_dept.sum()
                         
                         grouped_sums[dept] = enc_dept_sum.serialize()
                         
                    self.log(f"Aggregated records into {len(grouped_sums)} departments.")
                    
                    network_utils.send_msg(conn, {"results": grouped_sums})
                    self.log("Sent aggregated results to Alice.")
                    
                elif command == "EXIT":
                    self.log(f"Client {addr} disconnected.")
                    break
                    
        except Exception as e:
            self.log(f"Error handling client {addr}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()

# For backward compatibility if run directly
if __name__ == "__main__":
    server = BobServer()
    server.generate_data()
    server.start()
    try:
        while True:
            # Keep main thread alive
            time.sleep(1)
            if not server.running:
                break
    except KeyboardInterrupt:
        server.stop()
