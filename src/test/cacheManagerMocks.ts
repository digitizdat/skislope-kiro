/**
 * CacheManager Mock for Testing
 * Provides proper mocking for CacheManager initialization and operations
 * Requirements: 2.2, 3.1, 3.2
 */

import { vi } from 'vitest';
import { TerrainData, GridSize, HillMetrics, WeatherData, EquipmentData } from '../models/TerrainData';
import { SkiRun } from '../models/SkiRun';
import { CacheEntry, CacheConfig, CacheStats } from '../utils/CacheManager/CacheManager';

/**
 * Mock CacheManager implementation for testing
 */
export class MockCacheManager {
  private initialized = false;
  private terrainCache = new Map<string, CacheEntry<TerrainData>>();
  private runCache = new Map<string, CacheEntry<SkiRun>>();
  private agentCache = new Map<string, CacheEntry<HillMetrics | WeatherData | EquipmentData>>();
  private config: CacheConfig;

  constructor(config?: Partial<CacheConfig>) {
    this.config = {
      terrainCacheDuration: 24 * 60 * 60 * 1000,
      agentCacheDuration: 30 * 60 * 1000,
      runCacheDuration: 7 * 24 * 60 * 60 * 1000,
      maxCacheSize: 500,
      version: '1.0.0',
      ...config
    };
  }

  async initialize(): Promise<void> {
    this.initialized = true;
  }

  async cacheTerrainData(
    terrainData: TerrainData,
    run: SkiRun,
    gridSize: GridSize
  ): Promise<void> {
    if (!this.initialized) {
      throw new Error('Cache not initialized');
    }

    const key = this.generateTerrainKey(run.id, gridSize);
    const entry: CacheEntry<TerrainData> = {
      data: terrainData,
      timestamp: Date.now(),
      expiresAt: Date.now() + this.config.terrainCacheDuration,
      version: this.config.version,
      key
    };

    this.terrainCache.set(key, entry);
  }

  async getCachedTerrainData(
    runId: string,
    gridSize: GridSize
  ): Promise<TerrainData | null> {
    if (!this.initialized) {
      return null;
    }

    const key = this.generateTerrainKey(runId, gridSize);
    const entry = this.terrainCache.get(key);

    if (!entry) {
      return null;
    }

    if (this.isExpired(entry)) {
      this.terrainCache.delete(key);
      return null;
    }

    return entry.data;
  }

  async invalidateTerrainData(runId: string, gridSize: GridSize): Promise<void> {
    if (!this.initialized) {
      throw new Error('Cache not initialized');
    }

    const key = this.generateTerrainKey(runId, gridSize);
    this.terrainCache.delete(key);
  }

  async cacheRunDefinition(run: SkiRun): Promise<void> {
    if (!this.initialized) {
      throw new Error('Cache not initialized');
    }

    const key = this.generateRunKey(run.id);
    const entry: CacheEntry<SkiRun> = {
      data: run,
      timestamp: Date.now(),
      expiresAt: Date.now() + this.config.runCacheDuration,
      version: this.config.version,
      key
    };

    this.runCache.set(key, entry);
  }

  async getCachedRunDefinition(runId: string): Promise<SkiRun | null> {
    if (!this.initialized) {
      return null;
    }

    const key = this.generateRunKey(runId);
    const entry = this.runCache.get(key);

    if (!entry) {
      return null;
    }

    if (this.isExpired(entry)) {
      this.runCache.delete(key);
      return null;
    }

    return entry.data;
  }

  async getCachedRunsByArea(skiAreaId: string): Promise<SkiRun[]> {
    if (!this.initialized) {
      throw new Error('Cache not initialized');
    }

    const validRuns: SkiRun[] = [];
    const expiredKeys: string[] = [];

    for (const [key, entry] of this.runCache.entries()) {
      if (entry.data.skiAreaId === skiAreaId) {
        if (this.isExpired(entry)) {
          expiredKeys.push(key);
        } else {
          validRuns.push(entry.data);
        }
      }
    }

    // Clean up expired entries
    for (const key of expiredKeys) {
      this.runCache.delete(key);
    }

    return validRuns;
  }

  async invalidateRunDefinition(runId: string): Promise<void> {
    if (!this.initialized) {
      throw new Error('Cache not initialized');
    }

    const key = this.generateRunKey(runId);
    this.runCache.delete(key);
  }

