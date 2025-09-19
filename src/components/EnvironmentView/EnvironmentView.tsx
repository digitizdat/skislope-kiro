/**
 * Environment View Component - 3D ski slope viewer with camera controls
 * Requirements: 6.1, 6.2 - Camera controls and multiple view modes
 */

import { FC, useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { SkiArea } from '../../models/SkiArea';
import { SkiRun } from '../../models/SkiRun';
import { GridSize } from '../../models/TerrainData';
import { CameraMode } from '../../models/CameraState';
import { ThreeSetup } from '../../utils/ThreeSetup';
import { terrainService } from '../../services/TerrainService';
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
  const [isLoadingTerrain, setIsLoadingTerrain] = useState(false);
  const [terrainError, setTerrainError] = useState<string | null>(null);
  const [loadingProgress, setLoadingProgress] = useState(0);

  useEffect(() => {
    if (!containerRef.current) return;

    // Initialize Three.js setup
    threeSetupRef.current = new ThreeSetup(containerRef.current);
    threeSetupRef.current.startAnimation();

    // Load terrain data
    loadTerrainData();

    // Cleanup on unmount
    return () => {
      if (threeSetupRef.current) {
        threeSetupRef.current.dispose();
        threeSetupRef.current = null;
      }
    };
  }, []);

  // Reload terrain when run or grid size changes
  useEffect(() => {
    if (threeSetupRef.current) {
      loadTerrainData();
    }
  }, [selectedRun, selectedGridSize]);

  const loadTerrainData = async () => {
    if (!threeSetupRef.current) return;

    setIsLoadingTerrain(true);
    setTerrainError(null);
    setLoadingProgress(0);

    try {
      // Simulate progress updates
      setLoadingProgress(25);
      
      // Extract terrain data for the selected run
      const terrainData = await terrainService.extractTerrainData(selectedRun, selectedGridSize);
      setLoadingProgress(50);

      // Generate 3D mesh from terrain data
      const terrainMesh = terrainService.generateMesh(terrainData);
      setLoadingProgress(75);

      // Add terrain to the scene
      threeSetupRef.current.addTerrainMesh(terrainMesh);
      setLoadingProgress(100);

      // Position camera to view the terrain
      const bounds = terrainMesh.boundingBox;
      const center = bounds.getCenter(new THREE.Vector3());
      const size = bounds.getSize(new THREE.Vector3());
      
      // Position camera above and back from terrain center
      const cameraDistance = Math.max(size.x, size.z) * 1.5;
      const cameraHeight = center.y + size.y * 0.5 + 50;
      
      await threeSetupRef.current.flyToPosition([
        center.x,
        cameraHeight,
        center.z + cameraDistance
      ], 3000);

    } catch (error) {
      console.error('Failed to load terrain:', error);
      setTerrainError(error instanceof Error ? error.message : 'Failed to load terrain data');
    } finally {
      setIsLoadingTerrain(false);
      setLoadingProgress(0);
    }
  };

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
        <div className="scene-container" ref={containerRef}>
          {/* Loading Overlay */}
          {isLoadingTerrain && (
            <div className="loading-overlay">
              <div className="loading-content">
                <div className="loading-spinner"></div>
                <h3>Loading Terrain Data</h3>
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${loadingProgress}%` }}
                  ></div>
                </div>
                <p>{loadingProgress}% Complete</p>
                <p className="loading-details">
                  {loadingProgress < 25 && 'Connecting to hill metrics agent...'}
                  {loadingProgress >= 25 && loadingProgress < 50 && 'Processing elevation data...'}
                  {loadingProgress >= 50 && loadingProgress < 75 && 'Generating 3D mesh...'}
                  {loadingProgress >= 75 && 'Applying materials and LOD...'}
                </p>
              </div>
            </div>
          )}

          {/* Error Overlay */}
          {terrainError && (
            <div className="error-overlay">
              <div className="error-content">
                <h3>Failed to Load Terrain</h3>
                <p>{terrainError}</p>
                <button 
                  className="retry-button"
                  onClick={loadTerrainData}
                >
                  Retry
                </button>
              </div>
            </div>
          )}
        </div>
        
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