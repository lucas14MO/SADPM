import { SEVERITY_META, SEVERITY_ORDER } from '../../utils/severity';
import type { Severity } from '../../types/pothole';

interface SeverityFilterProps {
  active: Severity[];
  onToggle: (severity: Severity) => void;
}

/** Chips de gravedad: funcionan a la vez como leyenda de colores y como filtro. */
export default function SeverityFilter({ active, onToggle }: SeverityFilterProps) {
  return (
    <div className="absolute left-3 top-3 z-[1000] flex gap-2 rounded-xl bg-white/95 p-2 shadow-md backdrop-blur">
      {SEVERITY_ORDER.map((severity) => {
        const meta = SEVERITY_META[severity];
        const isActive = active.includes(severity);

        return (
          <button
            key={severity}
            type="button"
            onClick={() => onToggle(severity)}
            aria-pressed={isActive}
            className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition sm:text-sm ${
              isActive ? 'border-transparent text-white' : 'border-slate-300 bg-white text-slate-400'
            }`}
            style={isActive ? { backgroundColor: meta.color } : undefined}
          >
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: isActive ? '#ffffff' : meta.color }}
            />
            {meta.label}
          </button>
        );
      })}
    </div>
  );
}
