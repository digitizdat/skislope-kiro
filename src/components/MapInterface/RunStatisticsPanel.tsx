/**
 * Run Statistics Panel - Display boundary statistics and validation
 * Requirements: 10.4, 10.5 - Visual feedback and run statistics
 */

import React from 'react';
import { RunStatistics, ValidationResult } from '../../models/SkiRun';
import './RunStatisticsPanel.css';

interface RunStatisticsPanelProps {
  statistics: RunStatistics;
  validation: ValidationResult | null;
}

const RunStatisticsPanel: React.FC<RunStatisticsPanelProps> = ({ statistics, validation }) => {
  const formatDistance = (meters: number): string => {
    if (meters >= 1000) {
      return `${(meters / 1000).toFixed(2)} km`;
    }
    return `${Math.round(meters)} m`;
  };

  const formatArea = (squareMeters: number): string => {
    if (squareMeters >= 1000000) {
      return `${(squareMeters / 1000000).toFixed(2)} km²`;
    }
    if (squareMeters >= 10000) {
      return `${(squareMeters / 10000).toFixed(2)} ha`;
    }
    return `${Math.round(squareMeters)} m²`;
  };

  const formatSlope = (degrees: number): string => {
    return `${degrees.toFixed(1)}°`;
  };

  const getSlopeCategory = (degrees: number): string => {
    if (degrees < 10) return 'Gentle';
    if (degrees < 20) return 'Moderate';
    if (degrees < 30) return 'Steep';
    if (degrees < 40) return 'Very Steep';
    return 'Extreme';
  };

  const getSlopeCategoryClass = (degrees: number): string => {
    if (degrees < 10) return 'gentle';
    if (degrees < 20) return 'moderate';
    if (degrees < 30) return 'steep';
    if (degrees < 40) return 'very-steep';
    return 'extreme';
  };

  return (
    <div className="run-statistics-panel">
      <h3>Run Statistics</h3>
      
      <div className="statistics-grid">
        <div className="statistic-item">
          <label>Length</label>
          <span className="statistic-value">{formatDistance(statistics.estimatedLength)}</span>
        </div>
        
        <div className="statistic-item">
          <label>Area</label>
          <span className="statistic-value">{formatArea(statistics.area)}</span>
        </div>
        
        <div className="statistic-item">
          <label>Vertical Drop</label>
          <span className="statistic-value">{formatDistance(statistics.verticalDrop)}</span>
        </div>
        
        <div className={`statistic-item slope-${getSlopeCategoryClass(statistics.averageSlope)}`}>
          <label>Average Slope</label>
          <span className="statistic-value">
            {formatSlope(statistics.averageSlope)}
            <span className="slope-category">({getSlopeCategory(statistics.averageSlope)})</span>
          </span>
        </div>
      </div>

      <div className="bounding-box">
        <h4>Bounding Box</h4>
        <div className="coordinates">
          <div className="coordinate-item">
            <label>North East</label>
            <span className="coordinate-value">
              {statistics.boundingBox.northEast.lat.toFixed(6)}, {statistics.boundingBox.northEast.lng.toFixed(6)}
            </span>
          </div>
          <div className="coordinate-item">
            <label>South West</label>
            <span className="coordinate-value">
              {statistics.boundingBox.southWest.lat.toFixed(6)}, {statistics.boundingBox.southWest.lng.toFixed(6)}
            </span>
          </div>
        </div>
      </div>

      {validation && (
        <div className="validation-section">
          <div className={`validation-status ${validation.isValid ? 'valid' : 'invalid'}`}>
            <span className="status-icon">
              {validation.isValid ? '✓' : '✗'}
            </span>
            <span className="status-text">
              {validation.isValid ? 'Valid Run Boundary' : 'Invalid Run Boundary'}
            </span>
          </div>

          {validation.errors.length > 0 && (
            <div className="validation-errors">
              <h4>Errors</h4>
              <ul>
                {validation.errors.map((error, index) => (
                  <li key={index} className="error-item">
                    {error}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {validation.warnings.length > 0 && (
            <div className="validation-warnings">
              <h4>Warnings</h4>
              <ul>
                {validation.warnings.map((warning, index) => (
                  <li key={index} className="warning-item">
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RunStatisticsPanel;