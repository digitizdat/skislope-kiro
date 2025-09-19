/**
 * Grid Size Selector Component - Terrain detail level selection with performance warnings
 * Requirements: 7.2, 7.4 - Grid size selector (32x32 to 128x128) with performance warnings
 */

import { FC } from 'react';
import { GridSize, getGridCellCount, isHighDetailGrid } from '../../models/TerrainData';
import './GridSizeSelector.css';

interface GridSizeSelectorProps {
  selectedGridSize: GridSize;
  onGridSizeChange: (gridSize: GridSize) => void;
}

interface GridSizeOption {
  value: GridSize;
  label: string;
  description: string;
  performanceLevel: 'low' | 'medium' | 'high' | 'extreme';
  warning?: string;
}

const GRID_SIZE_OPTIONS: GridSizeOption[] = [
  {
    value: GridSize.SMALL,
    label: '32×32',
    description: 'Basic detail - Smooth performance on all devices',
    performanceLevel: 'low'
  },
  {
    value: GridSize.MEDIUM,
    label: '64×64',
    description: 'Standard detail - Good balance of quality and performance',
    performanceLevel: 'medium'
  },
  {
    value: GridSize.LARGE,
    label: '96×96',
    description: 'High detail - Requires modern hardware',
    performanceLevel: 'high',
    warning: 'May impact performance on older devices'
  },
  {
    value: GridSize.EXTRA_LARGE,
    label: '128×128',
    description: 'Maximum detail - High-end hardware recommended',
    performanceLevel: 'extreme',
    warning: 'Requires powerful GPU and sufficient RAM'
  }
];

const GridSizeSelector: FC<GridSizeSelectorProps> = ({ 
  selectedGridSize, 
  onGridSizeChange 
}) => {
  const selectedOption = GRID_SIZE_OPTIONS.find(option => option.value === selectedGridSize);
  const cellCount = getGridCellCount(selectedGridSize);

  return (
    <div className="grid-size-selector">
      <h3>Terrain Detail Level</h3>
      <p>Choose the level of terrain detail for your exploration</p>

      <div className="grid-options">
        {GRID_SIZE_OPTIONS.map((option) => (
          <div
            key={option.value}
            className={`grid-option ${selectedGridSize === option.value ? 'selected' : ''} ${option.performanceLevel}`}
            onClick={() => onGridSizeChange(option.value)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onGridSizeChange(option.value);
              }
            }}
          >
            <div className="option-header">
              <span className="option-label">{option.label}</span>
              <span className="performance-indicator">
                {option.performanceLevel === 'low' && '🟢'}
                {option.performanceLevel === 'medium' && '🟡'}
                {option.performanceLevel === 'high' && '🟠'}
                {option.performanceLevel === 'extreme' && '🔴'}
              </span>
            </div>
            
            <p className="option-description">{option.description}</p>
            
            <div className="option-details">
              <span className="cell-count">{getGridCellCount(option.value).toLocaleString()} cells</span>
            </div>

            {option.warning && (
              <div className="performance-warning">
                <span className="warning-icon">⚠️</span>
                <span className="warning-text">{option.warning}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {selectedOption && (
        <div className="selection-summary">
          <h4>Selected Configuration</h4>
          <div className="summary-details">
            <p><strong>Grid Size:</strong> {selectedOption.label} ({cellCount.toLocaleString()} cells)</p>
            <p><strong>Performance Impact:</strong> {selectedOption.performanceLevel.charAt(0).toUpperCase() + selectedOption.performanceLevel.slice(1)}</p>
            {selectedOption.warning && (
              <div className="summary-warning">
                <span className="warning-icon">⚠️</span>
                <span>{selectedOption.warning}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {isHighDetailGrid(selectedGridSize) && (
        <div className="hardware-recommendations">
          <h4>Hardware Recommendations</h4>
          <ul>
            <li>Modern GPU with 4GB+ VRAM</li>
            <li>8GB+ system RAM</li>
            <li>Stable internet connection for terrain data</li>
            <li>Hardware acceleration enabled in browser</li>
          </ul>
        </div>
      )}
    </div>
  );
};

export default GridSizeSelector;