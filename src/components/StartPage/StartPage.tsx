/**
 * Start Page Component - Ski Area Selection Interface
 * Requirements: 7.1, 7.2, 7.4 - Five ski area options, grid size selector, navigation
 */

import { useState, FC } from 'react';
import { PREDEFINED_SKI_AREAS, SkiArea } from '../../models/SkiArea';
import { GridSize } from '../../models/TerrainData';
import SkiAreaCard from './SkiAreaCard';
import GridSizeSelector from './GridSizeSelector';
import './StartPage.css';

interface StartPageProps {
  onAreaSelected: (area: SkiArea, gridSize: GridSize) => void;
  onBrowseRuns: (area: SkiArea) => void;
}

const StartPage: FC<StartPageProps> = ({ onAreaSelected, onBrowseRuns }) => {
  const [selectedArea, setSelectedArea] = useState<SkiArea | null>(null);
  const [selectedGridSize, setSelectedGridSize] = useState<GridSize>(GridSize.MEDIUM);

  const handleAreaSelect = (area: SkiArea) => {
    setSelectedArea(area);
  };

  const handleGridSizeChange = (gridSize: GridSize) => {
    setSelectedGridSize(gridSize);
  };

  const handleStartExploration = () => {
    if (selectedArea) {
      onAreaSelected(selectedArea, selectedGridSize);
    }
  };

  return (
    <div className="start-page">
      <header className="start-page-header">
        <h1>Alpine Ski Simulator</h1>
        <p>Explore world-renowned ski slopes in immersive 3D environments</p>
      </header>

      <main className="start-page-main">
        <section className="ski-area-selection">
          <h2>Choose Your Ski Area</h2>
          <p>Select from five world-class ski destinations</p>
          
          <div className="ski-area-grid">
            {PREDEFINED_SKI_AREAS.map((area) => (
              <SkiAreaCard
                key={area.id}
                area={area}
                isSelected={selectedArea?.id === area.id}
                onSelect={() => handleAreaSelect(area)}
              />
            ))}
          </div>
        </section>

        {selectedArea && (
          <section className="configuration-section">
            <div className="selected-area-info">
              <h3>Selected: {selectedArea.name}</h3>
              <p>{selectedArea.location}, {selectedArea.country}</p>
              <p>Elevation: {selectedArea.elevation.min}m - {selectedArea.elevation.max}m</p>
            </div>

            <GridSizeSelector
              selectedGridSize={selectedGridSize}
              onGridSizeChange={handleGridSizeChange}
            />

            <div className="action-buttons">
              <button 
                className="browse-runs-btn"
                onClick={() => onBrowseRuns(selectedArea)}
              >
                Browse Existing Runs
              </button>
              <button 
                className="start-exploration-btn"
                onClick={handleStartExploration}
              >
                Create New Run
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
};

export default StartPage;