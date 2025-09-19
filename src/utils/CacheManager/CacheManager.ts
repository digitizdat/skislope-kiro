import { TerrainData, GridSize, HillMetrics, WeatherData, EquipmentData } from '../../models/TerrainData';
import { SkiRun } from '../../models/SkiRun';

export interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
  version: string;
  key: string;
}

export interface CacheConfig {
  terrainCacheDuration: number; // in milliseconds
  agentCacheDuration: number;
  runCacheDuration: number;
  maxCacheSize: number; // in MB
  version: string;
}

export interface CacheStats {
  totalSize: number;
  entryCount: number;
  hitRate: number;
  lastCleanup: number;
}

export class CacheManager {
  private db: IDBDatabase | null = null;
  private dbName = 'alpine-ski-cache';
  private dbVersion = 1;
  private config: CacheConfig;
  private stats: CacheStats = {
    totalSize: 0,
    entryCount: 0,
    hitRate: 0,
    lastCleanup: 0
  };
  private hitCount = 0;
  private missCount = 0;

  constructor(config?: Partial<CacheConfig>) {
    this.config = {
      terrainCacheDuration: 24 * 60 * 60 * 1000, // 24 hours
      agentCacheDuration: 30 * 60 * 1000, // 30 minutes
      runCacheDuration: 7 * 24 * 60 * 60 * 1000, // 7 days
      maxCacheSize: 500, // 500 MB
      version: '1.0.0',
      ...config
    };
  }

