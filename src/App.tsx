import { useState, useEffect } from 'react';
import { StartPage } from './components/StartPage';
import { EnvironmentView } from './components/EnvironmentView';
import { MapInterface } from './components/MapInterface';
import { RunBrowser } from './components/RunBrowser';
import { SkiArea } from './models/SkiArea';
import { SkiRun } from './models/SkiRun';
import { GridSize } from './models/TerrainData';
import { offlineService } from './services/OfflineService';
import './App.css';

type AppView = 'start' | 'map' | 'runBrowser' | 'environment';

interface AppState {
  currentView: AppView;
  selectedArea: SkiArea | null;
  selectedRun: SkiRun | null;
  selectedGridSize: GridSize;
}

function App() {
  const [appState, setAppState] = useState<AppState>({
    currentView: 'start',
    selectedArea: null,
    selectedRun: null,
    selectedGridSize: GridSize.MEDIUM
  });

  // Initialize offline service and caching system
  useEffect(() => {
    const initializeOfflineService = async () => {
      try {
        await offlineService.initialize();
        console.log('Offline service initialized successfully');
      } catch (error) {
        console.error('Failed to initialize offline service:', error);
        // Continue without offline support
      }
    };

    initializeOfflineService();

    // Cleanup on unmount
    return () => {
      offlineService.destroy();
    };
  }, []);

  const handleAreaSelected = (area: SkiArea, gridSize: GridSize) => {
    setAppState(prev => ({
      ...prev,
      currentView: 'map',
      selectedArea: area,
      selectedGridSize: gridSize
    }));
  };

  const handleBrowseRuns = (area: SkiArea) => {
    setAppState(prev => ({
      ...prev,
      currentView: 'runBrowser',
      selectedArea: area
    }));
  };

  const handleRunSelected = (run: SkiRun, gridSize: GridSize) => {
    setAppState(prev => ({
      ...prev,
      currentView: 'environment',
      selectedRun: run,
      selectedGridSize: gridSize
    }));
  };

  const handleCreateNewRun = () => {
    setAppState(prev => ({
      ...prev,
      currentView: 'map'
    }));
  };

  const handleRunCreated = (run: SkiRun) => {
    setAppState(prev => ({
      ...prev,
      currentView: 'environment',
      selectedRun: run
    }));
  };

  const handleBackToStart = () => {
    setAppState({
      currentView: 'start',
      selectedArea: null,
      selectedRun: null,
      selectedGridSize: GridSize.MEDIUM
    });
  };

  const handleBackToMap = () => {
    setAppState(prev => ({
      ...prev,
      currentView: 'map',
      selectedRun: null
    }));
  };

  return (
    <div className="app">
      {appState.currentView === 'start' && (
        <StartPage 
          onAreaSelected={handleAreaSelected}
          onBrowseRuns={handleBrowseRuns}
        />
      )}
      
      {appState.currentView === 'runBrowser' && appState.selectedArea && (
        <RunBrowser
          skiArea={appState.selectedArea}
          onRunSelected={handleRunSelected}
          onCreateNewRun={handleCreateNewRun}
          onBack={handleBackToStart}
        />
      )}
      
      {appState.currentView === 'map' && appState.selectedArea && (
        <MapInterface
          skiArea={appState.selectedArea}
          onRunCreated={handleRunCreated}
          onBack={handleBackToStart}
        />
      )}
      
      {appState.currentView === 'environment' && appState.selectedArea && appState.selectedRun && (
        <EnvironmentView
          selectedArea={appState.selectedArea}
          selectedRun={appState.selectedRun}
          selectedGridSize={appState.selectedGridSize}
          onBackToStart={handleBackToStart}
          onBackToMap={handleBackToMap}
        />
      )}
    </div>
  );
}

export default App;