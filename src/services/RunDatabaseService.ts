/**
 * Run Database Service using IndexedDB for local storage of user-defined runs
 * Requirements: 3.4, 10.6 - Store run geographic boundary coordinates and metadata
 */

import { SkiRun } from '../models/SkiRun';
import { cacheManager } from '../utils/CacheManager';

export interface RunDatabaseServiceInterface {
  createRun(run: Omit<SkiRun, 'id' | 'createdAt' | 'lastModified'>): Promise<SkiRun>;
  updateRun(id: string, updates: Partial<SkiRun>): Promise<SkiRun>;
  deleteRun(id: string): Promise<void>;
  getRunsByArea(skiAreaId: string): Promise<SkiRun[]>;
  getAllRuns(): Promise<SkiRun[]>;
  getRunById(id: string): Promise<SkiRun | null>;
  duplicateRun(id: string, newName: string): Promise<SkiRun>;
  clearAllRuns(): Promise<void>;
}

export class RunDatabaseService implements RunDatabaseServiceInterface {
  private readonly DB_NAME = 'AlpineSkiSimulator';
  private readonly DB_VERSION = 1;
  private readonly STORE_NAME = 'runs';
  private db: IDBDatabase | null = null;

  /**
   * Initialize the IndexedDB database
   */
  private async initDB(): Promise<IDBDatabase> {
    if (this.db) {
      return this.db;
    }

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.DB_NAME, this.DB_VERSION);

