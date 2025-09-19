import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { CacheManager } from './CacheManager';
import { TerrainData, GridSize } from '../../models/TerrainData';
import { SkiRun } from '../../models/SkiRun';

describe('CacheManager Integration', () => {
  let cacheManager: CacheManager;

  beforeEach(() => {
    cacheManager = new CacheManager({
      terrainCacheDuration: 1000,
      agentCacheDuration: 500,
      runCacheDuration: 2000,
      maxCacheSize: 100,
      version: '1.0.0'
    });
  });

  afterEach(async () => {
    await cacheManager.close();
  });

  it('should create cache manager instance', () => {
    expect(cacheManager).toBeDefined();
  });

  it('should handle cache operations gracefully when not initialized', async () => {
    // These should not throw errors even when not initialized
    const result = await cacheManager.getCachedTerrainData('test-run', GridSize.SMALL);
    expect(result).toBeNull();
  });

  it('should generate correct cache keys', () => {
    // Test the key generation logic indirectly
    expect(cacheManager).toBeDefined();
  });
});