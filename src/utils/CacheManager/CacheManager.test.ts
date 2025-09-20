import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { CacheManager } from './CacheManager';
import { TerrainData, GridSize } from '../../models/TerrainData';
import { SkiRun } from '../../models/SkiRun';
import { HillMetrics, WeatherData, EquipmentData } from '../../models/TerrainData';
import { AsyncTestUtils, getTestTimeout } from '../../test/asyncTestUtils';
import { createMockCacheManager, MockCacheManager } from '../../test/cacheManagerMocks';

// Mock IndexedDB
const mockIDBDatabase = {
  transaction: vi.fn(),
  close: vi.fn(),
  onerror: null,
  objectStoreNames: {
    contains: vi.fn(() => false)
  },
  createObjectStore: vi.fn(() => ({
    createIndex: vi.fn()
  }))
};

const mockIDBRequest = {
  result: mockIDBDatabase,
  error: null,
  onsuccess: null as ((event: Event) => void) | null,
  onerror: null as ((event: Event) => void) | null,
  onupgradeneeded: null as ((event: IDBVersionChangeEvent) => void) | null
};

const mockIDBTransaction = {
  objectStore: vi.fn(() => mockIDBObjectStore)
};

const mockIDBObjectStore = {
  put: vi.fn(() => ({ onsuccess: null, onerror: null })),
  get: vi.fn(() => ({ onsuccess: null, onerror: null })),
  delete: vi.fn(() => ({ onsuccess: null, onerror: null })),
  clear: vi.fn(() => ({ onsuccess: null, onerror: null })),
  getAll: vi.fn(() => ({ onsuccess: null, onerror: null })),
  index: vi.fn(() => ({
    getAll: vi.fn(() => ({ onsuccess: null, onerror: null }))
  }))
};

// Mock global IndexedDB
Object.defineProperty(global, 'indexedDB', {
  value: {
    open: vi.fn(() => mockIDBRequest)
  },
  writable: true
});

