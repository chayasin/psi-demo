import pandas as pd
import random
import string

def generate_data(num_rows=1000, overlap_ratio=0.5, seed=42):
    """
    Generates data for Alice and Bob.
    Returns two DataFrames: df_alice, df_bob
    """
    random.seed(seed)
    
    # Total unique IDs needed
    # Overlap = 1000 * 0.5 = 500
    # Alice unique = 500
    # Bob unique = 500
    # Total = 1500
    
    num_overlap = int(num_rows * overlap_ratio)
    num_unique_alice = num_rows - num_overlap
    num_unique_bob = num_rows - num_overlap
    
    # Generate IDs
    def random_id():
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@example.com"
    
    common_ids = [random_id() for _ in range(num_overlap)]
    alice_only_ids = [random_id() for _ in range(num_unique_alice)]
    bob_only_ids = [random_id() for _ in range(num_unique_bob)]
    
    alice_ids = common_ids + alice_only_ids
    bob_ids = common_ids + bob_only_ids
    
    # Shuffle
    random.shuffle(alice_ids)
    random.shuffle(bob_ids)
    
    # Create Alice Data
    # Columns: ID, Name, Age, Salary
    alice_data = []
    for uid in alice_ids:
        alice_data.append({
            "ID": uid,
            "Name": ''.join(random.choices(string.ascii_uppercase, k=5)),
            "Age": random.randint(20, 60),
            "Salary": random.randint(30000, 150000)
        })
    
    # Create Bob Data
    # Columns: ID, Department, Bonus
    bob_data = []
    departments = ["HR", "Engineering", "Sales", "Marketing", "Finance"]
    for uid in bob_ids:
        bob_data.append({
            "ID": uid,
            "Department": random.choice(departments),
            "Bonus": random.randint(1000, 20000)
        })
        
    df_alice = pd.DataFrame(alice_data)
    df_bob = pd.DataFrame(bob_data)
    
    return df_alice, df_bob

if __name__ == "__main__":
    a, b = generate_data()
    print(f"Alice: {len(a)} rows")
    print(f"Bob: {len(b)} rows")
    print("Sample Alice:", a.head())
    print("Sample Bob:", b.head())
