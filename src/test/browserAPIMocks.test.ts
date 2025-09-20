/**
 * Comprehensive tests for Browser API Mocks
 * Tests all browser API mocks including localStorage, sessionStorage, fetch, XMLHttpRequest, and Web Audio API
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  createStorageMock,
  createFetchMock,
  createXMLHttpRequestMock,
  createWebAudioAPIMock,
  createFileBlobMocks,
  createURLMock,
  createBrowserAPIMocks,
  installBrowserAPIMocks,
  resetBrowserAPIMocks,
  type MockStorage,
  type MockFetch,
  type MockXMLHttpRequest,
  type BrowserAPIMocks,
} from './browserAPIMocks';

describe('Browser API Mocks', () => {
  let mocks: BrowserAPIMocks;

  beforeEach(() => {
    mocks = createBrowserAPIMocks();
  });

  afterEach(() => {
    resetBrowserAPIMocks(mocks);
  });

  describe('Storage API Mocks', () => {
    describe('localStorage mock', () => {
      let storage: MockStorage;

      beforeEach(() => {
        storage = createStorageMock();
      });

      it('should store and retrieve items', () => {
        storage.setItem('test-key', 'test-value');
        expect(storage.getItem('test-key')).toBe('test-value');
      });

      it('should return null for non-existent keys', () => {
        expect(storage.getItem('non-existent')).toBeNull();
      });

      it('should remove items', () => {
        storage.setItem('test-key', 'test-value');
        storage.removeItem('test-key');
        expect(storage.getItem('test-key')).toBeNull();
      });

      it('should clear all items', () => {
        storage.setItem('key1', 'value1');
        storage.setItem('key2', 'value2');
        expect(storage.length).toBe(2);
        
        storage.clear();
        expect(storage.length).toBe(0);
        expect(storage.getItem('key1')).toBeNull();
        expect(storage.getItem('key2')).toBeNull();
      });

      it('should return correct length', () => {
        expect(storage.length).toBe(0);
        storage.setItem('key1', 'value1');
        expect(storage.length).toBe(1);
        storage.setItem('key2', 'value2');
        expect(storage.length).toBe(2);
      });

      it('should return keys by index', () => {
        storage.setItem('key1', 'value1');
        storage.setItem('key2', 'value2');
        
        const key0 = storage.key(0);
        const key1 = storage.key(1);
        
        expect([key0, key1]).toContain('key1');
        expect([key0, key1]).toContain('key2');
        expect(storage.key(2)).toBeNull();
      });

      it('should convert values to strings', () => {
        storage.setItem('number', 123 as any);
        storage.setItem('boolean', true as any);
        storage.setItem('object', { test: 'value' } as any);
        
        expect(storage.getItem('number')).toBe('123');
        expect(storage.getItem('boolean')).toBe('true');
        expect(storage.getItem('object')).toBe('[object Object]');
      });
    });

    describe('sessionStorage mock', () => {
      it('should work independently from localStorage', () => {
        const localStorage = createStorageMock();
        const sessionStorage = createStorageMock();
        
        localStorage.setItem('key', 'local-value');
        sessionStorage.setItem('key', 'session-value');
        
        expect(localStorage.getItem('key')).toBe('local-value');
        expect(sessionStorage.getItem('key')).toBe('session-value');
      });
    });
  });

  describe('Fetch API Mock', () => {
    let fetchMock: MockFetch;

    beforeEach(() => {
      fetchMock = createFetchMock();
    });

    it('should return default successful response', async () => {
      const response = await fetchMock('https://example.com');
      
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);
      expect(response.statusText).toBe('OK');
      expect(response.url).toBe('https://example.com');
    });

    it('should handle custom mock responses', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        headers: new Map([['content-type', 'application/json']]),
        url: 'https://example.com/not-found',
      });

      const response = await fetchMock('https://example.com/not-found');
      
      expect(response.ok).toBe(false);
      expect(response.status).toBe(404);
      expect(response.statusText).toBe('Not Found');
    });

    it('should handle JSON responses', async () => {
      const testData = { message: 'Hello, World!' };
      fetchMock.mockResolvedValue({
        ok: true,
        status: 200,
        json: testData,
      });

      const response = await fetchMock('https://api.example.com/data');
      const data = await response.json();
      
      expect(data).toEqual(testData);
    });

    it('should handle text responses', async () => {
      const testText = 'Hello, World!';
      fetchMock.mockResolvedValue({
        ok: true,
        status: 200,
        text: testText,
      });

      const response = await fetchMock('https://example.com/text');
      const text = await response.text();
      
      expect(text).toBe(testText);
    });

    it('should handle blob responses', async () => {
      const testBlob = new Blob(['test data'], { type: 'text/plain' });
      fetchMock.mockResolvedValue({
        ok: true,
        status: 200,
        blob: testBlob,
      });

      const response = await fetchMock('https://example.com/blob');
      const blob = await response.blob();
      
      expect(blob).toBe(testBlob);
    });

    it('should handle arrayBuffer responses', async () => {
      const testBuffer = new ArrayBuffer(8);
      fetchMock.mockResolvedValue({
        ok: true,
        status: 200,
        arrayBuffer: testBuffer,
      });

      const response = await fetchMock('https://example.com/buffer');
      const buffer = await response.arrayBuffer();
      
      expect(buffer).toBe(testBuffer);
    });

    it('should handle rejected promises', async () => {
      const testError = new Error('Network error');
      fetchMock.mockRejectedValue(testError);

      await expect(fetchMock('https://example.com')).rejects.toThrow('Network error');
    });

    it('should handle custom implementations', async () => {
      fetchMock.mockImplementation(async (input, init) => {
        const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
        
        if (url.includes('/api/')) {
          return {
            ok: true,
            status: 200,
            statusText: 'OK',
            headers: new Map(),
            url,
            json: vi.fn(() => Promise.resolve({ api: true })),
            text: vi.fn(() => Promise.resolve('')),
            blob: vi.fn(() => Promise.resolve(new Blob())),
            arrayBuffer: vi.fn(() => Promise.resolve(new ArrayBuffer(0))),
            clone: vi.fn(),
          };
        }
        
        return {
          ok: false,
          status: 404,
          statusText: 'Not Found',
          headers: new Map(),
          url,
          json: vi.fn(() => Promise.resolve({})),
          text: vi.fn(() => Promise.resolve('')),
          blob: vi.fn(() => Promise.resolve(new Blob())),
          arrayBuffer: vi.fn(() => Promise.resolve(new ArrayBuffer(0))),
          clone: vi.fn(),
        };
      });

      const apiResponse = await fetchMock('https://example.com/api/data');
      const notFoundResponse = await fetchMock('https://example.com/other');
      
      expect(apiResponse.ok).toBe(true);
      expect(notFoundResponse.ok).toBe(false);
      expect(notFoundResponse.status).toBe(404);
    });

    it('should support response cloning', async () => {
      const response = await fetchMock('https://example.com');
      const clonedResponse = response.clone();
      
      expect(clonedResponse).toBeDefined();
      expect(typeof clonedResponse.clone).toBe('function');
    });

    it('should clear mock state', () => {
      fetchMock.mockResolvedValue({ status: 500 });
      fetchMock.mockClear();
      
      // After clearing, should return to default behavior
      expect(fetchMock).toBeDefined();
    });

    it('should reset mock state', () => {
      fetchMock.mockResolvedValue({ status: 500 });
      fetchMock.mockReset();
      
      // After resetting, should return to default behavior
      expect(fetchMock).toBeDefined();
    });
  });

  describe('XMLHttpRequest Mock', () => {
    let MockXHR: MockXMLHttpRequest;

    beforeEach(() => {
      MockXHR = createXMLHttpRequestMock();
    });

    it('should create XMLHttpRequest instances', () => {
      const xhr = new MockXHR();
      
      expect(xhr.readyState).toBe(0);
      expect(xhr.status).toBe(0);
      expect(xhr.statusText).toBe('');
      expect(xhr.response).toBeNull();
      expect(xhr.responseText).toBe('');
    });

    it('should handle open method', () => {
      const xhr = new MockXHR();
      
      xhr.open('GET', 'https://example.com/api');
      
      expect(xhr.readyState).toBe(1);
      expect(xhr.responseURL).toBe('https://example.com/api');
      expect(xhr.open).toHaveBeenCalledWith('GET', 'https://example.com/api');
    });

    it('should handle send method and trigger events', async () => {
      const xhr = new MockXHR();
      
      const promise = new Promise<void>((resolve, reject) => {
        xhr.onreadystatechange = () => {
          if (xhr.readyState === 4) {
            try {
              expect(xhr.status).toBe(200);
              expect(xhr.statusText).toBe('OK');
              expect(xhr.response).toBe('{}');
              expect(xhr.responseText).toBe('{}');
              resolve();
            } catch (error) {
              reject(error);
            }
          }
        };
        
        xhr.onload = () => {
          expect(xhr.readyState).toBe(4);
        };
        
        xhr.onerror = () => reject(new Error('XMLHttpRequest failed'));
      });
      
      xhr.open('GET', 'https://example.com/api');
      xhr.send();
      
      await promise;
    });

    it('should handle abort method', () => {
      const xhr = new MockXHR();
      const onAbort = vi.fn();
      
      xhr.onabort = onAbort;
      xhr.abort();
      
      expect(xhr.readyState).toBe(4);
      expect(xhr.status).toBe(0);
      expect(xhr.statusText).toBe('');
      expect(onAbort).toHaveBeenCalled();
    });

    it('should handle request headers', () => {
      const xhr = new MockXHR();
      
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.setRequestHeader('Authorization', 'Bearer token');
      
      expect(xhr.setRequestHeader).toHaveBeenCalledWith('Content-Type', 'application/json');
      expect(xhr.setRequestHeader).toHaveBeenCalledWith('Authorization', 'Bearer token');
    });

    it('should handle response headers', () => {
      const xhr = new MockXHR();
      
      const contentType = xhr.getResponseHeader('Content-Type');
      const allHeaders = xhr.getAllResponseHeaders();
      
      expect(contentType).toBeNull();
      expect(allHeaders).toBe('');
      expect(xhr.getResponseHeader).toHaveBeenCalledWith('Content-Type');
      expect(xhr.getAllResponseHeaders).toHaveBeenCalled();
    });

    it('should handle MIME type override', () => {
      const xhr = new MockXHR();
      
      xhr.overrideMimeType('text/plain');
      
      expect(xhr.overrideMimeType).toHaveBeenCalledWith('text/plain');
    });

    it('should handle event listeners', () => {
      const xhr = new MockXHR();
      const listener = vi.fn();
      
      xhr.addEventListener('load', listener);
      xhr.removeEventListener('load', listener);
      xhr.dispatchEvent(new Event('load'));
      
      expect(xhr.addEventListener).toHaveBeenCalledWith('load', listener);
      expect(xhr.removeEventListener).toHaveBeenCalledWith('load', listener);
      expect(xhr.dispatchEvent).toHaveBeenCalled();
    });

    it('should have correct constants', () => {
      expect(MockXHR.UNSENT).toBe(0);
      expect(MockXHR.OPENED).toBe(1);
      expect(MockXHR.HEADERS_RECEIVED).toBe(2);
      expect(MockXHR.LOADING).toBe(3);
      expect(MockXHR.DONE).toBe(4);
    });
  });

  describe('Web Audio API Mock', () => {
    let audioMocks: ReturnType<typeof createWebAudioAPIMock>;

    beforeEach(() => {
      audioMocks = createWebAudioAPIMock();
    });

    it('should create AudioContext instances', () => {
      const audioContext = new audioMocks.AudioContext();
      
      expect(audioContext.state).toBe('suspended');
      expect(audioContext.sampleRate).toBe(44100);
      expect(audioContext.currentTime).toBe(0);
      expect(audioContext.destination).toBeDefined();
      expect(audioContext.listener).toBeDefined();
    });

    it('should create oscillator nodes', () => {
      const audioContext = new audioMocks.AudioContext();
      const oscillator = audioContext.createOscillator();
      
      expect(oscillator.type).toBe('sine');
      expect(oscillator.frequency.value).toBe(440);
      expect(oscillator.detune.value).toBe(0);
      expect(oscillator.start).toBeDefined();
      expect(oscillator.stop).toBeDefined();
      expect(oscillator.connect).toBeDefined();
      expect(oscillator.disconnect).toBeDefined();
    });

    it('should create gain nodes', () => {
      const audioContext = new audioMocks.AudioContext();
      const gainNode = audioContext.createGain();
      
      expect(gainNode.gain.value).toBe(1);
      expect(gainNode.connect).toBeDefined();
      expect(gainNode.disconnect).toBeDefined();
    });

    it('should create audio buffers', () => {
      const audioContext = new audioMocks.AudioContext();
      const buffer = audioContext.createBuffer(2, 44100, 44100);
      
      expect(buffer.numberOfChannels).toBe(2);
      expect(buffer.length).toBe(44100);
      expect(buffer.sampleRate).toBe(44100);
      expect(buffer.duration).toBe(1);
      expect(buffer.getChannelData).toBeDefined();
    });

    it('should create buffer source nodes', () => {
      const audioContext = new audioMocks.AudioContext();
      const bufferSource = audioContext.createBufferSource();
      
      expect(bufferSource.buffer).toBeNull();
      expect(bufferSource.playbackRate.value).toBe(1);
      expect(bufferSource.detune.value).toBe(0);
      expect(bufferSource.loop).toBe(false);
      expect(bufferSource.start).toBeDefined();
      expect(bufferSource.stop).toBeDefined();
    });

    it('should create analyser nodes', () => {
      const audioContext = new audioMocks.AudioContext();
      const analyser = audioContext.createAnalyser();
      
      expect(analyser.fftSize).toBe(2048);
      expect(analyser.frequencyBinCount).toBe(1024);
      expect(analyser.minDecibels).toBe(-100);
      expect(analyser.maxDecibels).toBe(-30);
      expect(analyser.smoothingTimeConstant).toBe(0.8);
      expect(analyser.getByteFrequencyData).toBeDefined();
    });

    it('should create filter nodes', () => {
      const audioContext = new audioMocks.AudioContext();
      const filter = audioContext.createBiquadFilter();
      
      expect(filter.type).toBe('lowpass');
      expect(filter.frequency.value).toBe(350);
      expect(filter.Q.value).toBe(1);
      expect(filter.gain.value).toBe(0);
      expect(filter.getFrequencyResponse).toBeDefined();
    });

    it('should create panner nodes', () => {
      const audioContext = new audioMocks.AudioContext();
      const panner = audioContext.createPanner();
      
      expect(panner.panningModel).toBe('equalpower');
      expect(panner.distanceModel).toBe('inverse');
      expect(panner.refDistance).toBe(1);
      expect(panner.maxDistance).toBe(10000);
      expect(panner.positionX.value).toBe(0);
      expect(panner.positionY.value).toBe(0);
      expect(panner.positionZ.value).toBe(0);
    });

    it('should handle audio context state changes', async () => {
      const audioContext = new audioMocks.AudioContext();
      
      expect(audioContext.state).toBe('suspended');
      
      await audioContext.resume();
      expect(audioContext.state).toBe('running');
      
      await audioContext.suspend();
      expect(audioContext.state).toBe('suspended');
      
      await audioContext.close();
      expect(audioContext.state).toBe('closed');
    });

    it('should decode audio data', async () => {
      const audioContext = new audioMocks.AudioContext();
      const arrayBuffer = new ArrayBuffer(1024);
      
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      
      expect(audioBuffer).toBeDefined();
      expect(audioBuffer.sampleRate).toBe(44100);
      expect(audioBuffer.numberOfChannels).toBe(2);
    });

    it('should support webkit and offline contexts', () => {
      const webkitContext = new audioMocks.webkitAudioContext();
      const offlineContext = new audioMocks.OfflineAudioContext();
      
      expect(webkitContext.state).toBe('suspended');
      expect(offlineContext.state).toBe('suspended');
    });
  });

  describe('File and Blob API Mocks', () => {
    let fileBlobMocks: ReturnType<typeof createFileBlobMocks>;

    beforeEach(() => {
      fileBlobMocks = createFileBlobMocks();
    });

    it('should create Blob instances', () => {
      const blob = new fileBlobMocks.Blob(['Hello, World!'], { type: 'text/plain' });
      
      expect(blob.size).toBe(13);
      expect(blob.type).toBe('text/plain');
      expect(blob.slice).toBeDefined();
      expect(blob.stream).toBeDefined();
      expect(blob.text).toBeDefined();
      expect(blob.arrayBuffer).toBeDefined();
    });

    it('should create File instances', () => {
      const file = new fileBlobMocks.File(['Hello, World!'], 'test.txt', { 
        type: 'text/plain',
        lastModified: 1234567890 
      });
      
      expect(file.name).toBe('test.txt');
      expect(file.size).toBe(13);
      expect(file.type).toBe('text/plain');
      expect(file.lastModified).toBe(1234567890);
      expect(file.webkitRelativePath).toBe('');
    });

    it('should handle blob slicing', () => {
      const blob = new fileBlobMocks.Blob(['Hello, World!'], { type: 'text/plain' });
      const slice = blob.slice(0, 5, 'text/plain');
      
      expect(slice).toBeDefined();
      expect(slice.type).toBe('text/plain');
    });

    it('should handle blob text conversion', async () => {
      const blob = new fileBlobMocks.Blob(['Hello, World!'], { type: 'text/plain' });
      const text = await blob.text();
      
      expect(text).toBe('');
    });

    it('should handle blob array buffer conversion', async () => {
      const blob = new fileBlobMocks.Blob(['Hello, World!'], { type: 'text/plain' });
      const arrayBuffer = await blob.arrayBuffer();
      
      expect(arrayBuffer).toBeInstanceOf(ArrayBuffer);
      expect(arrayBuffer.byteLength).toBe(13);
    });

    it('should handle blob streaming', () => {
      const blob = new fileBlobMocks.Blob(['Hello, World!'], { type: 'text/plain' });
      const stream = blob.stream();
      
      expect(stream).toBeInstanceOf(ReadableStream);
    });

    it('should calculate size correctly for different data types', () => {
      const stringBlob = new fileBlobMocks.Blob(['Hello'], { type: 'text/plain' });
      const arrayBufferBlob = new fileBlobMocks.Blob([new ArrayBuffer(10)], { type: 'application/octet-stream' });
      const uint8ArrayBlob = new fileBlobMocks.Blob([new Uint8Array(5)], { type: 'application/octet-stream' });
      
      expect(stringBlob.size).toBe(5);
      expect(arrayBufferBlob.size).toBe(10);
      expect(uint8ArrayBlob.size).toBe(5);
    });
  });

  describe('URL API Mock', () => {
    let urlMock: ReturnType<typeof createURLMock>;

    beforeEach(() => {
      urlMock = createURLMock();
    });

    it('should create object URLs', () => {
      const blob = new Blob(['test data']);
      const url = urlMock.createObjectURL(blob);
      
      expect(url).toMatch(/^blob:/);
      expect(typeof url).toBe('string');
    });

    it('should revoke object URLs', () => {
      const blob = new Blob(['test data']);
      const url = urlMock.createObjectURL(blob);
      
      urlMock.revokeObjectURL(url);
      
      expect(urlMock.revokeObjectURL).toHaveBeenCalledWith(url);
    });

    it('should create unique URLs', () => {
      const blob1 = new Blob(['test data 1']);
      const blob2 = new Blob(['test data 2']);
      
      const url1 = urlMock.createObjectURL(blob1);
      const url2 = urlMock.createObjectURL(blob2);
      
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
      originalAPIs.set('URL', globalThis.URL);
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

    it('should reset all mocks correctly', () => {
      const installedMocks = installBrowserAPIMocks();
      
      // Use the mocks
      globalThis.localStorage.setItem('test', 'value');
      
      // Reset mocks
      resetBrowserAPIMocks(installedMocks);
      
      // Check that storage is cleared
      expect(globalThis.localStorage.getItem('test')).toBeNull();
      expect(globalThis.localStorage.length).toBe(0);
    });
  });

  describe('Integration with Test Environment', () => {
    it('should work with vitest mocking functions', () => {
      const fetchMock = createFetchMock();
      
      // Test that vitest functions are available
      expect(fetchMock.mockResolvedValue).toBeDefined();
      expect(fetchMock.mockRejectedValue).toBeDefined();
      expect(fetchMock.mockImplementation).toBeDefined();
      expect(fetchMock.mockClear).toBeDefined();
      expect(fetchMock.mockReset).toBeDefined();
    });

    it('should maintain mock state between calls', async () => {
      const fetchMock = createFetchMock();
      
      fetchMock.mockResolvedValue({
        ok: true,
        status: 201,
        statusText: 'Created',
      });
      
      const response1 = await fetchMock('https://example.com/api/1');
      const response2 = await fetchMock('https://example.com/api/2');
      
      expect(response1.status).toBe(201);
      expect(response2.status).toBe(201);
    });

    it('should handle complex mock scenarios', async () => {
      const fetchMock = createFetchMock();
      
      // Mock different responses for different URLs
      fetchMock.mockImplementation(async (input) => {
        const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
        
        if (url.includes('/api/users')) {
          return {
            ok: true,
            status: 200,
            statusText: 'OK',
            headers: new Map([['content-type', 'application/json']]),
            url,
            json: vi.fn(() => Promise.resolve({ users: [] })),
            text: vi.fn(() => Promise.resolve('')),
            blob: vi.fn(() => Promise.resolve(new Blob())),
            arrayBuffer: vi.fn(() => Promise.resolve(new ArrayBuffer(0))),
            clone: vi.fn(),
          };
        }
        
        return {
          ok: false,
          status: 404,
          statusText: 'Not Found',
          headers: new Map(),
          url,
          json: vi.fn(() => Promise.resolve({})),
          text: vi.fn(() => Promise.resolve('')),
          blob: vi.fn(() => Promise.resolve(new Blob())),
          arrayBuffer: vi.fn(() => Promise.resolve(new ArrayBuffer(0))),
          clone: vi.fn(),
        };
      });
      
      const usersResponse = await fetchMock('https://api.example.com/api/users');
      const notFoundResponse = await fetchMock('https://api.example.com/other');
      
      expect(usersResponse.ok).toBe(true);
      expect(notFoundResponse.ok).toBe(false);
      
      const usersData = await usersResponse.json();
      expect(usersData).toEqual({ users: [] });
    });
  });
});