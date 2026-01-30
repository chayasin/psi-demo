export default function DataTable({ columns, rows, maxRows = 10 }) {
  if (!rows || rows.length === 0) return <p className="muted">No data.</p>;

  const display = rows.slice(0, maxRows);

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {display.map((row, i) => (
            <tr key={i}>
              {columns.map((col) => (
                <td key={col}>{formatCell(row[col])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > maxRows && (
        <p className="muted">
          Showing {maxRows} of {rows.length} rows.
        </p>
      )}
    </div>
  );
}

function formatCell(value) {
  if (typeof value === "number") {
    return Number.isInteger(value)
      ? value.toLocaleString()
      : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(value);
}
