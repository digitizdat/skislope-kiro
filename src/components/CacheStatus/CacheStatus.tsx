import React, { useState, useEffect } from 'react';
import { offlineService } from '../../services/OfflineService';
import { CacheStats } from '../../utils/CacheManager';
import './CacheStatus.css';

interface CacheStatusProps {
  className?: string;
}

export const CacheStatus: React.FC<CacheStatusProps> = ({ className }) => {
  const [cacheStats, setCacheStats] = useState<CacheStats>({
    totalSize: 0,
    entryCount: 0,
    hitRate: 0,
    lastCleanup: 0
  });
  const [isOffline, setIsOffline] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const updateCacheStats = async () => {
      try {
        const stats = await offlineService.getCacheStats();
        setCacheStats(stats);
        setIsOffline(offlineService.isOfflineMode());
        setIsLoading(false);
      } catch (error) {
        console.error('Failed to get cache stats:', error);
        setIsLoading(false);
      }
    };

    // Initial load
    updateCacheStats();

    // Update every 30 seconds
    const interval = setInterval(updateCacheStats, 30000);

    // Listen for offline mode changes
    const handleOfflineModeChange = (event: CustomEvent) => {
      setIsOffline(event.detail.isOffline);
    };

    // Listen for cache cleared events
    const handleCacheCleared = () => {
      updateCacheStats();
    };

    window.addEventListener('offlineModeChanged', handleOfflineModeChange as EventListener);
    window.addEventListener('cacheCleared', handleCacheCleared);

    return () => {
      clearInterval(interval);
      window.removeEventListener('offlineModeChanged', handleOfflineModeChange as EventListener);
      window.removeEventListener('cacheCleared', handleCacheCleared);
    };
  }, []);

  const handleClearCache = async () => {
    try {
      await offlineService.clearCache();
      // Stats will be updated by the event listener
    } catch (error) {
      console.error('Failed to clear cache:', error);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatHitRate = (rate: number): string => {
    return (rate * 100).toFixed(1) + '%';
  };

  const formatLastCleanup = (timestamp: number): string => {
    if (timestamp === 0) return 'Never';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  if (isLoading) {
    return (
      <div className={`cache-status loading ${className || ''}`}>
        <div className="cache-status-item">
          <span className="cache-status-label">Cache Status:</span>
          <span className="cache-status-value">Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`cache-status ${isOffline ? 'offline' : 'online'} ${className || ''}`}>
      <div className="cache-status-header">
        <h3>Cache Status</h3>
        <div className={`connection-indicator ${isOffline ? 'offline' : 'online'}`}>
          {isOffline ? '🔴 Offline' : '🟢 Online'}
        </div>
      </div>
      
      <div className="cache-stats">
        <div className="cache-status-item">
          <span className="cache-status-label">Cached Items:</span>
          <span className="cache-status-value">{cacheStats.entryCount}</span>
        </div>
        
        <div className="cache-status-item">
          <span className="cache-status-label">Cache Size:</span>
          <span className="cache-status-value">{formatBytes(cacheStats.totalSize)}</span>
        </div>
        
        <div className="cache-status-item">
          <span className="cache-status-label">Hit Rate:</span>
          <span className="cache-status-value">{formatHitRate(cacheStats.hitRate)}</span>
        </div>
        
        <div className="cache-status-item">
          <span className="cache-status-label">Last Cleanup:</span>
          <span className="cache-status-value">{formatLastCleanup(cacheStats.lastCleanup)}</span>
        </div>
      </div>
      
      <div className="cache-actions">
        <button 
          className="cache-clear-button"
          onClick={handleClearCache}
          title="Clear all cached data"
        >
          Clear Cache
        </button>
      </div>
    </div>
  );
};