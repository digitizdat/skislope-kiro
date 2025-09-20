/**
 * Integration tests for browser API mocks with the test environment
 * Tests that all browser APIs work correctly in the test setup
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  initializeTestEnvironment,
  teardownTestEnvironment,
  resetTestEnvironment,
  isWebGLAvailable,
  isIndexedDBAvailable,
} from './testSetup';

describe('Browser API Integration Tests', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  afterEach(async () => {
    await teardownTestEnvironment();
  });

  describe('Storage APIs', () => {
    it('should have localStorage available', () => {
      expect(globalThis.localStorage).toBeDefined();
      expect(typeof globalThis.localStorage.setItem).toBe('function');
      expect(typeof globalThis.localStorage.getItem).toBe('function');
      expect(typeof globalThis.localStorage.removeItem).toBe('function');
      expect(typeof globalThis.localStorage.clear).toBe('function');
    });

    it('should have sessionStorage available', () => {
      expect(globalThis.sessionStorage).toBeDefined();
      expect(typeof globalThis.sessionStorage.setItem).toBe('function');
      expect(typeof globalThis.sessionStorage.getItem).toBe('function');
      expect(typeof globalThis.sessionStorage.removeItem).toBe('function');
      expect(typeof globalThis.sessionStorage.clear).toBe('function');
    });

    it('should work with localStorage operations', () => {
      globalThis.localStorage.setItem('test-key', 'test-value');
      expect(globalThis.localStorage.getItem('test-key')).toBe('test-value');
      
      globalThis.localStorage.removeItem('test-key');
      expect(globalThis.localStorage.getItem('test-key')).toBeNull();
    });

    it('should work with sessionStorage operations', () => {
      globalThis.sessionStorage.setItem('session-key', 'session-value');
      expect(globalThis.sessionStorage.getItem('session-key')).toBe('session-value');
      
      globalThis.sessionStorage.clear();
      expect(globalThis.sessionStorage.getItem('session-key')).toBeNull();
    });

    it('should maintain separate storage for localStorage and sessionStorage', () => {
      globalThis.localStorage.setItem('shared-key', 'local-value');
      globalThis.sessionStorage.setItem('shared-key', 'session-value');
      
      expect(globalThis.localStorage.getItem('shared-key')).toBe('local-value');
      expect(globalThis.sessionStorage.getItem('shared-key')).toBe('session-value');
    });
  });

  describe('Network APIs', () => {
    it('should have fetch available', () => {
      expect(globalThis.fetch).toBeDefined();
      expect(typeof globalThis.fetch).toBe('function');
    });

    it('should have XMLHttpRequest available', () => {
      expect(globalThis.XMLHttpRequest).toBeDefined();
      expect(typeof globalThis.XMLHttpRequest).toBe('function');
    });

    it('should work with fetch API', async () => {
      const response = await globalThis.fetch('https://example.com/api');
      
      expect(response).toBeDefined();
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);
      expect(typeof response.json).toBe('function');
      expect(typeof response.text).toBe('function');
    });

    it('should work with XMLHttpRequest', () => {
      const xhr = new globalThis.XMLHttpRequest();
      
      expect(xhr).toBeDefined();
      expect(xhr.readyState).toBe(0);
      expect(typeof xhr.open).toBe('function');
      expect(typeof xhr.send).toBe('function');
      expect(typeof xhr.abort).toBe('function');
    });

    it('should handle XMLHttpRequest lifecycle', async () => {
      const xhr = new globalThis.XMLHttpRequest();
      
      const promise = new Promise<void>((resolve, reject) => {
        xhr.onreadystatechange = () => {
          if (xhr.readyState === 4) {
            try {
              expect(xhr.status).toBe(200);
              expect(xhr.statusText).toBe('OK');
              resolve();
            } catch (error) {
              reject(error);
            }
          }
        };
        
        xhr.onerror = () => reject(new Error('XMLHttpRequest failed'));
      });
      
      xhr.open('GET', 'https://example.com/api');
      xhr.send();
      
      await promise;
    });
  });

  describe('Web Audio API', () => {
    it('should have AudioContext available', () => {
      expect(globalThis.AudioContext).toBeDefined();
      expect(typeof globalThis.AudioContext).toBe('function');
    });

    it('should create AudioContext instances', () => {
      const audioContext = new globalThis.AudioContext();
      
      expect(audioContext).toBeDefined();
      expect(audioContext.state).toBe('suspended');
      expect(audioContext.sampleRate).toBe(44100);
      expect(typeof audioContext.createOscillator).toBe('function');
      expect(typeof audioContext.createGain).toBe('function');
    });

    it('should create audio nodes', () => {
      const audioContext = new globalThis.AudioContext();
      
      const oscillator = audioContext.createOscillator();
      expect(oscillator).toBeDefined();
      expect(oscillator.type).toBe('sine');
      expect(oscillator.frequency.value).toBe(440);
      
      const gainNode = audioContext.createGain();
      expect(gainNode).toBeDefined();
      expect(gainNode.gain.value).toBe(1);
    });

    it('should handle audio context state changes', async () => {
      const audioContext = new globalThis.AudioContext();
      
      expect(audioContext.state).toBe('suspended');
      
      await audioContext.resume();
      expect(audioContext.state).toBe('running');
      
      await audioContext.suspend();
      expect(audioContext.state).toBe('suspended');
    });

    it('should create audio buffers', () => {
      const audioContext = new globalThis.AudioContext();
      const buffer = audioContext.createBuffer(2, 44100, 44100);
      
      expect(buffer).toBeDefined();
      expect(buffer.numberOfChannels).toBe(2);
      expect(buffer.length).toBe(44100);
      expect(buffer.sampleRate).toBe(44100);
      expect(buffer.duration).toBe(1);
    });
  });

  describe('File and Blob APIs', () => {
    it('should have Blob available', () => {
      expect(globalThis.Blob).toBeDefined();
      expect(typeof globalThis.Blob).toBe('function');
    });

    it('should have File available', () => {
      expect(globalThis.File).toBeDefined();
      expect(typeof globalThis.File).toBe('function');
    });

    it('should create Blob instances', () => {
      const blob = new globalThis.Blob(['Hello, World!'], { type: 'text/plain' });
      
      expect(blob).toBeDefined();
      expect(blob.size).toBe(13);
      expect(blob.type).toBe('text/plain');
      expect(typeof blob.slice).toBe('function');
      expect(typeof blob.text).toBe('function');
    });

    it('should create File instances', () => {
      const file = new globalThis.File(['Hello, World!'], 'test.txt', { 
        type: 'text/plain',
        lastModified: 1234567890 
      });
      
      expect(file).toBeDefined();
      expect(file.name).toBe('test.txt');
      expect(file.size).toBe(13);
      expect(file.type).toBe('text/plain');
      expect(file.lastModified).toBe(1234567890);
    });

    it('should handle blob operations', async () => {
      const blob = new globalThis.Blob(['Hello, World!'], { type: 'text/plain' });
      
      const text = await blob.text();
      expect(typeof text).toBe('string');
      
      const arrayBuffer = await blob.arrayBuffer();
      expect(arrayBuffer).toBeInstanceOf(ArrayBuffer);
      
      const slice = blob.slice(0, 5);
      expect(slice).toBeDefined();
    });
  });

  describe('URL API', () => {
    it('should have URL.createObjectURL available', () => {
      expect(globalThis.URL).toBeDefined();
      expect(typeof globalThis.URL.createObjectURL).toBe('function');
      expect(typeof globalThis.URL.revokeObjectURL).toBe('function');
    });

    it('should create and revoke object URLs', () => {
      const blob = new globalThis.Blob(['test data']);
      const url = globalThis.URL.createObjectURL(blob);
      
      expect(url).toBeDefined();
      expect(typeof url).toBe('string');
      expect(url).toMatch(/^blob:/);
      
      globalThis.URL.revokeObjectURL(url);
      // Should not throw
    });
  });

  describe('IndexedDB Integration', () => {
    it('should have IndexedDB available', () => {
      expect(isIndexedDBAvailable()).toBe(true);
      expect(globalThis.indexedDB).toBeDefined();
      expect(typeof globalThis.indexedDB.open).toBe('function');
    });

    it('should open IndexedDB databases', async () => {
      const request = globalThis.indexedDB.open('test-db', 1);
      
      const promise = new Promise<void>((resolve, reject) => {
        request.onsuccess = () => {
          try {
            const db = request.result;
            expect(db).toBeDefined();
            expect(db.name).toBe('test-db');
            db.close();
            resolve();
          } catch (error) {
            reject(error);
          }
        };
        
        request.onerror = () => {
          reject(new Error('Failed to open IndexedDB'));
        };
      });
      
      await promise;
    });
  });

  describe('WebGL Integration', () => {
    it('should have WebGL context available', () => {
      expect(isWebGLAvailable()).toBe(true);
    });

    it('should create canvas with WebGL context', () => {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl');
      
      expect(canvas).toBeDefined();
      expect(gl).toBeDefined();
      expect(gl.canvas).toBe(canvas);
      expect(typeof gl.clear).toBe('function');
      expect(typeof gl.createShader).toBe('function');
    });

    it('should work with Three.js-like operations', () => {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl');
      
      // Test basic WebGL operations that Three.js uses
      gl.clearColor(0.0, 0.0, 0.0, 1.0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      
      const shader = gl.createShader(gl.VERTEX_SHADER);
      expect(shader).toBeDefined();
      
      const program = gl.createProgram();
      expect(program).toBeDefined();
      
      const buffer = gl.createBuffer();
      expect(buffer).toBeDefined();
    });
  });

  describe('Environment Reset', () => {
    it('should reset storage between tests', async () => {
      // Set some data
      globalThis.localStorage.setItem('test-key', 'test-value');
      globalThis.sessionStorage.setItem('session-key', 'session-value');
      
      // Reset environment
      await resetTestEnvironment();
      
      // Check that data is cleared
      expect(globalThis.localStorage.getItem('test-key')).toBeNull();
      expect(globalThis.sessionStorage.getItem('session-key')).toBeNull();
    });

    it('should maintain API availability after reset', async () => {
      await resetTestEnvironment();
      
      // All APIs should still be available
      expect(globalThis.localStorage).toBeDefined();
      expect(globalThis.sessionStorage).toBeDefined();
      expect(globalThis.fetch).toBeDefined();
      expect(globalThis.XMLHttpRequest).toBeDefined();
      expect(globalThis.AudioContext).toBeDefined();
      expect(globalThis.Blob).toBeDefined();
      expect(globalThis.File).toBeDefined();
      expect(globalThis.indexedDB).toBeDefined();
    });
  });

  describe('Real-world Usage Scenarios', () => {
    it('should support CacheManager-like operations', async () => {
      // Simulate CacheManager operations
      const dbName = 'test-cache-db';
      const request = globalThis.indexedDB.open(dbName, 1);
      
      return new Promise<void>((resolve, reject) => {
        request.onupgradeneeded = () => {
          const db = request.result;
          const store = db.createObjectStore('cache', { keyPath: 'key' });
          store.createIndex('timestamp', 'timestamp');
        };
        
        request.onsuccess = async () => {
          const db = request.result;
          
          // Store data
          const transaction = db.transaction(['cache'], 'readwrite');
          const store = transaction.objectStore('cache');
          
          await new Promise<void>((resolveStore) => {
            const addRequest = store.add({
              key: 'test-data',
              value: { message: 'Hello, World!' },
              timestamp: Date.now()
            });
            
            addRequest.onsuccess = () => resolveStore();
            addRequest.onerror = () => reject(addRequest.error);
          });
          
          // Retrieve data
          const getTransaction = db.transaction(['cache'], 'readonly');
          const getStore = getTransaction.objectStore('cache');
          const getRequest = getStore.get('test-data');
          
          getRequest.onsuccess = () => {
            const result = getRequest.result;
            expect(result).toBeDefined();
            expect(result.key).toBe('test-data');
            expect(result.value.message).toBe('Hello, World!');
            
            db.close();
            resolve();
          };
          
          getRequest.onerror = () => reject(getRequest.error);
        };
        
        request.onerror = () => reject(request.error);
      });
    });

    it('should support AgentClient-like fetch operations', async () => {
      // Test JSON-RPC like request
      const response = await globalThis.fetch('http://localhost:8001/jsonrpc', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'getHillMetrics',
          params: { areaId: 'test-area' },
          id: 1,
        }),
      });
      
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);
      
      const data = await response.json();
      expect(data).toBeDefined();
    });

    it('should support audio service operations', () => {
      const audioContext = new globalThis.AudioContext();
      
      // Create audio graph like AudioService might
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      const panner = audioContext.createPanner();
      
      // Connect nodes
      oscillator.connect(gainNode);
      gainNode.connect(panner);
      panner.connect(audioContext.destination);
      
      // Configure nodes
      oscillator.frequency.value = 440;
      gainNode.gain.value = 0.5;
      panner.positionX.value = 1;
      panner.positionY.value = 0;
      panner.positionZ.value = 0;
      
      // Start/stop (should not throw)
      oscillator.start();
      oscillator.stop();
      
      expect(oscillator.frequency.value).toBe(440);
      expect(gainNode.gain.value).toBe(0.5);
      expect(panner.positionX.value).toBe(1);
    });

    it('should support file operations for terrain data', async () => {
      // Simulate terrain file processing
      const terrainData = new Uint8Array([1, 2, 3, 4, 5]);
      const blob = new globalThis.Blob([terrainData], { type: 'application/octet-stream' });
      const file = new globalThis.File([blob], 'terrain.dat', { type: 'application/octet-stream' });
      
      expect(file.name).toBe('terrain.dat');
      expect(file.size).toBe(5);
      
      const arrayBuffer = await file.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);
      
      expect(uint8Array.length).toBe(5);
      expect(Array.from(uint8Array)).toEqual([1, 2, 3, 4, 5]);
      
      // Create object URL for the file
      const url = globalThis.URL.createObjectURL(file);
      expect(url).toMatch(/^blob:/);
      
      globalThis.URL.revokeObjectURL(url);
    });
  });
});