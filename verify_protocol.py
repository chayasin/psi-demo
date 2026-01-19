from psi_protocol import PSIProtocol, SecureAggregator
import tenseal as ts
import pandas as pd

def test_psi():
    print("Testing PSI Logic...")
    alice = PSIProtocol()
    bob = PSIProtocol()
    
    # Alice Set: [1, 2, 3]
    # Bob Set: [2, 3, 4]
    # Intersection: [2, 3]
    
    alice_items = ["1", "2", "3"]
    bob_items = ["2", "3", "4"]
    
    # 1. Alice Blinds (a * H(x))
    print("Alice computes a*H(x)...")
    alice_blinded = []
    for x in alice_items:
        pt = alice.hash_to_curve_public_key(x)
        blinded = alice.apply_private_key(pt)
        alice_blinded.append(blinded)
        
    # 2. Bob receives a*H(x). Computes b*(a*H(x)).
    print("Bob computes b*(a*H(x))...")
    alice_blinded_by_bob = []
    for p in alice_blinded:
        res = bob.apply_private_key(p)
        alice_blinded_by_bob.append(res)
        
    # 3. Bob sends b*H(y).
    print("Bob computes b*H(y)...")
    bob_blinded = []
    for y in bob_items:
        pt = bob.hash_to_curve_public_key(y)
        blinded = bob.apply_private_key(pt)
        bob_blinded.append(blinded)
        
    # 4. Alice receives b*H(y). Computes a*(b*H(y)).
    print("Alice computes a*(b*H(y))...")
    bob_blinded_by_alice = []
    for p in bob_blinded:
        res = alice.apply_private_key(p)
        bob_blinded_by_alice.append(res)
        
    # 5. Intersect
    bob_set = set(bob_blinded_by_alice)
    intersection = []
    for i, val in enumerate(alice_blinded_by_bob):
        if val in bob_set:
            intersection.append(alice_items[i])
            
    print(f"Intersection: {intersection}")
    assert set(intersection) == {"2", "3"}
    print("PSI Test Passed!")

def test_aggregation():
    print("Testing Secure Aggregation Logic...")
    context = SecureAggregator.create_context()
    
    # Alice Salaries: [100, 200]
    alice_salaries = [100.0, 200.0]
    enc_salaries = SecureAggregator.encrypt_vector(context, alice_salaries)
    
    # Send enc_salaries to Bob
    serialized_enc = enc_salaries.serialize()
    
    # Bob receives
    enc_received = SecureAggregator.deserialize_vector(context, serialized_enc)
    
    # Bob Bonuses: [10, 20]
    bob_bonuses = [10.0, 20.0]
    
    # Add
    enc_total = enc_received + bob_bonuses
    
    # Bob Departments: ["HR", "HR"]
    # Sum both for "HR"
    mask = [1, 1]
    enc_dept = enc_total * mask
    enc_sum = enc_dept.sum()
    
    # Send back
    serialized_sum = enc_sum.serialize()
    
    # Alice decrypts
    enc_res = ts.ckks_vector_from(context, serialized_sum)
    decrypted = enc_res.decrypt()[0]
    
    print(f"Decrypted Sum: {decrypted}")
    expected = (100+10) + (200+20) # 330
    import math
    assert math.isclose(decrypted, expected, abs_tol=0.1)
    print("Aggregation Test Passed!")

if __name__ == "__main__":
    test_psi()
    test_aggregation()
