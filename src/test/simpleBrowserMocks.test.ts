/**
 * Tests for simple browser API mocks
 */

import { describe, it, expect } from 'vitest';
import {
  createSimpleStorageMock,
  createSimpleFetchMock,
  createSimpleXMLHttpRequestMock,
  createSimpleWebAudioMock,
  createSimpleFileBlobMocks,
  createSimpleURLMock,
} from './simpleBrowserMocks';

describe('Simple Browser API Mocks', () => {
  describe('Storage Mock', () => {
    it('should work correctly', () => {
      const storage = createSimpleStorageMock();
      
      storage.setItem('test', 'value');
      expect(storage.getItem('test')).toBe('value');
      expect(storage.length).toBe(1);
      
      storage.removeItem('test');
      expect(storage.getItem('test')).toBeNull();
      expect(storage.length).toBe(0);
    });
  });

  describe('Fetch Mock', () => {
    it('should work correctly', async () => {
      const fetchMock = createSimpleFetchMock();
      
      const response = await fetchMock('https://example.com');
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);
    });
  });

  describe('XMLHttpRequest Mock', () => {
    it('should work correctly', () => {
      const MockXHR = createSimpleXMLHttpRequestMock();
      const xhr = new MockXHR();
      
      expect(xhr.readyState).toBe(0);
      expect(xhr.open).toBeDefined();
      expect(xhr.send).toBeDefined();
    });
  });

  describe('Web Audio Mock', () => {
    it('should work correctly', () => {
      const { AudioContext } = createSimpleWebAudioMock();
      const audioContext = new AudioContext();
      
      expect(audioContext.state).toBe('suspended');
      expect(audioContext.sampleRate).toBe(44100);
      expect(audioContext.createOscillator).toBeDefined();
    });
  });

  describe('File and Blob Mocks', () => {
    it('should work correctly', () => {
      const { Blob, File } = createSimpleFileBlobMocks();
      
      const blob = new Blob(['test'], { type: 'text/plain' });
      expect(blob.size).toBe(4);
      expect(blob.type).toBe('text/plain');
      
      const file = new File(['test'], 'test.txt');
      expect(file.name).toBe('test.txt');
      expect(file.size).toBe(4);
    });
  });

  describe('URL Mock', () => {
    it('should work correctly', () => {
      const urlMock = createSimpleURLMock();
      
      const url = urlMock.createObjectURL({});
      expect(url).toMatch(/^blob:/);
      
      urlMock.revokeObjectURL(url);
    });
  });

  describe('Global Installation', () => {
    it('should have mocks available globally', () => {
      expect(globalThis.localStorage).toBeDefined();
      expect(globalThis.sessionStorage).toBeDefined();
      expect(globalThis.fetch).toBeDefined();
      expect(globalThis.XMLHttpRequest).toBeDefined();
      expect(globalThis.AudioContext).toBeDefined();
      expect(globalThis.Blob).toBeDefined();
      expect(globalThis.File).toBeDefined();
    });
  });
});