/**
 * Interactive Satellite Map Interface for Run Definition
 * Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MapContainer, TileLayer, Polygon, Polyline, useMapEvents } from 'react-leaflet';
import { Map as LeafletMap } from 'leaflet';
import { SkiArea } from '../../models/SkiArea';
import { 
  GeographicCoordinate, 
  SkiRun, 
  RunStatistics, 
  ValidationResult,
  TopographicalData,
  SurfaceType
} from '../../models/SkiRun';
import { mapService } from '../../services/MapService';
import { runDatabaseService } from '../../services/RunDatabaseService';
import RunCreationForm from './RunCreationForm';
import RunStatisticsPanel from './RunStatisticsPanel';
import './MapInterface.css';

interface MapInterfaceProps {
  skiArea: SkiArea;
  onRunCreated: (run: SkiRun) => void;
  onBack: () => void;
}

interface DrawingState {
  isDrawing: boolean;
  currentBoundary: GeographicCoordinate[];
  isComplete: boolean;
}

const MapInterface: React.FC<MapInterfaceProps> = ({ skiArea, onRunCreated, onBack }) => {
  const [drawingState, setDrawingState] = useState<DrawingState>({
    isDrawing: false,
    currentBoundary: [],
    isComplete: false
  });
  const [runStatistics, setRunStatistics] = useState<RunStatistics | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [topographicalData, setTopographicalData] = useState<TopographicalData | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [satelliteUrl, setSatelliteUrl] = useState<string>('');
  
  const mapRef = useRef<LeafletMap | null>(null);

  // Load satellite imagery and topographical data
  useEffect(() => {
    const loadMapData = async () => {
      try {
        const [satelliteImagery, topoData] = await Promise.all([
          mapService.loadSatelliteImagery(skiArea),
          mapService.loadTopographicalOverlay(skiArea)
        ]);
        
        setSatelliteUrl(satelliteImagery);
        setTopographicalData(topoData);
      } catch (error) {
        console.error('Failed to load map data:', error);
      }
    };

    loadMapData();
  }, [skiArea]);

  // Update statistics and validation when boundary changes
  useEffect(() => {
    if (drawingState.currentBoundary.length >= 3) {
      const stats = mapService.calculateRunStatistics(drawingState.currentBoundary);
      const validationResult = mapService.validateRunBoundary(drawingState.currentBoundary);
      
      setRunStatistics(stats);
      setValidation(validationResult);
    } else {
      setRunStatistics(null);
      setValidation(null);
    }
  }, [drawingState.currentBoundary]);

  const handleStartDrawing = useCallback(() => {
    setDrawingState({
      isDrawing: true,
      currentBoundary: [],
      isComplete: false
    });
    setShowCreateForm(false);
  }, []);

  const handleClearDrawing = useCallback(() => {
    setDrawingState({
      isDrawing: false,
      currentBoundary: [],
      isComplete: false
    });
    setRunStatistics(null);
    setValidation(null);
    setShowCreateForm(false);
  }, []);

  const handleCompleteDrawing = useCallback(() => {
    if (drawingState.currentBoundary.length >= 3) {
      setDrawingState(prev => ({
        ...prev,
        isDrawing: false,
        isComplete: true
      }));
    }
  }, [drawingState.currentBoundary.length]);

  const handleCreateRun = useCallback(() => {
    if (validation?.isValid && runStatistics) {
      setShowCreateForm(true);
    }
  }, [validation, runStatistics]);

  const handleRunFormSubmit = useCallback(async (runData: {
    name: string;
    difficulty: 'beginner' | 'intermediate' | 'advanced' | 'expert' | 'custom';
    surfaceType: SurfaceType;
    notes?: string;
    tags: string[];
  }) => {
    if (!runStatistics) return;

    try {
      const newRun = await runDatabaseService.createRun({
        name: runData.name,
        skiAreaId: skiArea.id,
        boundary: drawingState.currentBoundary,
        metadata: {
          difficulty: runData.difficulty,
          estimatedLength: runStatistics.estimatedLength,
          verticalDrop: runStatistics.verticalDrop,
          averageSlope: runStatistics.averageSlope,
          surfaceType: runData.surfaceType,
          notes: runData.notes,
          tags: runData.tags
        },
        statistics: runStatistics,
        createdBy: 'user', // In production, this would be the actual user ID
        isPublic: false
      });

      onRunCreated(newRun);
    } catch (error) {
      console.error('Failed to create run:', error);
      // In production, show user-friendly error message
      alert('Failed to save run. Please try again.');
    }
  }, [runStatistics, drawingState.currentBoundary, skiArea.id, onRunCreated]);

  return (
    <div className="map-interface">
      <header className="map-interface-header">
        <button className="back-button" onClick={onBack}>
          ← Back to Ski Areas
        </button>
        <h1>{skiArea.name} - Create New Run</h1>
        <p>{skiArea.location}, {skiArea.country}</p>
      </header>

      <div className="map-interface-content">
        <div className="map-container">
          <MapContainer
            center={[
              (skiArea.bounds.northEast.lat + skiArea.bounds.southWest.lat) / 2,
              (skiArea.bounds.northEast.lng + skiArea.bounds.southWest.lng) / 2
            ]}
            zoom={13}
            style={{ height: '100%', width: '100%' }}
            ref={mapRef}
          >
            {satelliteUrl && (
              <TileLayer
                url={satelliteUrl}
                attribution='&copy; <a href="https://www.esri.com/">Esri</a>'
                maxZoom={18}
              />
            )}

            {/* Topographical contour lines */}
            {topographicalData?.contourLines.map((contour, index) => (
              <Polyline
                key={`contour-${index}`}
                positions={contour.coordinates.map(coord => [coord.lat, coord.lng])}
                color="#8B4513"
                weight={1}
                opacity={0.6}
              />
            ))}

            {/* Current drawing boundary */}
            {drawingState.currentBoundary.length > 0 && (
              <Polygon
                positions={drawingState.currentBoundary.map(coord => [coord.lat, coord.lng])}
                color="#FF6B35"
                fillColor="#FF6B35"
                fillOpacity={0.3}
                weight={3}
              />
            )}

            <MapEventHandler
              isDrawing={drawingState.isDrawing}
              onPointAdded={(point) => {
                setDrawingState(prev => ({
                  ...prev,
                  currentBoundary: [...prev.currentBoundary, point]
                }));
              }}
            />
          </MapContainer>

          <div className="map-controls">
            {!drawingState.isDrawing && !drawingState.isComplete && (
              <button className="control-button primary" onClick={handleStartDrawing}>
                Start Drawing Run Boundary
              </button>
            )}

            {drawingState.isDrawing && (
              <div className="drawing-controls">
                <button className="control-button secondary" onClick={handleCompleteDrawing}>
                  Complete Boundary ({drawingState.currentBoundary.length} points)
                </button>
                <button className="control-button danger" onClick={handleClearDrawing}>
                  Clear
                </button>
                <p className="drawing-hint">
                  Click on the map to add boundary points. Complete when you have at least 3 points.
                </p>
              </div>
            )}

            {drawingState.isComplete && (
              <div className="completed-controls">
                <button 
                  className="control-button primary" 
                  onClick={handleCreateRun}
                  disabled={!validation?.isValid}
                >
                  Create Run
                </button>
                <button className="control-button secondary" onClick={handleClearDrawing}>
                  Start Over
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="map-sidebar">
          {runStatistics && (
            <RunStatisticsPanel 
              statistics={runStatistics}
              validation={validation}
            />
          )}

          {showCreateForm && runStatistics && validation?.isValid && (
            <RunCreationForm
              onSubmit={handleRunFormSubmit}
              onCancel={() => setShowCreateForm(false)}
              statistics={runStatistics}
            />
          )}
        </div>
      </div>
    </div>
  );
};

// Component to handle map click events for drawing
interface MapEventHandlerProps {
  isDrawing: boolean;
  onPointAdded: (point: GeographicCoordinate) => void;
}

const MapEventHandler: React.FC<MapEventHandlerProps> = ({ isDrawing, onPointAdded }) => {
  useMapEvents({
    click: (e) => {
      if (isDrawing) {
        onPointAdded({
          lat: e.latlng.lat,
          lng: e.latlng.lng
        });
      }
    }
  });

  return null;
};

export default MapInterface;