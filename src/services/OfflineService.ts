/**
 * Offline Service for managing offline mode and cache initialization
 * Requirements: 5.4, 8.5 - Offline mode support with cached data fallback
 */

import { cacheManager, CacheStats } from '../utils/CacheManager';
import { SkiRun } from '../models/SkiRun';
import { TerrainData, GridSize, HillMetrics, WeatherData, EquipmentData } from '../models/TerrainData';

export interface OfflineServiceInterface {
  initialize(): Promise<void>;
  isOfflineMode(): boolean;
  setOfflineMode(enabled: boolean): void;
  isDataAvailableOffline(runId: string, gridSize: GridSize): Promise<boolean>;
  getOfflineData(runId: string, gridSize: GridSize): Promise<OfflineData | null>;
  getCacheStats(): Promise<CacheStats>;
  clearCache(): Promise<void>;
  performCacheCleanup(): Promise<void>;
}

export interface OfflineData {
  terrain: TerrainData;
  run: SkiRun;
  agents?: {
    hillMetrics?: HillMetrics;
    weather?: WeatherData;
    equipment?: EquipmentData;
  };
}

export class OfflineService implements OfflineServiceInterface {
  private isOffline = false;
  private initialized = false;
  private cleanupInterval: number | null = null;

  constructor() {
    // Listen for online/offline events
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => {
        console.log('Network connection restored');
        this.setOfflineMode(false);
      });

      window.addEventListener('offline', () => {
        console.log('Network connection lost, switching to offline mode');
        this.setOfflineMode(true);
      });

      // Check initial network status
      this.isOffline = !navigator.onLine;
    }
  }

  /**
   * Initialize the offline service and cache manager
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      return;
    }

    try {
      await cacheManager.initialize();
      console.log('Cache manager initialized successfully');

      // Start periodic cache cleanup (every 6 hours)
      this.startCacheCleanup();

      this.initialized = true;
      console.log('Offline service initialized');
    } catch (error) {
      console.error('Failed to initialize offline service:', error);
      throw new Error(`Offline service initialization failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Check if the application is in offline mode
   */
  isOfflineMode(): boolean {
    return this.isOffline;
  }

  /**
   * Set offline mode state
   */
  setOfflineMode(enabled: boolean): void {
    const wasOffline = this.isOffline;
    this.isOffline = enabled;

    if (wasOffline !== enabled) {
      console.log(`Offline mode ${enabled ? 'enabled' : 'disabled'}`);
      
      // Dispatch custom event for components to listen to
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('offlineModeChanged', {
          detail: { isOffline: enabled }
        }));
      }
    }
  }

  /**
   * Check if data is available for offline use
   */
  async isDataAvailableOffline(runId: string, gridSize: GridSize): Promise<boolean> {
    if (!this.initialized) {
      await this.initialize();
    }

    try {
      return await cacheManager.isOfflineModeAvailable(runId, gridSize);
    } catch (error) {
      console.error('Failed to check offline data availability:', error);
      return false;
    }
  }

  /**
   * Get offline data for a specific run and grid size
   */
  async getOfflineData(runId: string, gridSize: GridSize): Promise<OfflineData | null> {
    if (!this.initialized) {
      await this.initialize();
    }

    try {
      const offlineData = await cacheManager.getOfflineData(runId, gridSize);
      
      if (offlineData) {
        console.log(`Retrieved offline data for run ${runId} with grid size ${gridSize}`);
        return offlineData;
      }

      console.warn(`No offline data available for run ${runId} with grid size ${gridSize}`);
      return null;
    } catch (error) {
      console.error('Failed to get offline data:', error);
      return null;
    }
  }

  /**
   * Get cache statistics
   */
  async getCacheStats(): Promise<CacheStats> {
    if (!this.initialized) {
      await this.initialize();
    }

    try {
      return await cacheManager.getCacheStats();
    } catch (error) {
      console.error('Failed to get cache stats:', error);
      return {
        totalSize: 0,
        entryCount: 0,
        hitRate: 0,
        lastCleanup: 0
      };
    }
  }

  /**
   * Clear all cached data
   */
  async clearCache(): Promise<void> {
    if (!this.initialized) {
      await this.initialize();
    }

    try {
      await cacheManager.clearCache();
      console.log('Cache cleared successfully');
      
      // Dispatch event for UI updates
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('cacheCleared'));
      }
    } catch (error) {
      console.error('Failed to clear cache:', error);
      throw new Error(`Cache clear failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Perform cache cleanup to remove expired entries
   */
  async performCacheCleanup(): Promise<void> {
    if (!this.initialized) {
      await this.initialize();
    }

    try {
      await cacheManager.cleanup();
      console.log('Cache cleanup completed');
    } catch (error) {
      console.error('Failed to perform cache cleanup:', error);
      // Don't throw error for cleanup failures
    }
  }

  /**
   * Start periodic cache cleanup
   */
  private startCacheCleanup(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }

    // Run cleanup every 6 hours
    this.cleanupInterval = setInterval(async () => {
      await this.performCacheCleanup();
    }, 6 * 60 * 60 * 1000);
  }

  /**
   * Stop periodic cache cleanup
   */
  private stopCacheCleanup(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
  }

  /**
   * Preload data for offline use
   */
  async preloadForOffline(runs: SkiRun[], gridSizes: GridSize[]): Promise<void> {
    if (!this.initialized) {
      await this.initialize();
    }

    console.log(`Preloading ${runs.length} runs with ${gridSizes.length} grid sizes for offline use`);

    const preloadPromises: Promise<void>[] = [];

    for (const run of runs) {
      for (const gridSize of gridSizes) {
        preloadPromises.push(
          this.preloadRunData(run, gridSize).catch(error => {
            console.warn(`Failed to preload run ${run.id} with grid size ${gridSize}:`, error);
            // Don't fail the entire preload operation for individual failures
          })
        );
      }
    }

    try {
      await Promise.all(preloadPromises);
      console.log('Preload completed');
    } catch (error) {
      console.error('Preload failed:', error);
      throw error;
    }
  }

  /**
   * Preload data for a specific run and grid size
   */
  private async preloadRunData(run: SkiRun, _gridSize: GridSize): Promise<void> {
    // This would typically trigger the terrain service to load and cache the data
    // For now, we'll just cache the run definition
    try {
      await cacheManager.cacheRunDefinition(run);
      console.log(`Preloaded run definition: ${run.id}`);
    } catch (error) {
      console.warn(`Failed to preload run ${run.id}:`, error);
      throw error;
    }
  }

  /**
   * Get offline mode status and statistics
   */
  async getOfflineStatus(): Promise<{
    isOffline: boolean;
    isInitialized: boolean;
    cacheStats: CacheStats;
    networkStatus: boolean;
  }> {
    const cacheStats = await this.getCacheStats();
    
    return {
      isOffline: this.isOffline,
      isInitialized: this.initialized,
      cacheStats,
      networkStatus: typeof navigator !== 'undefined' ? navigator.onLine : true
    };
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    this.stopCacheCleanup();
    
    if (typeof window !== 'undefined') {
      window.removeEventListener('online', () => this.setOfflineMode(false));
      window.removeEventListener('offline', () => this.setOfflineMode(true));
    }

    // Close cache manager
    cacheManager.close();
    
    this.initialized = false;
    console.log('Offline service destroyed');
  }
}

/**
 * Export singleton instance
 */
export const offlineService = new OfflineService();