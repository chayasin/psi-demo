import time
import pandas as pd
import tenseal as ts
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from psi_protocol import PSIProtocol, SecureAggregator
from data_generator import generate_data

app = FastAPI(title="PSI Demo API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory session state (single-user demo)
# ---------------------------------------------------------------------------

class SessionState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.df_alice: pd.DataFrame | None = None
        self.df_bob: pd.DataFrame | None = None
        self.alice_psi = None  # PSIProtocol instance for Alice
        self.bob_psi = None    # PSIProtocol instance for Bob
        self.intersection_ids: list[str] = []
        self.joined_data: pd.DataFrame | None = None
        self.aggregated_data: pd.DataFrame | None = None
        self.logs: list[str] = []

    def log(self, message: str):
        ts_str = time.strftime("%H:%M:%S")
        self.logs.append(f"[{ts_str}] {message}")


state = SessionState()

# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class StatusResponse(BaseModel):
    data_generated: bool
    alice_rows: int
    bob_rows: int
    intersection_size: int
    has_joined_data: bool
    has_aggregated_data: bool
    logs: list[str]


class GenerateDataResponse(BaseModel):
    alice_rows: int
    bob_rows: int
    alice_columns: list[str]
    bob_columns: list[str]
    alice_sample: list[dict]
    bob_sample: list[dict]


class PSIResponse(BaseModel):
    intersection_size: int
    sample_ids: list[str]
    alice_total: int
    bob_total: int


class JoinResponse(BaseModel):
    row_count: int
    columns: list[str]
    data: list[dict]


class AggregationResponse(BaseModel):
    departments: list[dict]
    secure: bool

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/status", response_model=StatusResponse)
def get_status():
    return StatusResponse(
        data_generated=state.df_alice is not None,
        alice_rows=len(state.df_alice) if state.df_alice is not None else 0,
        bob_rows=len(state.df_bob) if state.df_bob is not None else 0,
        intersection_size=len(state.intersection_ids),
        has_joined_data=state.joined_data is not None,
        has_aggregated_data=state.aggregated_data is not None,
        logs=state.logs,
    )


@app.post("/api/reset")
def reset_session():
    state.reset()
    state.log("Session reset.")
    return {"message": "Session reset successfully."}


@app.post("/api/generate-data", response_model=GenerateDataResponse)
def generate_data_endpoint():
    state.reset()
    state.log("Generating data for Alice and Bob...")
    df_alice, df_bob = generate_data()
    state.df_alice = df_alice
    state.df_bob = df_bob
    state.alice_psi = PSIProtocol()
    state.bob_psi = PSIProtocol()
    state.log(f"Alice has {len(df_alice)} rows, Bob has {len(df_bob)} rows.")
    return GenerateDataResponse(
        alice_rows=len(df_alice),
        bob_rows=len(df_bob),
        alice_columns=list(df_alice.columns),
        bob_columns=list(df_bob.columns),
        alice_sample=df_alice.head(10).to_dict("records"),
        bob_sample=df_bob.head(10).to_dict("records"),
    )


@app.post("/api/run-psi", response_model=PSIResponse)
def run_psi():
    if state.df_alice is None or state.df_bob is None:
        raise HTTPException(status_code=400, detail="Generate data first.")

    state.log("Starting PSI Protocol (ECDH)...")

    alice_psi = state.alice_psi
    bob_psi = state.bob_psi
    alice_ids = state.df_alice["ID"].tolist()
    bob_ids = state.df_bob["ID"].tolist()

    # Step 1: Alice blinds her items — H(x)^a
    state.log("Alice: Hashing and blinding IDs...")
    alice_blinded = []
    for uid in alice_ids:
        pt = alice_psi.hash_to_curve_public_key(uid)
        blinded = alice_psi.apply_private_key(pt)
        alice_blinded.append(blinded)

    # Step 2: Bob double-blinds Alice's items — (H(x)^a)^b
    state.log("Bob: Double-blinding Alice's items...")
    alice_double_blinded = []
    for p in alice_blinded:
        res = bob_psi.apply_private_key(p)
        alice_double_blinded.append(res)

    # Step 3: Bob blinds his own items — H(y)^b
    state.log("Bob: Hashing and blinding own IDs...")
    bob_blinded = []
    for uid in bob_ids:
        pt = bob_psi.hash_to_curve_public_key(uid)
        blinded = bob_psi.apply_private_key(pt)
        bob_blinded.append(blinded)

    # Step 4: Alice double-blinds Bob's items — (H(y)^b)^a
    state.log("Alice: Double-blinding Bob's items...")
    bob_double_blinded = []
    for p in bob_blinded:
        val = alice_psi.apply_private_key(p)
        bob_double_blinded.append(val)

    # Step 5: Find intersection — compare H(x)^ab with H(y)^ba
    state.log("Computing intersection...")
    bob_set = set(bob_double_blinded)
    intersection_ids = []
    for i, val in enumerate(alice_double_blinded):
        if val in bob_set:
            intersection_ids.append(alice_ids[i])

    state.intersection_ids = intersection_ids
    state.joined_data = None
    state.aggregated_data = None
    state.log(f"Intersection found: {len(intersection_ids)} common IDs out of Alice={len(alice_ids)}, Bob={len(bob_ids)}.")

    return PSIResponse(
        intersection_size=len(intersection_ids),
        sample_ids=intersection_ids[:10],
        alice_total=len(alice_ids),
        bob_total=len(bob_ids),
    )


@app.post("/api/run-join", response_model=JoinResponse)
def run_join():
    if not state.intersection_ids:
        raise HTTPException(status_code=400, detail="Run PSI first to find the intersection.")

    state.log("Running data join on intersection IDs...")

    mask = state.df_bob["ID"].isin(state.intersection_ids)
    bob_subset = state.df_bob[mask]

    joined = pd.merge(
        state.df_alice[state.df_alice["ID"].isin(state.intersection_ids)],
        bob_subset,
        on="ID",
    )
    state.joined_data = joined
    state.aggregated_data = None
    state.log(f"Join complete: {len(joined)} rows with columns {list(joined.columns)}.")

    return JoinResponse(
        row_count=len(joined),
        columns=list(joined.columns),
        data=joined.head(50).to_dict("records"),
    )


@app.post("/api/run-insecure-aggregation", response_model=AggregationResponse)
def run_insecure_aggregation():
    if state.joined_data is None:
        raise HTTPException(status_code=400, detail="Run Join first.")

    state.log("Running insecure aggregation (plaintext)...")

    df = state.joined_data.copy()
    df["TotalComp"] = df["Salary"] + df["Bonus"]
    agg = df.groupby("Department")["TotalComp"].sum().reset_index()
    agg = agg.rename(columns={"TotalComp": "TotalCompensation"})
    state.aggregated_data = agg
    state.log(f"Insecure aggregation complete: {len(agg)} departments.")

    return AggregationResponse(
        departments=agg.to_dict("records"),
        secure=False,
    )


@app.post("/api/run-secure-aggregation", response_model=AggregationResponse)
def run_secure_aggregation():
    if not state.intersection_ids:
        raise HTTPException(status_code=400, detail="Run PSI first.")

    state.log("Starting Secure Aggregation (TenSEAL CKKS)...")

    # --- Alice side: create context & encrypt salaries ---
    context = SecureAggregator.create_context()

    sorted_ids = sorted(state.intersection_ids)
    alice_subset = state.df_alice[state.df_alice["ID"].isin(sorted_ids)].set_index("ID")
    alice_subset = alice_subset.reindex(sorted_ids)
    salaries = alice_subset["Salary"].tolist()

    state.log(f"Alice: Encrypting {len(salaries)} salaries...")
    enc_salaries = SecureAggregator.encrypt_vector(context, salaries)

    # Serialize for "transfer" to Bob
    context_bytes = context.serialize(save_secret_key=False)
    enc_salaries_bytes = enc_salaries.serialize()

    # --- Bob side: add bonuses homomorphically ---
    state.log("Bob: Performing homomorphic addition of bonuses...")
    bob_context = SecureAggregator.deserialize_context(context_bytes)
    bob_enc_salaries = SecureAggregator.deserialize_vector(bob_context, enc_salaries_bytes)

    bob_subset = state.df_bob[state.df_bob["ID"].isin(sorted_ids)].set_index("ID")
    bob_subset = bob_subset.reindex(sorted_ids)
    bonuses = bob_subset["Bonus"].tolist()
    departments = bob_subset["Department"].tolist()

    enc_total = bob_enc_salaries + bonuses

    grouped_sums = {}
    unique_depts = set(departments)
    for dept in unique_depts:
        mask = [1 if d == dept else 0 for d in departments]
        enc_dept = enc_total * mask
        enc_dept_sum = enc_dept.sum()
        grouped_sums[dept] = enc_dept_sum.serialize()

    state.log(f"Bob: Aggregated into {len(grouped_sums)} departments.")

    # --- Alice side: decrypt ---
    state.log("Alice: Decrypting results...")
    results = []
    for dept, enc_sum_bytes in grouped_sums.items():
        enc_sum = ts.ckks_vector_from(context, enc_sum_bytes)
        val = enc_sum.decrypt()[0]
        results.append({"Department": dept, "TotalCompensation": round(val, 2)})

    state.aggregated_data = pd.DataFrame(results)
    state.log("Secure aggregation complete.")

    return AggregationResponse(
        departments=results,
        secure=True,
    )


@app.get("/api/logs")
def get_logs():
    return {"logs": state.logs}
