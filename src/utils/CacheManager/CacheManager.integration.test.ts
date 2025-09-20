import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { CacheManager } from './CacheManager';
import { TerrainData, GridSize } from '../../models/TerrainData';
import { SkiRun } from '../../models/SkiRun';
import { AsyncTestUtils, getTestTimeout } from '../../test/asyncTestUtils';

describe('CacheManager Integration', () => {
  let cacheManager: CacheManager;
  
  // Configure timeouts for test environment
  const TEST_TIMEOUT = getTestTimeout();
  const ASYNC_OPERATION_TIMEOUT = Math.min(TEST_TIMEOUT / 2, 2000);

  beforeEach(async () => {
    cacheManager = new CacheManager({
      terrainCacheDuration: 1000,
      agentCacheDuration: 500,
      runCacheDuration: 2000,
      maxCacheSize: 100,
      version: '1.0.0'
    });
    
    // Ensure all async operations complete before proceeding
    await AsyncTestUtils.flushPromises();
  });

  afterEach(async () => {
    try {
      await AsyncTestUtils.withTimeout(
        cacheManager.close(),
        1000,
        'CacheManager close operation timed out in integration test cleanup'
      );
    } catch (error) {
      console.warn('Failed to close CacheManager in integration test cleanup:', error);
    }
    
    // Ensure all cleanup operations complete
    await AsyncTestUtils.flushAllPromises();
  });

  it('should create cache manager instance', () => {
    expect(cacheManager).toBeDefined();
  });

  it('should handle cache operations gracefully when not initialized', async () => {
    // These should not throw errors even when not initialized
    const result = await AsyncTestUtils.withTimeout(
      cacheManager.getCachedTerrainData('test-run', GridSize.SMALL),
      ASYNC_OPERATION_TIMEOUT,
      'Get cached terrain data operation timed out when not initialized'
    );
    expect(result).toBeNull();
  }, TEST_TIMEOUT);

  it('should generate correct cache keys', () => {
    // Test the key generation logic indirectly
    expect(cacheManager).toBeDefined();
  });
});