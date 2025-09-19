/**
 * Environment View Component - 3D ski slope viewer with camera controls
 * Requirements: 6.1, 6.2 - Camera controls and multiple view modes
 */

import { FC, useEffect, useRef, useState } from 'react';
import { SkiArea } from '../../models/SkiArea';
import { SkiRun } from '../../models/SkiRun';
import { GridSize } from '../../models/TerrainData';
import { CameraMode } from '../../models/CameraState';
import { ThreeSetup } from '../../utils/ThreeSetup';
import './EnvironmentView.css';

interface EnvironmentViewProps {
  selectedArea: SkiArea;
  selectedRun: SkiRun;
  selectedGridSize: GridSize;
  onBackToStart: () => void;
  onBackToMap: () => void;
}

const EnvironmentView: FC<EnvironmentViewProps> = ({ 
  selectedArea, 
  selectedRun,
  selectedGridSize, 
  onBackToStart,
  onBackToMap
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const threeSetupRef = useRef<ThreeSetup | null>(null);
  const [currentCameraMode, setCurrentCameraMode] = useState<CameraMode>(CameraMode.FREEFLY);
  const [currentTimeOfDay, setCurrentTimeOfDay] = useState<'dawn' | 'morning' | 'noon' | 'afternoon' | 'dusk' | 'night'>('noon');

  useEffect(() => {
    if (!containerRef.current) return;

    // Initialize Three.js setup
    threeSetupRef.current = new ThreeSetup(containerRef.current);
    threeSetupRef.current.startAnimation();

    // Cleanup on unmount
    return () => {
      if (threeSetupRef.current) {
        threeSetupRef.current.dispose();
        threeSetupRef.current = null;
      }
    };
  }, []);

  const handleCameraModeChange = (mode: CameraMode) => {
    if (threeSetupRef.current) {
      threeSetupRef.current.setCameraMode(mode);
      setCurrentCameraMode(mode);
    }
  };

  const handleTimeOfDayChange = (time: typeof currentTimeOfDay) => {
    if (threeSetupRef.current) {
      threeSetupRef.current.setTimeOfDay(time);
      setCurrentTimeOfDay(time);
    }
  };

  const handleFlyToPosition = async (position: [number, number, number]) => {
    if (threeSetupRef.current) {
      await threeSetupRef.current.flyToPosition(position, 2000);
    }
  };

  return (
    <div className="environment-view">
      <header className="environment-header">
        <div className="header-buttons">
          <button className="back-button" onClick={onBackToStart}>
            ← Back to Start
          </button>
          <button className="back-button" onClick={onBackToMap}>
            ← Back to Map
          </button>
        </div>
        <h1>{selectedArea.name} - {selectedRun.name}</h1>
        <div className="config-info">
          Grid: {selectedGridSize}
        </div>
      </header>

      <main className="environment-main">
        {/* 3D Scene Container */}
        <div className="scene-container" ref={containerRef} />
        
        {/* Camera Controls Panel */}
        <div className="controls-panel">
          <div className="control-group">
            <h3>Camera Mode</h3>
            <div className="button-group">
              {Object.values(CameraMode).map((mode) => (
                <button
                  key={mode}
                  className={`control-button ${currentCameraMode === mode ? 'active' : ''}`}
                  onClick={() => handleCameraModeChange(mode)}
                >
                  {mode.charAt(0).toUpperCase() + mode.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div className="control-group">
            <h3>Time of Day</h3>
            <div className="button-group">
              {(['dawn', 'morning', 'noon', 'afternoon', 'dusk', 'night'] as const).map((time) => (
                <button
                  key={time}
                  className={`control-button ${currentTimeOfDay === time ? 'active' : ''}`}
                  onClick={() => handleTimeOfDayChange(time)}
                >
                  {time.charAt(0).toUpperCase() + time.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div className="control-group">
            <h3>Quick Navigation</h3>
            <div className="button-group">
              <button 
                className="control-button"
                onClick={() => handleFlyToPosition([0, 20, 30])}
              >
                Overview
              </button>
              <button 
                className="control-button"
                onClick={() => handleFlyToPosition([0, 5, 10])}
              >
                Ground Level
              </button>
              <button 
                className="control-button"
                onClick={() => handleFlyToPosition([0, 50, 0])}
              >
                Aerial View
              </button>
            </div>
          </div>

          <div className="control-group">
            <h3>Run Information</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Area:</span>
                <span className="info-value">{selectedArea.name}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Location:</span>
                <span className="info-value">{selectedArea.location}, {selectedArea.country}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Run:</span>
                <span className="info-value">{selectedRun.name}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Difficulty:</span>
                <span className="info-value">{selectedRun.metadata.difficulty}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Length:</span>
                <span className="info-value">{(selectedRun.statistics.estimatedLength / 1000).toFixed(2)} km</span>
              </div>
              <div className="info-item">
                <span className="info-label">Vertical Drop:</span>
                <span className="info-value">{Math.round(selectedRun.statistics.verticalDrop)} m</span>
              </div>
            </div>
          </div>

          <div className="control-group">
            <h3>Controls Help</h3>
            <div className="help-text">
              <p><strong>Mouse:</strong> Left click + drag to rotate camera</p>
              <p><strong>Keyboard:</strong> WASD or arrow keys to move</p>
              <p><strong>Mouse Wheel:</strong> Zoom in/out</p>
              <p><strong>Q/Space:</strong> Move up</p>
              <p><strong>E/C:</strong> Move down</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default EnvironmentView;