# Private Set Intersection (PSI) Demo

This repository demonstrates a **Private Set Intersection (PSI)** protocol between two parties, **Alice** and **Bob**, using Python. It showcases how two parties can collaborate on data without revealing their full datasets to each other.

## Overview

- **Alice (Client)**: Has a dataset of employees with `Name`, `Age`, and `Salary`.
- **Bob (Server)**: Has a dataset of employees with `Department` and `Bonus`.
- **Goal**: Find common employees (by ID) and perform operations on them without sharing non-intersecting data.

## Scenarios

### 1. Basic Intersection (Who do we both have?)
**Goal**: Find the list of IDs that exist in both Alice's and Bob's datasets.

**How it works (ECDH Protocol)**:
We use an Elliptic Curve Diffie-Hellman (ECDH) approach to perform a "Double Blinding" comparison.
1.  **Alice** hashes her IDs and "blinds" them with her secret key $a$: $H(x)^a$. She sends these to Bob.
2.  **Bob** blinds Alice's received items with his secret key $b$: $(H(x)^a)^b = H(x)^{ab}$. He sends these back to Alice.
3.  **Bob** also hashes his own IDs and blinds them with his secret key $b$: $H(y)^b$. He sends these to Alice.
4.  **Alice** blinds Bob's received items with her secret key $a$: $(H(y)^b)^a = H(y)^{ba}$.
5.  **Comparison**: Since multiplication is commutative ($ab = ba$), if an ID is the same ($x=y$), then $H(x)^{ab} = H(y)^{ba}$. Alice compares the two sets of double-blinded values to find matches.

**Privacy**: Bob never sees Alice's IDs (only blinded values). Alice never sees Bob's non-intersecting IDs (only blinded values).

---

### 2. Intersection with Data Join (Enriching Data)
**Goal**: Alice wants to add Bob's `Department` and `Bonus` information to the employees they have in common.

**How it works**:
1.  **Alice** performs Scenario 1 to find the intersecting IDs.
2.  **Alice** sends the list of *only* the intersecting IDs to Bob.
3.  **Bob** looks up the data for those specific IDs and sends the `Department` and `Bonus` back to Alice.
4.  **Alice** merges this new data with her local `Name` and `Salary` data.

**Privacy**: Bob learns which IDs are in the intersection (because Alice asks for them). He does *not* learn about Alice's other employees.

---

### 3. Secure Aggregation (Privacy-Preserving Analytics)
**Goal**: Alice wants to know the **Total Compensation** (Salary + Bonus) per Department, but **neither party wants to reveal individual salary or bonus amounts**.

**How it works (Paillier Homomorphic Encryption)**:
We use the Paillier cryptosystem, which allows addition of encrypted numbers: $Enc(A) + B = Enc(A + B)$.
1.  **Alice** generates a public/private key pair.
2.  **Alice** encrypts her `Salary` for the intersecting employees: $Enc(Salary)$. She sends these to Bob along with her public key.
3.  **Bob** takes each encrypted salary and adds his local `Bonus` to it homomorphically: $Enc(Salary) + Bonus = Enc(Salary + Bonus)$.
4.  **Bob** groups these encrypted totals by `Department` and sums them up (also homomorphically).
5.  **Bob** sends the final *encrypted* sums for each department to Alice.
6.  **Alice** decrypts the sums using her private key to get the final result.

**Privacy**:
- **Bob** sees encrypted salaries but cannot decrypt them. He doesn't know Alice's salary data.
- **Alice** receives only the final aggregated totals. She doesn't know Bob's individual bonuses.

## Usage

### Prerequisites
```bash
pip install -r requirements.txt
```

### Running with UI (Recommended)
1.  **Start Bob (Server)**:
    ```bash
    streamlit run bob_app.py --server.port 8503
    ```
2.  **Start Alice (Client)**:
    ```bash
    streamlit run alice_app.py --server.port 8504
    ```
3.  Open Alice's URL (e.g., `http://localhost:8504`), connect to Bob, and click the buttons to run each scenario.

### Running via CLI
```bash
# Terminal 1
python bob.py

# Terminal 2
python alice.py
```

## Mathematical Details

### 1. ECDH PSI (Private Set Intersection)
This protocol relies on the **commutative property** of scalar multiplication on Elliptic Curves.

Let $G$ be a generator point on an elliptic curve $E$.
Let $a$ be Alice's private key (a random scalar).
Let $b$ be Bob's private key (a random scalar).
Let $H(x)$ be a hash function that maps an input $x$ to a point on the curve.

1.  **Alice** computes $P_a = a \cdot H(x)$ for each item $x$ in her set.
2.  **Bob** receives $P_a$ and computes $P_{ab} = b \cdot P_a = b \cdot (a \cdot H(x))$.
    *   Due to associativity/commutativity: $b \cdot a \cdot H(x) = (ab) \cdot H(x)$.
3.  **Bob** computes $P_b = b \cdot H(y)$ for each item $y$ in his set.
4.  **Alice** receives $P_b$ and computes $P_{ba} = a \cdot P_b = a \cdot (b \cdot H(y))$.
    *   Similarly: $a \cdot b \cdot H(y) = (ab) \cdot H(y)$.

**Conclusion**: If Alice has item $x$ and Bob has item $y$, and $x = y$, then:
$$P_{ab} = (ab) \cdot H(x) = (ab) \cdot H(y) = P_{ba}$$
Alice can simply check if any of her double-blinded points ($P_{ab}$) match any of the double-blinded points she computed from Bob ($P_{ba}$).

### 2. Paillier Homomorphic Encryption (Secure Aggregation)
The Paillier cryptosystem is an additive homomorphic encryption scheme.

Let $n = p \cdot q$ be the product of two large primes.
Let $g$ be a generator.
Public Key: $(n, g)$. Private Key: $(\lambda, \mu)$.

**Encryption**:
To encrypt a message $m$ with random $r$:
$$c = g^m \cdot r^n \mod n^2$$

**Homomorphic Addition**:
Given two ciphertexts $c_1 = E(m_1)$ and $c_2 = E(m_2)$:
$$c_1 \cdot c_2 = (g^{m_1} r_1^n) \cdot (g^{m_2} r_2^n) = g^{m_1+m_2} (r_1 r_2)^n \mod n^2$$
$$c_1 \cdot c_2 = E(m_1 + m_2)$$
*Multiplying ciphertexts results in the encryption of the sum of the plaintexts.*

**Homomorphic Multiplication by Scalar**:
Given ciphertext $c = E(m)$ and a scalar $k$:
$$c^k = (g^m r^n)^k = g^{mk} (r^k)^n \mod n^2$$
$$c^k = E(m \cdot k)$$
*Raising a ciphertext to a scalar power results in the encryption of the product.*

**In our Scenario**:
Alice sends $c_{salary} = E(Salary)$.
Bob computes $c_{total} = c_{salary} \cdot E(Bonus) = E(Salary + Bonus)$.
Bob sums these up for the department: $C_{final} = \prod c_{total_i} = E(\sum (Salary_i + Bonus_i))$.
Alice decrypts $C_{final}$ to get the total compensation.
