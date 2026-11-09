import { useState } from 'react';
import Header from './components/layout/Header';
import MapView from './components/map/MapView';
import SeverityFilter from './components/filters/SeverityFilter';
import RadiusSearch from './components/filters/RadiusSearch';
import PotholeDetailPanel from './components/details/PotholeDetailPanel';
import ErrorBanner from './components/common/ErrorBanner';
import { usePotholes } from './hooks/usePotholes';
import { potholeService } from './services';
import { SEVERITY_ORDER } from './utils/severity';
import { DEFAULT_RADIUS_METERS } from './utils/geo';
import type { FeedbackType, Pothole, SearchArea, Severity } from './types/pothole';

function App() {
  const [activeSeverities, setActiveSeverities] = useState<Severity[]>([...SEVERITY_ORDER]);
  const [selectedPothole, setSelectedPothole] = useState<Pothole | null>(null);
  const [searchArea, setSearchArea] = useState<SearchArea | null>(null);
  const [isPickingCenter, setIsPickingCenter] = useState(false);
  const [radiusMeters, setRadiusMeters] = useState(DEFAULT_RADIUS_METERS);
  const { potholes, isLoading, error, reload } = usePotholes(activeSeverities, searchArea);

  const toggleSeverity = (severity: Severity) => {
    setActiveSeverities((prev) =>
      prev.includes(severity) ? prev.filter((current) => current !== severity) : [...prev, severity],
    );
  };

  const startPicking = () => {
    setSelectedPothole(null);
    setIsPickingCenter(true);
  };

  const pickCenter = (lat: number, lng: number) => {
    setSearchArea({ lat, lng, radiusMeters });
    setIsPickingCenter(false);
  };

  const changeRadius = (meters: number) => {
    setRadiusMeters(meters);
    setSearchArea((current) => current && { ...current, radiusMeters: meters });
  };

  const clearSearch = () => {
    setSearchArea(null);
    setIsPickingCenter(false);
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
        radiusMeters={searchArea?.radiusMeters ?? null}
      />

      <div className="relative flex-1">
        <MapView
          potholes={potholes}
          selectedId={selectedPothole?.id ?? null}
          onSelectPothole={setSelectedPothole}
          searchArea={searchArea}
          isPickingCenter={isPickingCenter}
          onPickCenter={pickCenter}
        />

        <SeverityFilter active={activeSeverities} onToggle={toggleSeverity} />

        <RadiusSearch
          area={searchArea}
          isPicking={isPickingCenter}
          radiusMeters={radiusMeters}
          onStartPicking={startPicking}
          onCancelPicking={() => setIsPickingCenter(false)}
          onRadiusChange={changeRadius}
          onClear={clearSearch}
        />

        {error && <ErrorBanner message={error} onRetry={reload} />}

        {selectedPothole && (
          <PotholeDetailPanel
            pothole={selectedPothole}
            onClose={() => setSelectedPothole(null)}
            onFeedback={submitFeedback}
          />
        )}
      </div>
    </div>
  );
}

export default App;