  async cacheAgentResponse<T extends HillMetrics | WeatherData | EquipmentData>(
    agentType: 'hill-metrics' | 'weather' | 'equipment',
    skiAreaId: string,
    data: T,
    customExpiration?: number
  ): Promise<void> {
    if (!this.initialized) {
      throw new Error('Cache not initialized');
    }

    const key = this.generateAgentKey(agentType, skiAreaId);
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      expiresAt: Date.now() + (customExpiration || this.config.agentCacheDuration),
      version: this.config.version,
      key
    };

    this.agentCache.set(key, entry);
  }

  async getCachedAgentResponse<T extends HillMetrics | WeatherData | EquipmentData>(
    agentType: 'hill-metrics' | 'weather' | 'equipment',
    skiAreaId: string
  ): Promise<T | null> {
    if (!this.initialized) {
      return null;
    }

    const key = this.generateAgentKey(agentType, skiAreaId);
    const entry = this.agentCache.get(key);

    if (!entry) {
      return null;
    }

    if (this.isExpired(entry)) {
      this.agentCache.delete(key);
      return null;
    }

    return entry.data as T;
  }

  async invalidateAgentResponse(
    agentType: 'hill-metrics' | 'weather' | 'equipment',
    skiAreaId: string
  ): Promise<void> {
    if (!this.initialized) {
      throw new Error('Cache not initialized');
    }

    const key = this.generateAgentKey(agentType, skiAreaId);
    this.agentCache.delete(key);
  }

  async isOfflineModeAvailable(runId: string, gridSize: GridSize): Promise<boolean> {
    const terrainData = await this.getCachedTerrainData(runId, gridSize);
    const runDefinition = await this.getCachedRunDefinition(runId);
    
    return terrainData !== null && runDefinition !== null;
  }

  async getOfflineData(runId: string, gridSize: GridSize): Promise<{
    terrain: TerrainData;
    run: SkiRun;
    agents?: {
      hillMetrics?: HillMetrics;
      weather?: WeatherData;
      equipment?: EquipmentData;
    };
  } | null> {
    const terrain = await this.getCachedTerrainData(runId, gridSize);
    const run = await this.getCachedRunDefinition(runId);
    
    if (!terrain || !run) {
      return null;
    }

    const hillMetrics = await this.getCachedAgentResponse<HillMetrics>('hill-metrics', run.skiAreaId);
    const weather = await this.getCachedAgentResponse<WeatherData>('weather', run.skiAreaId);
    const equipment = await this.getCachedAgentResponse<EquipmentData>('equipment', run.skiAreaId);

    return {
      terrain,
      run,
      agents: {
        hillMetrics: hillMetrics || undefined,
        weather: weather || undefined,
        equipment: equipment || undefined
      }
    };
  }

  async cleanup(): Promise<void> {
    if (!this.initialized) {
      throw new Error('Cache not initialized');
    }

    const now = Date.now();
    
    // Clean up expired terrain data
    for (const [key, entry] of this.terrainCache.entries()) {
      if (this.isExpired(entry)) {
        this.terrainCache.delete(key);
      }
    }

    // Clean up expired run data
    for (const [key, entry] of this.runCache.entries()) {
      if (this.isExpired(entry)) {
        this.runCache.delete(key);
      }
    }

    // Clean up expired agent data
    for (const [key, entry] of this.agentCache.entries()) {
      if (this.isExpired(entry)) {
        this.agentCache.delete(key);
      }
    }
  }

  async clearCache(): Promise<void> {
    if (!this.initialized) {
      throw new Error('Cache not initialized');
    }

    this.terrainCache.clear();
    this.runCache.clear();
    this.agentCache.clear();
  }

  async getCacheStats(): Promise<CacheStats> {
    const totalEntries = this.terrainCache.size + this.runCache.size + this.agentCache.size;
    
    // Rough size estimation
    let totalSize = 0;
    for (const entry of this.terrainCache.values()) {
      totalSize += JSON.stringify(entry).length;
    }
    for (const entry of this.runCache.values()) {
      totalSize += JSON.stringify(entry).length;
    }
    for (const entry of this.agentCache.values()) {
      totalSize += JSON.stringify(entry).length;
    }

    return {
      totalSize,
      entryCount: totalEntries,
      hitRate: 0.8, // Mock hit rate
      lastCleanup: Date.now()
    };
  }

  async close(): Promise<void> {
    this.initialized = false;
    this.terrainCache.clear();
    this.runCache.clear();
    this.agentCache.clear();
  }

  // Helper methods
  private generateTerrainKey(runId: string, gridSize: GridSize): string {
    return `terrain:${runId}:${gridSize}`;
  }

  private generateRunKey(runId: string): string {
    return `run:${runId}`;
  }

  private generateAgentKey(agentType: string, skiAreaId: string): string {
    return `agent:${agentType}:${skiAreaId}`;
  }

  private isExpired(entry: CacheEntry<any>): boolean {
    return Date.now() > entry.expiresAt;
  }

  // Test utilities
  setInitialized(initialized: boolean): void {
    this.initialized = initialized;
  }

  getTerrainCacheSize(): number {
    return this.terrainCache.size;
  }

  getRunCacheSize(): number {
    return this.runCache.size;
  }

  getAgentCacheSize(): number {
    return this.agentCache.size;
  }

  // Simulate cache hit/miss for testing
  simulateCacheHit(runId: string, gridSize: GridSize, terrainData: TerrainData): void {
    const key = this.generateTerrainKey(runId, gridSize);
    const entry: CacheEntry<TerrainData> = {
      data: terrainData,
      timestamp: Date.now(),
      expiresAt: Date.now() + this.config.terrainCacheDuration,
      version: this.config.version,
      key
    };
    this.terrainCache.set(key, entry);
  }

  simulateCacheMiss(runId: string, gridSize: GridSize): void {
    const key = this.generateTerrainKey(runId, gridSize);
    this.terrainCache.delete(key);
  }

  simulateExpiredCache(runId: string, gridSize: GridSize, terrainData: TerrainData): void {
    const key = this.generateTerrainKey(runId, gridSize);
    const entry: CacheEntry<TerrainData> = {
      data: terrainData,
      timestamp: Date.now() - 10000,
      expiresAt: Date.now() - 5000, // Expired
      version: this.config.version,
      key
    };
    this.terrainCache.set(key, entry);
  }
}

