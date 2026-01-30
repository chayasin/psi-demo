export default function Header({ onReset }) {
  return (
    <header className="header">
      <div className="header-content">
        <h1>Private Set Intersection Demo</h1>
        <p className="subtitle">
          Two-party PSI with ECDH &bull; Data Join &bull; Secure Aggregation
          (TenSEAL CKKS)
        </p>
        <button className="btn btn-outline" onClick={onReset}>
          Reset Session
        </button>
      </div>
    </header>
  );
}
