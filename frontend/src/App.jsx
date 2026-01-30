import { useState } from "react";
import Header from "./components/Header";
import StepCard from "./components/StepCard";
import DataTable from "./components/DataTable";
import LogPanel from "./components/LogPanel";
import * as api from "./api/client";
import "./App.css";

export default function App() {
  // --- state -----------------------------------------------------------------
  const [dataResult, setDataResult] = useState(null);
  const [psiResult, setPsiResult] = useState(null);
  const [joinResult, setJoinResult] = useState(null);
  const [aggResult, setAggResult] = useState(null);
  const [secAggResult, setSecAggResult] = useState(null);
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);

  const [loadingGen, setLoadingGen] = useState(false);
  const [loadingPsi, setLoadingPsi] = useState(false);
  const [loadingJoin, setLoadingJoin] = useState(false);
  const [loadingAgg, setLoadingAgg] = useState(false);
  const [loadingSecAgg, setLoadingSecAgg] = useState(false);

  // --- helpers ---------------------------------------------------------------
  async function refreshLogs() {
    try {
      const res = await api.getLogs();
      setLogs(res.logs);
    } catch {
      /* ignore */
    }
  }

  function clearError() {
    setError(null);
  }

  // --- handlers --------------------------------------------------------------
  async function handleReset() {
    clearError();
    await api.resetSession();
    setDataResult(null);
    setPsiResult(null);
    setJoinResult(null);
    setAggResult(null);
    setSecAggResult(null);
    setLogs([]);
  }

  async function handleGenerate() {
    clearError();
    setLoadingGen(true);
    try {
      const res = await api.generateData();
      setDataResult(res);
      setPsiResult(null);
      setJoinResult(null);
      setAggResult(null);
      setSecAggResult(null);
      await refreshLogs();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingGen(false);
    }
  }

  async function handlePSI() {
    clearError();
    setLoadingPsi(true);
    try {
      const res = await api.runPSI();
      setPsiResult(res);
      setJoinResult(null);
      setAggResult(null);
      setSecAggResult(null);
      await refreshLogs();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingPsi(false);
    }
  }

  async function handleJoin() {
    clearError();
    setLoadingJoin(true);
    try {
      const res = await api.runJoin();
      setJoinResult(res);
      setAggResult(null);
      await refreshLogs();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingJoin(false);
    }
  }

  async function handleInsecureAgg() {
    clearError();
    setLoadingAgg(true);
    try {
      const res = await api.runInsecureAggregation();
      setAggResult(res);
      await refreshLogs();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingAgg(false);
    }
  }

  async function handleSecureAgg() {
    clearError();
    setLoadingSecAgg(true);
    try {
      const res = await api.runSecureAggregation();
      setSecAggResult(res);
      await refreshLogs();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingSecAgg(false);
    }
  }

  // --- render ----------------------------------------------------------------
  return (
    <div className="app">
      <Header onReset={handleReset} />

      {error && (
        <div className="error-banner" onClick={clearError}>
          {error}
        </div>
      )}

      <main className="main">
        {/* Step 1 ---------------------------------------------------------- */}
        <StepCard
          step="1"
          title="Generate Data"
          description="Create random datasets for Alice (ID, Name, Age, Salary) and Bob (ID, Department, Bonus) with ~50% overlap."
          buttonLabel="Generate Data"
          loading={loadingGen}
          onRun={handleGenerate}
        >
          {dataResult && (
            <div className="result">
              <div className="data-panels">
                <div className="panel">
                  <h3>Alice's Data ({dataResult.alice_rows} rows)</h3>
                  <DataTable
                    columns={dataResult.alice_columns}
                    rows={dataResult.alice_sample}
                  />
                </div>
                <div className="panel">
                  <h3>Bob's Data ({dataResult.bob_rows} rows)</h3>
                  <DataTable
                    columns={dataResult.bob_columns}
                    rows={dataResult.bob_sample}
                  />
                </div>
              </div>
            </div>
          )}
        </StepCard>

        {/* Step 2 ---------------------------------------------------------- */}
        <StepCard
          step="2"
          title="Scenario 1: Private Set Intersection"
          description="Use ECDH to find common employee IDs without revealing non-matching records."
          buttonLabel="Run PSI Protocol"
          disabled={!dataResult}
          loading={loadingPsi}
          onRun={handlePSI}
        >
          {psiResult && (
            <div className="result">
              <div className="stats-row">
                <div className="stat">
                  <span className="stat-value">{psiResult.alice_total}</span>
                  <span className="stat-label">Alice's IDs</span>
                </div>
                <div className="stat">
                  <span className="stat-value">{psiResult.bob_total}</span>
                  <span className="stat-label">Bob's IDs</span>
                </div>
                <div className="stat highlight">
                  <span className="stat-value">
                    {psiResult.intersection_size}
                  </span>
                  <span className="stat-label">Intersection</span>
                </div>
              </div>
              <h4>Sample Intersection IDs</h4>
              <div className="id-chips">
                {psiResult.sample_ids.map((id) => (
                  <span key={id} className="chip">
                    {id}
                  </span>
                ))}
              </div>
            </div>
          )}
        </StepCard>

        {/* Step 3 ---------------------------------------------------------- */}
        <StepCard
          step="3"
          title="Scenario 2: Data Join"
          description="Alice requests Bob's data for the intersection IDs and merges with her own."
          buttonLabel="Fetch Joined Data"
          disabled={!psiResult}
          loading={loadingJoin}
          onRun={handleJoin}
        >
          {joinResult && (
            <div className="result">
              <p>
                <strong>{joinResult.row_count}</strong> joined rows &mdash;
                columns: {joinResult.columns.join(", ")}
              </p>
              <DataTable
                columns={joinResult.columns}
                rows={joinResult.data}
                maxRows={15}
              />
            </div>
          )}
        </StepCard>

        {/* Step 4a --------------------------------------------------------- */}
        <StepCard
          step="4a"
          title="Scenario 3a: Insecure Aggregation"
          description="Compute total compensation per department using plaintext data (baseline)."
          buttonLabel="Run Insecure Aggregation"
          disabled={!joinResult}
          loading={loadingAgg}
          onRun={handleInsecureAgg}
        >
          {aggResult && (
            <div className="result">
              <DataTable
                columns={["Department", "TotalCompensation"]}
                rows={aggResult.departments}
              />
            </div>
          )}
        </StepCard>

        {/* Step 4b --------------------------------------------------------- */}
        <StepCard
          step="4b"
          title="Scenario 3b: Secure Aggregation (Homomorphic Encryption)"
          description="Compute total compensation per department using TenSEAL CKKS. Bob adds bonuses to encrypted salaries without seeing them."
          buttonLabel="Run Secure Aggregation"
          disabled={!psiResult}
          loading={loadingSecAgg}
          onRun={handleSecureAgg}
        >
          {secAggResult && (
            <div className="result">
              <span className="badge-secure">HE-Encrypted</span>
              <DataTable
                columns={["Department", "TotalCompensation"]}
                rows={secAggResult.departments}
              />
            </div>
          )}
        </StepCard>

        {/* Logs ------------------------------------------------------------- */}
        <LogPanel logs={logs} />
      </main>
    </div>
  );
}
