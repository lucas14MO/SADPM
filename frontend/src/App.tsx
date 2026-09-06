import { useState } from 'react';
import Header from './components/layout/Header';
import MapView from './components/map/MapView';
import SeverityFilter from './components/filters/SeverityFilter';
import PotholeDetailPanel from './components/details/PotholeDetailPanel';
import ErrorBanner from './components/common/ErrorBanner';
import { usePotholes } from './hooks/usePotholes';
import { SEVERITY_ORDER } from './utils/severity';
import type { Pothole, Severity } from './types/pothole';

function App() {
  const [activeSeverities, setActiveSeverities] = useState<Severity[]>([...SEVERITY_ORDER]);
  const [selectedPothole, setSelectedPothole] = useState<Pothole | null>(null);
  const { potholes, isLoading, error, reload } = usePotholes(activeSeverities);

  const toggleSeverity = (severity: Severity) => {
    setActiveSeverities((prev) =>
      prev.includes(severity) ? prev.filter((current) => current !== severity) : [...prev, severity],
    );
  };

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-slate-100">
      <Header visibleCount={potholes.length} isLoading={isLoading} />

      <div className="relative flex-1">
        <MapView
          potholes={potholes}
          selectedId={selectedPothole?.id ?? null}
          onSelectPothole={setSelectedPothole}
        />

        <SeverityFilter active={activeSeverities} onToggle={toggleSeverity} />

        {error && <ErrorBanner message={error} onRetry={reload} />}

        {selectedPothole && (
          <PotholeDetailPanel pothole={selectedPothole} onClose={() => setSelectedPothole(null)} />
        )}
      </div>
    </div>
  );
}

export default App;
