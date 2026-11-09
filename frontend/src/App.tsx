import { useState } from 'react';
import Header from './components/layout/Header';
import MapView from './components/map/MapView';
import SeverityFilter from './components/filters/SeverityFilter';
import PotholeDetailPanel from './components/details/PotholeDetailPanel';
import ClassificationPage from './components/calibration/ClassificationPage';
import ErrorBanner from './components/common/ErrorBanner';
import { usePotholes } from './hooks/usePotholes';
import { potholeService } from './services';
import { SEVERITY_ORDER } from './utils/severity';
import type { FeedbackType, Pothole, Severity } from './types/pothole';

function App() {
  const [view, setView] = useState<'map' | 'calibration'>('map');
  const [activeSeverities, setActiveSeverities] = useState<Severity[]>([...SEVERITY_ORDER]);
  const [selectedPothole, setSelectedPothole] = useState<Pothole | null>(null);
  const [searchCenter, setSearchCenter] = useState<[number, number]>([-27.3306, -55.8657]);
  const [radiusMeters, setRadiusMeters] = useState(1000);
  const [radiusInput, setRadiusInput] = useState('1000');
  const { potholes, isLoading, error, reload } = usePotholes(activeSeverities, {
    lat: searchCenter[0],
    lng: searchCenter[1],
    radiusMeters,
  });

  const toggleSeverity = (severity: Severity) => {
    setActiveSeverities((prev) =>
      prev.includes(severity) ? prev.filter((current) => current !== severity) : [...prev, severity],
    );
  };

  const commitRadius = () => {
    const value = Number(radiusInput);
    if (!Number.isFinite(value) || value < 100 || value > 50000) {
      setRadiusInput(String(radiusMeters));
      return;
    }
    setRadiusMeters(value);
    setRadiusInput(String(value));
    setSelectedPothole(null);
  };

  const submitFeedback = async (type: FeedbackType) => {
    if (!selectedPothole) return;
    const result = await potholeService.submitFeedback(selectedPothole.id, type);
    setSelectedPothole((current) => current && ({
      ...current,
      falsePositiveReports: result.false_positive_reports,
      repairedReports: result.repaired_reports,
      isVisible: result.is_visible,
    }));
    reload();
    if (!result.is_visible) setSelectedPothole(null);
  };

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-slate-100">
      <Header
        visibleCount={potholes.length}
        isLoading={isLoading}
        view={view}
        onViewChange={setView}
      />

      <div className="relative flex-1">
        {view === 'calibration' ? (
          <ClassificationPage />
        ) : (
          <>
        <MapView
          potholes={potholes}
          selectedId={selectedPothole?.id ?? null}
          searchCenter={searchCenter}
          radiusMeters={radiusMeters}
          onSelectPothole={setSelectedPothole}
          onSelectCenter={(center) => {
            setSearchCenter(center);
            setSelectedPothole(null);
          }}
        />

        <label className="absolute left-3 top-16 z-[1000] flex items-center gap-3 rounded-lg border border-slate-200 bg-white/95 px-3 py-2 shadow-md backdrop-blur">
          <span className="text-xs font-medium text-slate-700">Radio de búsqueda</span>
          <input
            aria-label="Radio de búsqueda en metros"
            type="number"
            min={100}
            max={50000}
            step={100}
            value={radiusInput}
            onChange={(event) => setRadiusInput(event.target.value)}
            onBlur={commitRadius}
            onKeyDown={(event) => {
              if (event.key === 'Enter') commitRadius();
              if (event.key === 'Escape') setRadiusInput(String(radiusMeters));
            }}
            className="w-24 rounded border border-slate-300 px-2 py-1 text-right text-sm tabular-nums text-slate-900"
          />
          <span className="text-xs text-slate-500">m</span>
        </label>

        <SeverityFilter active={activeSeverities} onToggle={toggleSeverity} />

        {error && <ErrorBanner message={error} onRetry={reload} />}

        {selectedPothole && (
          <PotholeDetailPanel
            pothole={selectedPothole}
            onClose={() => setSelectedPothole(null)}
            onFeedback={submitFeedback}
          />
        )}
          </>
        )}
      </div>
    </div>
  );
}

export default App;
