/**
 * Run Browser Component - Display and manage saved runs for each ski area
 * Requirements: 3.5, 7.4, 10.7, 10.8 - Run browser, preview cards, editing, grid size selector
 */

import { useState, useEffect, FC } from 'react';
import { SkiArea } from '../../models/SkiArea';
import { SkiRun } from '../../models/SkiRun';
import { GridSize } from '../../models/TerrainData';
import { runDatabaseService } from '../../services/RunDatabaseService';
import RunPreviewCard from './RunPreviewCard';
import GridSizeSelector from '../StartPage/GridSizeSelector';
import './RunBrowser.css';

interface RunBrowserProps {
  skiArea: SkiArea;
  onRunSelected: (run: SkiRun, gridSize: GridSize) => void;
  onCreateNewRun: () => void;
  onBack: () => void;
}

const RunBrowser: FC<RunBrowserProps> = ({
  skiArea,
  onRunSelected,
  onCreateNewRun,
  onBack
}) => {
  const [runs, setRuns] = useState<SkiRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<SkiRun | null>(null);
  const [selectedGridSize, setSelectedGridSize] = useState<GridSize>(GridSize.MEDIUM);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingRun, setEditingRun] = useState<SkiRun | null>(null);

  useEffect(() => {
    loadRuns();
  }, [skiArea.id]);

  const loadRuns = async () => {
    try {
      setLoading(true);
      setError(null);
      const areaRuns = await runDatabaseService.getRunsByArea(skiArea.id);
      setRuns(areaRuns);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load runs');
    } finally {
      setLoading(false);
    }
  };

  const handleRunSelect = (run: SkiRun) => {
    setSelectedRun(run);
  };

  const handleGridSizeChange = (gridSize: GridSize) => {
    setSelectedGridSize(gridSize);
  };

  const handleStartExploration = () => {
    if (selectedRun) {
      onRunSelected(selectedRun, selectedGridSize);
    }
  };

  const handleEditRun = (run: SkiRun) => {
    setEditingRun(run);
  };

  const handleSaveEdit = async (updatedRun: SkiRun) => {
    try {
      await runDatabaseService.updateRun(updatedRun.id, updatedRun);
      setEditingRun(null);
      await loadRuns(); // Refresh the list
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update run');
    }
  };

  const handleCancelEdit = () => {
    setEditingRun(null);
  };

  const handleDuplicateRun = async (run: SkiRun) => {
    try {
      const duplicateName = `${run.name} (Copy)`;
      await runDatabaseService.duplicateRun(run.id, duplicateName);
      await loadRuns(); // Refresh the list
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to duplicate run');
    }
  };

  const handleDeleteRun = async (run: SkiRun) => {
    if (window.confirm(`Are you sure you want to delete "${run.name}"? This action cannot be undone.`)) {
      try {
        await runDatabaseService.deleteRun(run.id);
        if (selectedRun?.id === run.id) {
          setSelectedRun(null);
        }
        await loadRuns(); // Refresh the list
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete run');
      }
    }
  };

  if (loading) {
    return (
      <div className="run-browser">
        <div className="run-browser-loading">
          <div className="loading-spinner"></div>
          <p>Loading runs for {skiArea.name}...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="run-browser">
      <header className="run-browser-header">
        <button className="back-button" onClick={onBack}>
          ← Back to Ski Areas
        </button>
        <div className="area-info">
          <h1>{skiArea.name}</h1>
          <p>{skiArea.location}, {skiArea.country}</p>
          <p>Elevation: {skiArea.elevation.min}m - {skiArea.elevation.max}m</p>
        </div>
      </header>

      <main className="run-browser-main">
        {error && (
          <div className="error-message">
            <p>Error: {error}</p>
            <button onClick={loadRuns}>Retry</button>
          </div>
        )}

        <section className="runs-section">
          <div className="runs-header">
            <h2>Saved Runs ({runs.length})</h2>
            <button className="create-run-button" onClick={onCreateNewRun}>
              + Create New Run
            </button>
          </div>

          {runs.length === 0 ? (
            <div className="no-runs">
              <p>No runs created for this ski area yet.</p>
              <p>Create your first run to start exploring!</p>
              <button className="create-first-run-button" onClick={onCreateNewRun}>
                Create Your First Run
              </button>
            </div>
          ) : (
            <div className="runs-grid">
              {runs.map((run) => (
                <RunPreviewCard
                  key={run.id}
                  run={run}
                  skiArea={skiArea}
                  isSelected={selectedRun?.id === run.id}
                  isEditing={editingRun?.id === run.id}
                  onSelect={() => handleRunSelect(run)}
                  onEdit={() => handleEditRun(run)}
                  onSaveEdit={handleSaveEdit}
                  onCancelEdit={handleCancelEdit}
                  onDuplicate={() => handleDuplicateRun(run)}
                  onDelete={() => handleDeleteRun(run)}
                />
              ))}
            </div>
          )}
        </section>

        {selectedRun && !editingRun && (
          <section className="run-configuration">
            <div className="selected-run-info">
              <h3>Selected: {selectedRun.name}</h3>
              <div className="run-stats">
                <span>Length: {Math.round(selectedRun.statistics.estimatedLength)}m</span>
                <span>Drop: {Math.round(selectedRun.statistics.verticalDrop)}m</span>
                <span>Slope: {selectedRun.statistics.averageSlope.toFixed(1)}°</span>
                <span>Difficulty: {selectedRun.metadata.difficulty}</span>
              </div>
            </div>

            <GridSizeSelector
              selectedGridSize={selectedGridSize}
              onGridSizeChange={handleGridSizeChange}
            />

            <button 
              className="start-exploration-btn"
              onClick={handleStartExploration}
            >
              Explore in 3D
            </button>
          </section>
        )}
      </main>
    </div>
  );
};

export default RunBrowser;