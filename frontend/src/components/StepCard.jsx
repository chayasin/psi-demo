export default function StepCard({
  step,
  title,
  description,
  disabled,
  loading,
  buttonLabel,
  onRun,
  children,
}) {
  return (
    <section className="card">
      <div className="card-header">
        <span className="step-badge">{step}</span>
        <div>
          <h2>{title}</h2>
          <p className="muted">{description}</p>
        </div>
      </div>

      <div className="card-body">
        <button
          className="btn btn-primary"
          disabled={disabled || loading}
          onClick={onRun}
        >
          {loading ? "Running..." : buttonLabel}
        </button>

        {children}
      </div>
    </section>
  );
}