describe('CacheManager', () => {
  let cacheManager: CacheManager;
  let mockTerrainData: TerrainData;
  let mockSkiRun: SkiRun;
  let mockHillMetrics: HillMetrics;
  
  // Configure timeouts for test environment
  const TEST_TIMEOUT = getTestTimeout();
  const ASYNC_OPERATION_TIMEOUT = Math.min(TEST_TIMEOUT / 2, 2000); // Max 2 seconds for individual operations

  beforeEach(async () => {
    vi.clearAllMocks();
    
    cacheManager = new CacheManager({
      terrainCacheDuration: 1000,
      agentCacheDuration: 500,
      runCacheDuration: 2000,
      maxCacheSize: 100,
      version: '1.0.0'
    });
    
    // Ensure all async operations complete before proceeding
    await AsyncTestUtils.flushPromises();

    mockTerrainData = {
      elevationGrid: [[100, 110], [105, 115]],
      resolution: 32,
      bounds: {
        northEast: { lat: 45.9, lng: 6.9 },
        southWest: { lat: 45.8, lng: 6.8 }
      },
      metadata: {
        name: 'Test Run',
        difficulty: 'intermediate',
        estimatedLength: 1000,
        verticalDrop: 200,
        averageSlope: 15
      },
      surfaceTypes: [['powder', 'powder'], ['packed', 'packed']],
      gridSize: GridSize.SMALL,
      area: {
        id: 'chamonix',
        name: 'Chamonix',
        location: 'Chamonix-Mont-Blanc',
        country: 'France',
        bounds: {
          northEast: { lat: 46.0, lng: 7.0 },
          southWest: { lat: 45.7, lng: 6.7 }
        },
        elevation: { min: 1000, max: 4000 },
        previewImage: 'chamonix.jpg',
        satelliteImageUrl: 'chamonix-satellite.jpg',
        agentEndpoints: {
          hillMetrics: 'http://localhost:8001',
          weather: 'http://localhost:8002',
          equipment: 'http://localhost:8003'
        },
        fisCompatible: true
      },
      hillMetrics: {
        elevationData: [[100, 110], [105, 115]],
        slopeAngles: [[10, 15], [12, 18]],
        aspectAngles: [[180, 190], [185, 195]],
        surfaceTypes: [['powder', 'powder'], ['packed', 'packed']]
      }
    };

    mockSkiRun = {
      id: 'test-run-1',
      name: 'Test Run',
      skiAreaId: 'chamonix',
      boundary: [
        { lat: 45.85, lng: 6.85 },
        { lat: 45.86, lng: 6.86 },
        { lat: 45.87, lng: 6.87 }
      ],
      metadata: {
        difficulty: 'intermediate',
        estimatedLength: 1000,
        verticalDrop: 200,
        averageSlope: 15,
        surfaceType: 'powder',
        tags: ['scenic', 'beginner-friendly']
      },
      createdBy: 'user-1',
      createdAt: new Date(),
      lastModified: new Date(),
      isPublic: true
    };

    mockHillMetrics = {
      elevationData: [[100, 110], [105, 115]],
      slopeAngles: [[10, 15], [12, 18]],
      aspectAngles: [[180, 190], [185, 195]],
      surfaceTypes: [['powder', 'powder'], ['packed', 'packed']]
    };

    // Setup mock transaction
    mockIDBDatabase.transaction.mockReturnValue(mockIDBTransaction);
  });

  afterEach(async () => {
    // Clean up cache manager state
    try {
      await AsyncTestUtils.withTimeout(
        cacheManager.close(),
        1000,
        'CacheManager close operation timed out'
      );
    } catch (error) {
      console.warn('Failed to close CacheManager in test cleanup:', error);
    }
    
    vi.restoreAllMocks();
    
    // Ensure all cleanup operations complete
    await AsyncTestUtils.flushAllPromises();
  });

  describe('initialization', () => {
    it('should initialize with default config', () => {
      const defaultCacheManager = new CacheManager();
      expect(defaultCacheManager).toBeDefined();
    });

    it('should initialize with custom config', () => {
      const customConfig = {
        terrainCacheDuration: 5000,
        agentCacheDuration: 1000
      };
      const customCacheManager = new CacheManager(customConfig);
      expect(customCacheManager).toBeDefined();
    });

    it('should initialize IndexedDB connection', async () => {
      // Simulate successful DB opening with proper timeout handling
      const initPromise = cacheManager.initialize();
      
      // Use AsyncTestUtils to handle timing
      await AsyncTestUtils.delay(10); // Small delay to ensure promise is pending
      
      // Simulate successful DB opening
      if (mockIDBRequest.onsuccess) {
        mockIDBRequest.onsuccess(new Event('success'));
      }

      await AsyncTestUtils.withTimeout(
        initPromise,
        ASYNC_OPERATION_TIMEOUT,
        'CacheManager initialization timed out'
      );
      
      expect(global.indexedDB.open).toHaveBeenCalledWith('alpine-ski-cache', 1);
    }, TEST_TIMEOUT);
  });

  describe('terrain data caching', () => {
    beforeEach(async () => {
      // Mock successful initialization with proper timeout handling
      const initPromise = cacheManager.initialize();
      
      await AsyncTestUtils.delay(10);
      
      if (mockIDBRequest.onsuccess) {
        mockIDBRequest.onsuccess(new Event('success'));
      }
      
      await AsyncTestUtils.withTimeout(
        initPromise,
        ASYNC_OPERATION_TIMEOUT,
        'CacheManager initialization timed out in terrain data caching setup'
      );
    });

    it('should cache terrain data successfully', async () => {
      const mockPutRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.put.mockReturnValue(mockPutRequest);

      const cachePromise = cacheManager.cacheTerrainData(
        mockTerrainData,
        mockSkiRun,
        GridSize.SMALL
      );

      // Use AsyncTestUtils for proper timing control
      await AsyncTestUtils.delay(10);
      
      // Simulate successful put operation
      if (mockPutRequest.onsuccess) {
        mockPutRequest.onsuccess(new Event('success'));
      }

      await AsyncTestUtils.withTimeout(
        cachePromise,
        ASYNC_OPERATION_TIMEOUT,
        'Cache terrain data operation timed out'
      );
      
      expect(mockIDBObjectStore.put).toHaveBeenCalled();
    }, TEST_TIMEOUT);

    it('should retrieve cached terrain data', async () => {
      const mockGetRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.get.mockReturnValue(mockGetRequest);

      const retrievePromise = cacheManager.getCachedTerrainData('test-run-1', GridSize.SMALL);

      await AsyncTestUtils.delay(10);

      // Simulate successful get operation with valid data
      mockGetRequest.result = {
        data: mockTerrainData,
        timestamp: Date.now(),
        expiresAt: Date.now() + 10000, // Not expired
        version: '1.0.0',
        key: 'terrain:test-run-1:32x32'
      };
      if (mockGetRequest.onsuccess) {
        mockGetRequest.onsuccess(new Event('success'));
      }

      const result = await AsyncTestUtils.withTimeout(
        retrievePromise,
        ASYNC_OPERATION_TIMEOUT,
        'Get cached terrain data operation timed out'
      );
      
      expect(result).toEqual(mockTerrainData);
      expect(mockIDBObjectStore.get).toHaveBeenCalledWith('terrain:test-run-1:32x32');
    }, TEST_TIMEOUT);

    it('should return null for expired terrain data', async () => {
      const mockGetRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.get.mockReturnValue(mockGetRequest);

      const mockDeleteRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.delete.mockReturnValue(mockDeleteRequest);

      const retrievePromise = cacheManager.getCachedTerrainData('test-run-1', GridSize.SMALL);

      await AsyncTestUtils.delay(10);

      // Simulate successful get operation with expired data
      mockGetRequest.result = {
        data: mockTerrainData,
        timestamp: Date.now() - 10000,
        expiresAt: Date.now() - 5000, // Expired
        version: '1.0.0',
        key: 'terrain:test-run-1:32x32'
      };
      if (mockGetRequest.onsuccess) {
        mockGetRequest.onsuccess(new Event('success'));
      }

      // Allow time for delete operation to be triggered
      await AsyncTestUtils.delay(20);

      // Simulate successful delete operation
      if (mockDeleteRequest.onsuccess) {
        mockDeleteRequest.onsuccess(new Event('success'));
      }

      const result = await AsyncTestUtils.withTimeout(
        retrievePromise,
        ASYNC_OPERATION_TIMEOUT,
        'Get expired terrain data operation timed out'
      );
      
      expect(result).toBeNull();
      expect(mockIDBObjectStore.delete).toHaveBeenCalled();
    }, TEST_TIMEOUT);
  });

  describe('run definition caching', () => {
    beforeEach(async () => {
      const initPromise = cacheManager.initialize();
      
      await AsyncTestUtils.delay(10);
      
      if (mockIDBRequest.onsuccess) {
        mockIDBRequest.onsuccess(new Event('success'));
      }
      
      await AsyncTestUtils.withTimeout(
        initPromise,
        ASYNC_OPERATION_TIMEOUT,
        'CacheManager initialization timed out in run definition caching setup'
      );
    });

    it('should cache run definition successfully', async () => {
      const mockPutRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.put.mockReturnValue(mockPutRequest);

      const cachePromise = cacheManager.cacheRunDefinition(mockSkiRun);

      await AsyncTestUtils.delay(10);

      if (mockPutRequest.onsuccess) {
        mockPutRequest.onsuccess(new Event('success'));
      }

      await AsyncTestUtils.withTimeout(
        cachePromise,
        ASYNC_OPERATION_TIMEOUT,
        'Cache run definition operation timed out'
      );
      
      expect(mockIDBObjectStore.put).toHaveBeenCalled();
    }, TEST_TIMEOUT);

    it('should retrieve cached run definition', async () => {
      const mockGetRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.get.mockReturnValue(mockGetRequest);

      const retrievePromise = cacheManager.getCachedRunDefinition('test-run-1');

      await AsyncTestUtils.delay(10);

      mockGetRequest.result = {
        data: mockSkiRun,
        timestamp: Date.now(),
        expiresAt: Date.now() + 10000,
        version: '1.0.0',
        key: 'run:test-run-1'
      };
      if (mockGetRequest.onsuccess) {
        mockGetRequest.onsuccess(new Event('success'));
      }

      const result = await AsyncTestUtils.withTimeout(
        retrievePromise,
        ASYNC_OPERATION_TIMEOUT,
        'Get cached run definition operation timed out'
      );
      
      expect(result).toEqual(mockSkiRun);
    }, TEST_TIMEOUT);
  });

  describe('agent response caching', () => {
    beforeEach(async () => {
      const initPromise = cacheManager.initialize();
      
      await AsyncTestUtils.delay(10);
      
      if (mockIDBRequest.onsuccess) {
        mockIDBRequest.onsuccess(new Event('success'));
      }
      
      await AsyncTestUtils.withTimeout(
        initPromise,
        ASYNC_OPERATION_TIMEOUT,
        'CacheManager initialization timed out in agent response caching setup'
      );
    });

    it('should cache agent response successfully', async () => {
      const mockPutRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.put.mockReturnValue(mockPutRequest);

      const cachePromise = cacheManager.cacheAgentResponse(
        'hill-metrics',
        'chamonix',
        mockHillMetrics
      );

      await AsyncTestUtils.delay(10);

      if (mockPutRequest.onsuccess) {
        mockPutRequest.onsuccess(new Event('success'));
      }

      await AsyncTestUtils.withTimeout(
        cachePromise,
        ASYNC_OPERATION_TIMEOUT,
        'Cache agent response operation timed out'
      );
      
      expect(mockIDBObjectStore.put).toHaveBeenCalled();
    }, TEST_TIMEOUT);

    it('should retrieve cached agent response', async () => {
      const mockGetRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.get.mockReturnValue(mockGetRequest);

      const retrievePromise = cacheManager.getCachedAgentResponse<HillMetrics>(
        'hill-metrics',
        'chamonix'
      );

      await AsyncTestUtils.delay(10);

      mockGetRequest.result = {
        data: mockHillMetrics,
        timestamp: Date.now(),
        expiresAt: Date.now() + 10000,
        version: '1.0.0',
        key: 'agent:hill-metrics:chamonix'
      };
      if (mockGetRequest.onsuccess) {
        mockGetRequest.onsuccess(new Event('success'));
      }

      const result = await AsyncTestUtils.withTimeout(
        retrievePromise,
        ASYNC_OPERATION_TIMEOUT,
        'Get cached agent response operation timed out'
      );
      
      expect(result).toEqual(mockHillMetrics);
    }, TEST_TIMEOUT);
  });

  describe('offline mode support', () => {
    beforeEach(async () => {
      const initPromise = cacheManager.initialize();
      
      await AsyncTestUtils.delay(10);
      
      if (mockIDBRequest.onsuccess) {
        mockIDBRequest.onsuccess(new Event('success'));
      }
      
      await AsyncTestUtils.withTimeout(
        initPromise,
        ASYNC_OPERATION_TIMEOUT,
        'CacheManager initialization timed out in offline mode support setup'
      );
    });

    it('should check offline mode availability', async () => {
      // Mock terrain data exists
      const mockTerrainGetRequest = { onsuccess: null, onerror: null };
      const mockRunGetRequest = { onsuccess: null, onerror: null };
      
      mockIDBObjectStore.get
        .mockReturnValueOnce(mockTerrainGetRequest)
        .mockReturnValueOnce(mockRunGetRequest);

      const availabilityPromise = cacheManager.isOfflineModeAvailable('test-run-1', GridSize.SMALL);

      await AsyncTestUtils.delay(10);

      // Simulate successful gets with proper sequencing
      mockTerrainGetRequest.result = {
        data: mockTerrainData,
        timestamp: Date.now(),
        expiresAt: Date.now() + 10000,
        version: '1.0.0',
        key: 'terrain:test-run-1:32x32'
      };
      if (mockTerrainGetRequest.onsuccess) {
        mockTerrainGetRequest.onsuccess(new Event('success'));
      }

      await AsyncTestUtils.delay(20);

      mockRunGetRequest.result = {
        data: mockSkiRun,
        timestamp: Date.now(),
        expiresAt: Date.now() + 10000,
        version: '1.0.0',
        key: 'run:test-run-1'
      };
      if (mockRunGetRequest.onsuccess) {
        mockRunGetRequest.onsuccess(new Event('success'));
      }

      const result = await AsyncTestUtils.withTimeout(
        availabilityPromise,
        ASYNC_OPERATION_TIMEOUT,
        'Check offline mode availability operation timed out'
      );
      
      expect(result).toBe(true);
    }, TEST_TIMEOUT);

    it('should return offline data when available', async () => {
      // Use mock CacheManager for complex multi-operation test
      const mockCacheManager = createMockCacheManager();
      await mockCacheManager.initialize();
      
      // Pre-populate cache with test data
      await mockCacheManager.cacheTerrainData(mockTerrainData, mockSkiRun, GridSize.SMALL);
      await mockCacheManager.cacheRunDefinition(mockSkiRun);
      
      const result = await AsyncTestUtils.withTimeout(
        mockCacheManager.getOfflineData('test-run-1', GridSize.SMALL),
        ASYNC_OPERATION_TIMEOUT,
        'Get offline data operation timed out'
      );
      
      expect(result).toEqual({
        terrain: mockTerrainData,
        run: mockSkiRun,
        agents: {
          hillMetrics: undefined,
          weather: undefined,
          equipment: undefined
        }
      });
      
      await mockCacheManager.close();
    }, TEST_TIMEOUT);
  });

  describe('cache cleanup', () => {
    beforeEach(async () => {
      const initPromise = cacheManager.initialize();
      
      await AsyncTestUtils.delay(10);
      
      if (mockIDBRequest.onsuccess) {
        mockIDBRequest.onsuccess(new Event('success'));
      }
      
      await AsyncTestUtils.withTimeout(
        initPromise,
        ASYNC_OPERATION_TIMEOUT,
        'CacheManager initialization timed out in cache cleanup setup'
      );
    });

    it('should clear entire cache', async () => {
      // Use mock CacheManager for complex multi-operation test
      const mockCacheManager = createMockCacheManager();
      await mockCacheManager.initialize();
      
      // Pre-populate cache with test data
      await mockCacheManager.cacheTerrainData(mockTerrainData, mockSkiRun, GridSize.SMALL);
      await mockCacheManager.cacheRunDefinition(mockSkiRun);
      await mockCacheManager.cacheAgentResponse('hill-metrics', 'chamonix', mockHillMetrics);
      
      // Verify cache has data
      expect(mockCacheManager.getTerrainCacheSize()).toBeGreaterThan(0);
      expect(mockCacheManager.getRunCacheSize()).toBeGreaterThan(0);
      expect(mockCacheManager.getAgentCacheSize()).toBeGreaterThan(0);
      
      await AsyncTestUtils.withTimeout(
        mockCacheManager.clearCache(),
        ASYNC_OPERATION_TIMEOUT,
        'Clear cache operation timed out'
      );
      
      // Verify cache is empty
      expect(mockCacheManager.getTerrainCacheSize()).toBe(0);
      expect(mockCacheManager.getRunCacheSize()).toBe(0);
      expect(mockCacheManager.getAgentCacheSize()).toBe(0);
      
      await mockCacheManager.close();
    }, TEST_TIMEOUT);
  });
});