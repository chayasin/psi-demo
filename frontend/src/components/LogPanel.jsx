export default function LogPanel({ logs }) {
  if (!logs || logs.length === 0) return null;

  return (
    <section className="card log-panel">
      <h2>Protocol Logs</h2>
      <div className="log-area">
        {[...logs].reverse().map((line, i) => (
          <div key={i} className="log-line">
            {line}
          </div>
        ))}
      </div>
    </section>
  );
}
