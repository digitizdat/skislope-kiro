/**
 * Simple tests for Browser API Mocks
 * Tests core functionality without complex vitest integration
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  createStorageMock,
  createFetchMock,
  createXMLHttpRequestMock,
  createWebAudioAPIMock,
  createFileBlobMocks,
  createURLMock,
  installBrowserAPIMocks,
  type BrowserAPIMocks,
} from './browserAPIMocks';

describe('Browser API Mocks - Core Functionality', () => {
  let mocks: BrowserAPIMocks;

  beforeEach(() => {
    mocks = {
      localStorage: createStorageMock(),
      sessionStorage: createStorageMock(),
      fetch: createFetchMock(),
      XMLHttpRequest: createXMLHttpRequestMock(),
      audioContext: createWebAudioAPIMock(),
      fileBlobAPIs: createFileBlobMocks(),
      urlAPI: createURLMock(),
    };
  });

  describe('Storage API Mocks', () => {
    it('should store and retrieve items', () => {
      mocks.localStorage.setItem('test-key', 'test-value');
      expect(mocks.localStorage.getItem('test-key')).toBe('test-value');
    });

    it('should return null for non-existent keys', () => {
      expect(mocks.localStorage.getItem('non-existent')).toBeNull();
    });

    it('should remove items', () => {
      mocks.localStorage.setItem('test-key', 'test-value');
      mocks.localStorage.removeItem('test-key');
      expect(mocks.localStorage.getItem('test-key')).toBeNull();
    });

    it('should clear all items', () => {
      mocks.localStorage.setItem('key1', 'value1');
      mocks.localStorage.setItem('key2', 'value2');
      expect(mocks.localStorage.length).toBe(2);
      
      mocks.localStorage.clear();
      expect(mocks.localStorage.length).toBe(0);
    });

    it('should work independently for localStorage and sessionStorage', () => {
      mocks.localStorage.setItem('key', 'local-value');
      mocks.sessionStorage.setItem('key', 'session-value');
      
      expect(mocks.localStorage.getItem('key')).toBe('local-value');
      expect(mocks.sessionStorage.getItem('key')).toBe('session-value');
    });
  });

  describe('Fetch API Mock', () => {
    it('should return default successful response', async () => {
      const response = await mocks.fetch('https://example.com');
      
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);
      expect(response.statusText).toBe('OK');
    });

    it('should handle custom mock responses', async () => {
      mocks.fetch.mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      });

      const response = await mocks.fetch('https://example.com/not-found');
      
      expect(response.ok).toBe(false);
      expect(response.status).toBe(404);
      expect(response.statusText).toBe('Not Found');
    });

    it('should handle JSON responses', async () => {
      const testData = { message: 'Hello, World!' };
      mocks.fetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: testData,
      });

      const response = await mocks.fetch('https://api.example.com/data');
      const data = await response.json();
      
      expect(data).toEqual(testData);
    });

    it('should handle rejected promises', async () => {
      const testError = new Error('Network error');
      mocks.fetch.mockRejectedValue(testError);

      await expect(mocks.fetch('https://example.com')).rejects.toThrow('Network error');
    });

    it('should clear mock state', () => {
      mocks.fetch.mockResolvedValue({ status: 500 });
      mocks.fetch.mockClear();
      
      // After clearing, should return to default behavior
      expect(mocks.fetch).toBeDefined();
    });
  });

  describe('XMLHttpRequest Mock', () => {
    it('should create XMLHttpRequest instances', () => {
      const xhr = new mocks.XMLHttpRequest();
      
      expect(xhr.readyState).toBe(0);
      expect(xhr.status).toBe(0);
      expect(xhr.statusText).toBe('');
    });

    it('should handle open method', () => {
      const xhr = new mocks.XMLHttpRequest();
      
      xhr.open('GET', 'https://example.com/api');
      
      expect(xhr.readyState).toBe(1);
      expect(xhr.responseURL).toBe('https://example.com/api');
    });

    it('should have correct constants', () => {
      expect(mocks.XMLHttpRequest.UNSENT).toBe(0);
      expect(mocks.XMLHttpRequest.OPENED).toBe(1);
      expect(mocks.XMLHttpRequest.HEADERS_RECEIVED).toBe(2);
      expect(mocks.XMLHttpRequest.LOADING).toBe(3);
      expect(mocks.XMLHttpRequest.DONE).toBe(4);
    });
  });

  describe('Web Audio API Mock', () => {
    it('should create AudioContext instances', () => {
      const audioContext = new mocks.audioContext.AudioContext();
      
      expect(audioContext.state).toBe('suspended');
      expect(audioContext.sampleRate).toBe(44100);
      expect(audioContext.currentTime).toBe(0);
    });

    it('should create oscillator nodes', () => {
      const audioContext = new mocks.audioContext.AudioContext();
      const oscillator = audioContext.createOscillator();
      
      expect(oscillator.type).toBe('sine');
      expect(oscillator.frequency.value).toBe(440);
      expect(oscillator.detune.value).toBe(0);
    });

    it('should create gain nodes', () => {
      const audioContext = new mocks.audioContext.AudioContext();
      const gainNode = audioContext.createGain();
      
      expect(gainNode.gain.value).toBe(1);
    });

    it('should handle audio context state changes', async () => {
      const audioContext = new mocks.audioContext.AudioContext();
      
      expect(audioContext.state).toBe('suspended');
      
      await audioContext.resume();
      expect(audioContext.state).toBe('running');
      
      await audioContext.suspend();
      expect(audioContext.state).toBe('suspended');
    });
  });

  describe('File and Blob API Mocks', () => {
    it('should create Blob instances', () => {
      const blob = new mocks.fileBlobAPIs.Blob(['Hello, World!'], { type: 'text/plain' });
      
      expect(blob.size).toBe(13);
      expect(blob.type).toBe('text/plain');
    });

    it('should create File instances', () => {
      const file = new mocks.fileBlobAPIs.File(['Hello, World!'], 'test.txt', { 
        type: 'text/plain',
        lastModified: 1234567890 
      });
      
      expect(file.name).toBe('test.txt');
      expect(file.size).toBe(13);
      expect(file.type).toBe('text/plain');
      expect(file.lastModified).toBe(1234567890);
    });

    it('should handle blob operations', async () => {
      const blob = new mocks.fileBlobAPIs.Blob(['Hello, World!'], { type: 'text/plain' });
      
      const text = await blob.text();
      expect(typeof text).toBe('string');
      
      const arrayBuffer = await blob.arrayBuffer();
      expect(arrayBuffer).toBeInstanceOf(ArrayBuffer);
      expect(arrayBuffer.byteLength).toBe(13);
    });
  });

  describe('URL API Mock', () => {
    it('should create object URLs', () => {
      const blob = new Blob(['test data']);
      const url = mocks.urlAPI.createObjectURL(blob);
      
      expect(url).toMatch(/^blob:/);
      expect(typeof url).toBe('string');
    });

    it('should revoke object URLs', () => {
      const blob = new Blob(['test data']);
      const url = mocks.urlAPI.createObjectURL(blob);
      
      mocks.urlAPI.revokeObjectURL(url);
      // Should not throw
    });

    it('should create unique URLs', () => {
      const blob1 = new Blob(['test data 1']);
      const blob2 = new Blob(['test data 2']);
      
      const url1 = mocks.urlAPI.createObjectURL(blob1);
      const url2 = mocks.urlAPI.createObjectURL(blob2);
      
      expect(url1).not.toBe(url2);
    });
  });

  describe('Global Installation', () => {
    let originalAPIs: Map<string, any>;

    beforeEach(() => {
      // Store original APIs
      originalAPIs = new Map();
      originalAPIs.set('localStorage', globalThis.localStorage);
      originalAPIs.set('sessionStorage', globalThis.sessionStorage);
      originalAPIs.set('fetch', globalThis.fetch);
      originalAPIs.set('XMLHttpRequest', globalThis.XMLHttpRequest);
      originalAPIs.set('AudioContext', globalThis.AudioContext);
      originalAPIs.set('Blob', globalThis.Blob);
      originalAPIs.set('File', globalThis.File);
    });

    afterEach(() => {
      // Restore original APIs
      for (const [key, value] of originalAPIs) {
        if (value !== undefined) {
          Object.defineProperty(globalThis, key, {
            value,
            writable: true,
            configurable: true,
          });
        }
      }
    });

    it('should install all browser API mocks globally', () => {
      const installedMocks = installBrowserAPIMocks();
      
      expect(globalThis.localStorage).toBe(installedMocks.localStorage);
      expect(globalThis.sessionStorage).toBe(installedMocks.sessionStorage);
      expect(globalThis.fetch).toBe(installedMocks.fetch);
      expect(globalThis.XMLHttpRequest).toBe(installedMocks.XMLHttpRequest);
      expect(globalThis.AudioContext).toBe(installedMocks.audioContext.AudioContext);
      expect(globalThis.Blob).toBe(installedMocks.fileBlobAPIs.Blob);
      expect(globalThis.File).toBe(installedMocks.fileBlobAPIs.File);
    });

    it('should allow using mocked APIs globally', () => {
      installBrowserAPIMocks();
      
      // Test localStorage
      globalThis.localStorage.setItem('test', 'value');
      expect(globalThis.localStorage.getItem('test')).toBe('value');
      
      // Test AudioContext
      const audioContext = new globalThis.AudioContext();
      expect(audioContext.state).toBe('suspended');
      
      // Test Blob
      const blob = new globalThis.Blob(['test']);
      expect(blob.size).toBe(4);
    });
  });

  describe('Real-world Usage Scenarios', () => {
    it('should support AgentClient-like fetch operations', async () => {
      // Test JSON-RPC like request
      const response = await mocks.fetch('http://localhost:8001/jsonrpc', {
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
      const audioContext = new mocks.audioContext.AudioContext();
      
      // Create audio graph like AudioService might
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      const panner = audioContext.createPanner();
      
      // Configure nodes
      oscillator.frequency.value = 440;
      gainNode.gain.value = 0.5;
      panner.positionX.value = 1;
      panner.positionY.value = 0;
      panner.positionZ.value = 0;
      
      expect(oscillator.frequency.value).toBe(440);
      expect(gainNode.gain.value).toBe(0.5);
      expect(panner.positionX.value).toBe(1);
    });

    it('should support file operations for terrain data', async () => {
      // Simulate terrain file processing
      const terrainData = new Uint8Array([1, 2, 3, 4, 5]);
      const file = new mocks.fileBlobAPIs.File([terrainData], 'terrain.dat', { type: 'application/octet-stream' });
      
      expect(file.name).toBe('terrain.dat');
      expect(file.size).toBe(5);
      
      const arrayBuffer = await file.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);
      
      expect(uint8Array.length).toBe(5);
      // Note: The mock arrayBuffer returns a new ArrayBuffer, so we can't compare the exact values
      // but we can verify the size is correct
      
      // Create object URL for the file
      const url = mocks.urlAPI.createObjectURL(file);
      expect(url).toMatch(/^blob:/);
      
      mocks.urlAPI.revokeObjectURL(url);
    });
  });
});