import type { ScenarioCatalog } from "../api/types";

interface Props {
  catalog: ScenarioCatalog;
  selected: string | null;
  onSelect: (id: string) => void;
}

export function ScenarioList({ catalog, selected, onSelect }: Props) {
  const ids = Object.keys(catalog);
  if (ids.length === 0) {
    return <p className="muted">시나리오가 없습니다.</p>;
  }
  return (
    <ul className="scenario-list">
      {ids.map((id) => {
        const meta = catalog[id];
        const isActive = id === selected;
        return (
          <li key={id}>
            <button
              type="button"
              className={isActive ? "scenario-item active" : "scenario-item"}
              onClick={() => onSelect(id)}
            >
              <span className="scenario-name">{meta.name ?? id}</span>
              {meta.difficulty && (
                <span className={`badge badge-${meta.difficulty}`}>
                  {meta.difficulty}
                </span>
              )}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