/**
 * Create a mock CacheManager with vitest spies
 */
export function createMockCacheManager(config?: Partial<CacheConfig>): MockCacheManager {
  const mockCacheManager = new MockCacheManager(config);
  
  // Spy on all methods to track calls
  vi.spyOn(mockCacheManager, 'initialize');
  vi.spyOn(mockCacheManager, 'cacheTerrainData');
  vi.spyOn(mockCacheManager, 'getCachedTerrainData');
  vi.spyOn(mockCacheManager, 'invalidateTerrainData');
  vi.spyOn(mockCacheManager, 'cacheRunDefinition');
  vi.spyOn(mockCacheManager, 'getCachedRunDefinition');
  vi.spyOn(mockCacheManager, 'getCachedRunsByArea');
  vi.spyOn(mockCacheManager, 'invalidateRunDefinition');
  vi.spyOn(mockCacheManager, 'cacheAgentResponse');
  vi.spyOn(mockCacheManager, 'getCachedAgentResponse');
  vi.spyOn(mockCacheManager, 'invalidateAgentResponse');
  vi.spyOn(mockCacheManager, 'isOfflineModeAvailable');
  vi.spyOn(mockCacheManager, 'getOfflineData');
  vi.spyOn(mockCacheManager, 'cleanup');
  vi.spyOn(mockCacheManager, 'clearCache');
  vi.spyOn(mockCacheManager, 'getCacheStats');
  vi.spyOn(mockCacheManager, 'close');

  return mockCacheManager;
}

/**
 * Create a simple mock for CacheManager module
 */
export function createCacheManagerModuleMock() {
  const mockInstance = createMockCacheManager();
  
  return {
    CacheManager: vi.fn(() => mockInstance),
    cacheManager: mockInstance
  };
}

/**
 * Setup CacheManager mock for tests that need initialized cache
 */
export async function setupInitializedCacheManager(config?: Partial<CacheConfig>): Promise<MockCacheManager> {
  const mockCacheManager = createMockCacheManager(config);
  await mockCacheManager.initialize();
  return mockCacheManager;
}

/**
 * Reset all CacheManager mocks
 */
export function resetCacheManagerMocks(mockCacheManager: MockCacheManager): void {
  vi.clearAllMocks();
  mockCacheManager.clearCache();
  mockCacheManager.setInitialized(false);
}