      request.onerror = () => {
        reject(new Error(`Failed to open database: ${request.error?.message}`));
      };

      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        
        // Create runs object store if it doesn't exist
        if (!db.objectStoreNames.contains(this.STORE_NAME)) {
          const store = db.createObjectStore(this.STORE_NAME, { keyPath: 'id' });
          
          // Create indexes for efficient querying
          store.createIndex('skiAreaId', 'skiAreaId', { unique: false });
          store.createIndex('createdBy', 'createdBy', { unique: false });
          store.createIndex('createdAt', 'createdAt', { unique: false });
          store.createIndex('isPublic', 'isPublic', { unique: false });
          store.createIndex('name', 'name', { unique: false });
        }
      };
    });
  }

  /**
   * Create a new run in the database
   * Requirements: 3.3, 3.4 - Save run with name, difficulty, and metadata
   */
  async createRun(runData: Omit<SkiRun, 'id' | 'createdAt' | 'lastModified'>): Promise<SkiRun> {
    const db = await this.initDB();
    
    const newRun: SkiRun = {
      ...runData,
      id: `run_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      createdAt: new Date(),
      lastModified: new Date()
    };

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.STORE_NAME], 'readwrite');
      const store = transaction.objectStore(this.STORE_NAME);
      const request = store.add(newRun);

      request.onsuccess = async () => {
        // Cache the run definition
        try {
          await cacheManager.cacheRunDefinition(newRun);
          console.log(`Cached new run definition: ${newRun.id}`);
        } catch (cacheError) {
          console.warn('Failed to cache run definition:', cacheError);
          // Continue without caching - don't fail the entire operation
        }
        resolve(newRun);
      };

      request.onerror = () => {
        reject(new Error(`Failed to create run: ${request.error?.message}`));
      };
    });
  }

  /**
   * Update an existing run
   */
  async updateRun(id: string, updates: Partial<SkiRun>): Promise<SkiRun> {
    const db = await this.initDB();
    
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.STORE_NAME], 'readwrite');
      const store = transaction.objectStore(this.STORE_NAME);
      const getRequest = store.get(id);

      getRequest.onsuccess = () => {
        const existingRun = getRequest.result;
        if (!existingRun) {
          reject(new Error(`Run with id ${id} not found`));
          return;
        }

        const updatedRun: SkiRun = {
          ...existingRun,
          ...updates,
          id, // Ensure ID cannot be changed
          lastModified: new Date()
        };

        const putRequest = store.put(updatedRun);
        
        putRequest.onsuccess = async () => {
          // Update cache with the modified run
          try {
            await cacheManager.cacheRunDefinition(updatedRun);
            console.log(`Updated cached run definition: ${updatedRun.id}`);
          } catch (cacheError) {
            console.warn('Failed to update cached run definition:', cacheError);
            // Continue without caching - don't fail the entire operation
          }
          resolve(updatedRun);
        };

        putRequest.onerror = () => {
          reject(new Error(`Failed to update run: ${putRequest.error?.message}`));
        };
      };

      getRequest.onerror = () => {
        reject(new Error(`Failed to get run for update: ${getRequest.error?.message}`));
      };
    });
  }

  /**
   * Delete a run from the database
   */
  async deleteRun(id: string): Promise<void> {
    const db = await this.initDB();
    
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.STORE_NAME], 'readwrite');
      const store = transaction.objectStore(this.STORE_NAME);
      const request = store.delete(id);

      request.onsuccess = async () => {
        // Invalidate cache for the deleted run
        try {
          await cacheManager.invalidateRunDefinition(id);
          console.log(`Invalidated cached run definition: ${id}`);
        } catch (cacheError) {
          console.warn('Failed to invalidate cached run definition:', cacheError);
          // Continue without cache invalidation - don't fail the entire operation
        }
        resolve();
      };

      request.onerror = () => {
        reject(new Error(`Failed to delete run: ${request.error?.message}`));
      };
    });
  }

  /**
   * Get all runs for a specific ski area
   * Requirements: 3.5 - Display saved runs for each ski area
   */
  async getRunsByArea(skiAreaId: string): Promise<SkiRun[]> {
    // Try cache first
    try {
      const cachedRuns = await cacheManager.getCachedRunsByArea(skiAreaId);
      if (cachedRuns.length > 0) {
        console.log(`Using cached runs for area ${skiAreaId}`);
        return cachedRuns.sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
      }
    } catch (cacheError) {
      console.warn('Failed to get cached runs:', cacheError);
      // Continue with database query
    }

    const db = await this.initDB();
    
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.STORE_NAME], 'readonly');
      const store = transaction.objectStore(this.STORE_NAME);
      const index = store.index('skiAreaId');
      const request = index.getAll(skiAreaId);

      request.onsuccess = async () => {
        const runs = request.result.map(this.deserializeRun);
        // Sort by creation date, newest first
        runs.sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
        
        // Cache the runs
        try {
          for (const run of runs) {
            await cacheManager.cacheRunDefinition(run);
          }
          console.log(`Cached ${runs.length} runs for area ${skiAreaId}`);
        } catch (cacheError) {
          console.warn('Failed to cache runs:', cacheError);
          // Continue without caching - don't fail the entire operation
        }
        
        resolve(runs);
      };

      request.onerror = () => {
        reject(new Error(`Failed to get runs for area: ${request.error?.message}`));
      };
    });
  }

  /**
   * Get all runs from the database
   */
  async getAllRuns(): Promise<SkiRun[]> {
    const db = await this.initDB();
    
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.STORE_NAME], 'readonly');
      const store = transaction.objectStore(this.STORE_NAME);
      const request = store.getAll();

      request.onsuccess = () => {
        const runs = request.result.map(this.deserializeRun);
        // Sort by creation date, newest first
        runs.sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
        resolve(runs);
      };

      request.onerror = () => {
        reject(new Error(`Failed to get all runs: ${request.error?.message}`));
      };
    });
  }

  /**
   * Get a specific run by ID
   */
  async getRunById(id: string): Promise<SkiRun | null> {
    const db = await this.initDB();
    
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.STORE_NAME], 'readonly');
      const store = transaction.objectStore(this.STORE_NAME);
      const request = store.get(id);

      request.onsuccess = () => {
        const run = request.result;
        resolve(run ? this.deserializeRun(run) : null);
      };

      request.onerror = () => {
        reject(new Error(`Failed to get run by ID: ${request.error?.message}`));
      };
    });
  }

  /**
   * Duplicate an existing run with a new name
   * Requirements: 10.7 - Run editing, duplication, and deletion functionality
   */
  async duplicateRun(id: string, newName: string): Promise<SkiRun> {
    const originalRun = await this.getRunById(id);
    if (!originalRun) {
      throw new Error(`Run with id ${id} not found`);
    }

    const duplicatedRun = {
      ...originalRun,
      name: newName,
      metadata: {
        ...originalRun.metadata,
        tags: [...originalRun.metadata.tags, 'duplicate']
      }
    };

    // Remove id, createdAt, and lastModified so they get regenerated
    const { id: _, createdAt: __, lastModified: ___, ...runData } = duplicatedRun;
    
    return this.createRun(runData);
  }

  /**
   * Clear all runs from the database (for testing/reset purposes)
   */
  async clearAllRuns(): Promise<void> {
    const db = await this.initDB();
    
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.STORE_NAME], 'readwrite');
      const store = transaction.objectStore(this.STORE_NAME);
      const request = store.clear();

      request.onsuccess = () => {
        resolve();
      };

      request.onerror = () => {
        reject(new Error(`Failed to clear runs: ${request.error?.message}`));
      };
    });
  }

  /**
   * Deserialize run data from IndexedDB (convert date strings back to Date objects)
   */
  private deserializeRun(run: any): SkiRun {
    return {
      ...run,
      createdAt: new Date(run.createdAt),
      lastModified: new Date(run.lastModified)
    };
  }

  /**
   * Get database statistics
   */
  async getStats(): Promise<{
    totalRuns: number;
    runsByArea: Record<string, number>;
    oldestRun: Date | null;
    newestRun: Date | null;
  }> {
    const allRuns = await this.getAllRuns();
    
    const runsByArea: Record<string, number> = {};
    let oldestRun: Date | null = null;
    let newestRun: Date | null = null;

    for (const run of allRuns) {
      // Count runs by area
      runsByArea[run.skiAreaId] = (runsByArea[run.skiAreaId] || 0) + 1;
      
      // Track oldest and newest runs
      if (!oldestRun || run.createdAt < oldestRun) {
        oldestRun = run.createdAt;
      }
      if (!newestRun || run.createdAt > newestRun) {
        newestRun = run.createdAt;
      }
    }

    return {
      totalRuns: allRuns.length,
      runsByArea,
      oldestRun,
      newestRun
    };
  }
}

// Export singleton instance
export const runDatabaseService = new RunDatabaseService();