  async initialize(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        this.setupErrorHandling();
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        this.createObjectStores(db);
      };
    });
  }

  private createObjectStores(db: IDBDatabase): void {
    // Terrain data store
    if (!db.objectStoreNames.contains('terrain')) {
      const terrainStore = db.createObjectStore('terrain', { keyPath: 'key' });
      terrainStore.createIndex('skiAreaId', 'skiAreaId', { unique: false });
      terrainStore.createIndex('gridSize', 'gridSize', { unique: false });
      terrainStore.createIndex('expiresAt', 'expiresAt', { unique: false });
    }

    // Run definitions store
    if (!db.objectStoreNames.contains('runs')) {
      const runsStore = db.createObjectStore('runs', { keyPath: 'key' });
      runsStore.createIndex('skiAreaId', 'skiAreaId', { unique: false });
      runsStore.createIndex('userId', 'userId', { unique: false });
      runsStore.createIndex('expiresAt', 'expiresAt', { unique: false });
    }

    // Agent responses store
    if (!db.objectStoreNames.contains('agents')) {
      const agentsStore = db.createObjectStore('agents', { keyPath: 'key' });
      agentsStore.createIndex('agentType', 'agentType', { unique: false });
      agentsStore.createIndex('skiAreaId', 'skiAreaId', { unique: false });
      agentsStore.createIndex('expiresAt', 'expiresAt', { unique: false });
    }

    // Cache metadata store
    if (!db.objectStoreNames.contains('metadata')) {
      db.createObjectStore('metadata', { keyPath: 'key' });
    }
  }

  private setupErrorHandling(): void {
    if (this.db) {
      this.db.onerror = (event) => {
        console.error('IndexedDB error:', event);
      };
    }
  }

  // Terrain data caching
  async cacheTerrainData(
    terrainData: TerrainData,
    run: SkiRun,
    gridSize: GridSize
  ): Promise<void> {
    if (!this.db) throw new Error('Cache not initialized');

    const key = this.generateTerrainKey(run.id, gridSize);
    const entry: CacheEntry<TerrainData> = {
      data: terrainData,
      timestamp: Date.now(),
      expiresAt: Date.now() + this.config.terrainCacheDuration,
      version: this.config.version,
      key
    };

    const transaction = this.db.transaction(['terrain'], 'readwrite');
    const store = transaction.objectStore('terrain');
    
    await this.promisifyRequest(store.put({
      ...entry,
      skiAreaId: run.skiAreaId,
      gridSize,
      runId: run.id
    }));

    this.updateStats();
  }

  async getCachedTerrainData(
    runId: string,
    gridSize: GridSize
  ): Promise<TerrainData | null> {
    if (!this.db) throw new Error('Cache not initialized');

    const key = this.generateTerrainKey(runId, gridSize);
    const transaction = this.db.transaction(['terrain'], 'readonly');
    const store = transaction.objectStore('terrain');
    
    const result = await this.promisifyRequest(store.get(key));
    
    if (!result) {
      this.missCount++;
      return null;
    }

    if (this.isExpired(result)) {
      await this.invalidateTerrainData(runId, gridSize);
      this.missCount++;
      return null;
    }

    this.hitCount++;
    return result.data;
  }

  async invalidateTerrainData(runId: string, gridSize: GridSize): Promise<void> {
    if (!this.db) throw new Error('Cache not initialized');

    const key = this.generateTerrainKey(runId, gridSize);
    const transaction = this.db.transaction(['terrain'], 'readwrite');
    const store = transaction.objectStore('terrain');
    
    await this.promisifyRequest(store.delete(key));
    this.updateStats();
  }

  // Run definitions caching
  async cacheRunDefinition(run: SkiRun): Promise<void> {
    if (!this.db) throw new Error('Cache not initialized');

    const key = this.generateRunKey(run.id);
    const entry: CacheEntry<SkiRun> = {
      data: run,
      timestamp: Date.now(),
      expiresAt: Date.now() + this.config.runCacheDuration,
      version: this.config.version,
      key
    };

    const transaction = this.db.transaction(['runs'], 'readwrite');
    const store = transaction.objectStore('runs');
    
    await this.promisifyRequest(store.put({
      ...entry,
      skiAreaId: run.skiAreaId,
      userId: run.createdBy
    }));

    this.updateStats();
  }

  async getCachedRunDefinition(runId: string): Promise<SkiRun | null> {
    if (!this.db) throw new Error('Cache not initialized');

    const key = this.generateRunKey(runId);
    const transaction = this.db.transaction(['runs'], 'readonly');
    const store = transaction.objectStore('runs');
    
    const result = await this.promisifyRequest(store.get(key));
    
    if (!result) {
      this.missCount++;
      return null;
    }

    if (this.isExpired(result)) {
      await this.invalidateRunDefinition(runId);
      this.missCount++;
      return null;
    }

    this.hitCount++;
    return result.data;
  }

  async getCachedRunsByArea(skiAreaId: string): Promise<SkiRun[]> {
    if (!this.db) throw new Error('Cache not initialized');

    const transaction = this.db.transaction(['runs'], 'readonly');
    const store = transaction.objectStore('runs');
    const index = store.index('skiAreaId');
    
    const results = await this.promisifyRequest(index.getAll(skiAreaId));
    
    const validRuns: SkiRun[] = [];
    const expiredKeys: string[] = [];

    for (const result of results) {
      if (this.isExpired(result)) {
        expiredKeys.push(result.key);
      } else {
        validRuns.push(result.data);
        this.hitCount++;
      }
    }

    // Clean up expired entries
    if (expiredKeys.length > 0) {
      const writeTransaction = this.db.transaction(['runs'], 'readwrite');
      const writeStore = writeTransaction.objectStore('runs');
      
      for (const key of expiredKeys) {
        writeStore.delete(key);
        this.missCount++;
      }
    }

    return validRuns;
  }

  async invalidateRunDefinition(runId: string): Promise<void> {
    if (!this.db) throw new Error('Cache not initialized');

    const key = this.generateRunKey(runId);
    const transaction = this.db.transaction(['runs'], 'readwrite');
    const store = transaction.objectStore('runs');
    
    await this.promisifyRequest(store.delete(key));
    this.updateStats();
  }

  // Agent response caching
  async cacheAgentResponse<T extends HillMetrics | WeatherData | EquipmentData>(
    agentType: 'hill-metrics' | 'weather' | 'equipment',
    skiAreaId: string,
    data: T,
    customExpiration?: number
  ): Promise<void> {
    if (!this.db) throw new Error('Cache not initialized');

    const key = this.generateAgentKey(agentType, skiAreaId);
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      expiresAt: Date.now() + (customExpiration || this.config.agentCacheDuration),
      version: this.config.version,
      key
    };

    const transaction = this.db.transaction(['agents'], 'readwrite');
    const store = transaction.objectStore('agents');
    
    await this.promisifyRequest(store.put({
      ...entry,
      agentType,
      skiAreaId
    }));

    this.updateStats();
  }

  async getCachedAgentResponse<T extends HillMetrics | WeatherData | EquipmentData>(
    agentType: 'hill-metrics' | 'weather' | 'equipment',
    skiAreaId: string
  ): Promise<T | null> {
    if (!this.db) throw new Error('Cache not initialized');

    const key = this.generateAgentKey(agentType, skiAreaId);
    const transaction = this.db.transaction(['agents'], 'readonly');
    const store = transaction.objectStore('agents');
    
    const result = await this.promisifyRequest(store.get(key));
    
    if (!result) {
      this.missCount++;
      return null;
    }

    if (this.isExpired(result)) {
      await this.invalidateAgentResponse(agentType, skiAreaId);
      this.missCount++;
      return null;
    }

    this.hitCount++;
    return result.data;
  }

  async invalidateAgentResponse(
    agentType: 'hill-metrics' | 'weather' | 'equipment',
    skiAreaId: string
  ): Promise<void> {
    if (!this.db) throw new Error('Cache not initialized');

    const key = this.generateAgentKey(agentType, skiAreaId);
    const transaction = this.db.transaction(['agents'], 'readwrite');
    const store = transaction.objectStore('agents');
    
    await this.promisifyRequest(store.delete(key));
    this.updateStats();
  }

  // Offline mode support
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

    // Try to get cached agent data (optional for offline mode)
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

  // Cache cleanup and maintenance
  async cleanup(): Promise<void> {
    if (!this.db) throw new Error('Cache not initialized');

    const now = Date.now();
    const stores = ['terrain', 'runs', 'agents'];
    
    for (const storeName of stores) {
      const transaction = this.db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const index = store.index('expiresAt');
      
      // Get all expired entries
      const range = IDBKeyRange.upperBound(now);
      const expiredEntries = await this.promisifyRequest(index.getAll(range));
      
      // Delete expired entries
      for (const entry of expiredEntries) {
        await this.promisifyRequest(store.delete(entry.key));
      }
    }

    this.stats.lastCleanup = now;
    this.updateStats();
  }

  async clearCache(): Promise<void> {
    if (!this.db) throw new Error('Cache not initialized');

    const stores = ['terrain', 'runs', 'agents'];
    
    for (const storeName of stores) {
      const transaction = this.db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      await this.promisifyRequest(store.clear());
    }

    this.resetStats();
  }

  async getCacheStats(): Promise<CacheStats> {
    await this.updateStats();
    return {
      ...this.stats,
      hitRate: this.hitCount + this.missCount > 0 
        ? this.hitCount / (this.hitCount + this.missCount) 
        : 0
    };
  }

  // Private helper methods
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

  private async promisifyRequest<T>(request: IDBRequest<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  private async updateStats(): Promise<void> {
    if (!this.db) return;

    let totalSize = 0;
    let entryCount = 0;
    
    const stores = ['terrain', 'runs', 'agents'];
    
    for (const storeName of stores) {
      const transaction = this.db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      const allEntries = await this.promisifyRequest(store.getAll());
      
      entryCount += allEntries.length;
      
      // Estimate size (rough calculation)
      for (const entry of allEntries) {
        totalSize += JSON.stringify(entry).length;
      }
    }

    this.stats.totalSize = totalSize;
    this.stats.entryCount = entryCount;
  }

  private resetStats(): void {
    this.stats = {
      totalSize: 0,
      entryCount: 0,
      hitRate: 0,
      lastCleanup: Date.now()
    };
    this.hitCount = 0;
    this.missCount = 0;
  }

  async close(): Promise<void> {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }
}

// Singleton instance
export const cacheManager = new CacheManager();