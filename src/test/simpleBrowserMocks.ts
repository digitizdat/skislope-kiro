/**
 * Simple Browser API Mocks for Testing
 * Provides basic mocking without complex vitest integration
 */

// Simple Storage Mock
export function createSimpleStorageMock() {
  const storage = new Map<string, string>();
  
  return {
    getItem: (key: string) => storage.get(key) || null,
    setItem: (key: string, value: string) => {
      storage.set(key, String(value));
    },
    removeItem: (key: string) => {
      storage.delete(key);
    },
    clear: () => {
      storage.clear();
    },
    key: (index: number) => {
      const keys = Array.from(storage.keys());
      return keys[index] || null;
    },
    get length() {
      return storage.size;
    },
  };
}

// Simple Fetch Mock
export function createSimpleFetchMock() {
  let mockResponse = {
    ok: true,
    status: 200,
    statusText: 'OK',
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
    blob: () => Promise.resolve(new Blob()),
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
  };
  
  const fetchMock = async (input: RequestInfo | URL, init?: RequestInit) => {
    return { ...mockResponse };
  };
  
  fetchMock.setMockResponse = (response: Partial<typeof mockResponse>) => {
    mockResponse = { ...mockResponse, ...response };
  };
  
  return fetchMock;
}

// Simple XMLHttpRequest Mock
export function createSimpleXMLHttpRequestMock() {
  return function MockXMLHttpRequest(this: any) {
    this.readyState = 0;
    this.response = null;
    this.responseText = '';
    this.responseType = '';
    this.responseURL = '';
    this.status = 0;
    this.statusText = '';
    this.timeout = 0;
    this.upload = {};
    this.withCredentials = false;
    
    this.onreadystatechange = null;
    this.onload = null;
    this.onerror = null;
    this.onabort = null;
    this.ontimeout = null;
    this.onprogress = null;
    
    this.open = (method: string, url: string) => {
      this.readyState = 1;
      this.responseURL = url;
      if (this.onreadystatechange) {
        this.onreadystatechange();
      }
    };
    
    this.send = (body?: any) => {
      setTimeout(() => {
        this.readyState = 4;
        this.status = 200;
        this.statusText = 'OK';
        this.response = '{}';
        this.responseText = '{}';
        
        if (this.onreadystatechange) {
          this.onreadystatechange();
        }
        if (this.onload) {
          this.onload();
        }
      }, 0);
    };
    
    this.abort = () => {
      this.readyState = 4;
      this.status = 0;
      this.statusText = '';
      if (this.onabort) {
        this.onabort();
      }
    };
    
    this.setRequestHeader = () => {};
    this.getResponseHeader = () => null;
    this.getAllResponseHeaders = () => '';
    this.overrideMimeType = () => {};
    this.addEventListener = () => {};
    this.removeEventListener = () => {};
    this.dispatchEvent = () => {};
  };
}

// Simple Web Audio API Mock
export function createSimpleWebAudioMock() {
  const createMockAudioNode = () => ({
    connect: () => {},
    disconnect: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  });
  
  const MockAudioContext = function(this: any) {
    this.state = 'suspended';
    this.sampleRate = 44100;
    this.currentTime = 0;
    this.destination = createMockAudioNode();
    this.listener = {
      positionX: { value: 0 },
      positionY: { value: 0 },
      positionZ: { value: 0 },
      forwardX: { value: 0 },
      forwardY: { value: 0 },
      forwardZ: { value: -1 },
      upX: { value: 0 },
      upY: { value: 1 },
      upZ: { value: 0 },
    };
    
    this.createOscillator = () => ({
      ...createMockAudioNode(),
      type: 'sine',
      frequency: { value: 440 },
      detune: { value: 0 },
      start: () => {},
      stop: () => {},
    });
    
    this.createGain = () => ({
      ...createMockAudioNode(),
      gain: { value: 1 },
    });
    
    this.createBuffer = (numberOfChannels: number, length: number, sampleRate: number) => ({
      numberOfChannels,
      length,
      sampleRate,
      duration: length / sampleRate,
      getChannelData: () => new Float32Array(length),
      copyFromChannel: () => {},
      copyToChannel: () => {},
    });
    
    this.createBufferSource = () => ({
      ...createMockAudioNode(),
      buffer: null,
      playbackRate: { value: 1 },
      detune: { value: 0 },
      loop: false,
      loopStart: 0,
      loopEnd: 0,
      start: () => {},
      stop: () => {},
    });
    
    this.createAnalyser = () => ({
      ...createMockAudioNode(),
      fftSize: 2048,
      frequencyBinCount: 1024,
      minDecibels: -100,
      maxDecibels: -30,
      smoothingTimeConstant: 0.8,
      getByteFrequencyData: () => {},
      getByteTimeDomainData: () => {},
      getFloatFrequencyData: () => {},
      getFloatTimeDomainData: () => {},
    });
    
    this.decodeAudioData = () => Promise.resolve(this.createBuffer(2, 44100, 44100));
    
    this.suspend = () => {
      this.state = 'suspended';
      return Promise.resolve();
    };
    
    this.resume = () => {
      this.state = 'running';
      return Promise.resolve();
    };
    
    this.close = () => {
      this.state = 'closed';
      return Promise.resolve();
    };
  };
  
  return {
    AudioContext: MockAudioContext,
    webkitAudioContext: MockAudioContext,
    OfflineAudioContext: MockAudioContext,
  };
}

// Simple File and Blob Mocks
export function createSimpleFileBlobMocks() {
  const MockBlob = function(this: any, parts?: BlobPart[], options?: BlobPropertyBag) {
    this.size = 0;
    this.type = options?.type || '';
    
    if (parts) {
      this.size = parts.reduce((total, part) => {
        if (typeof part === 'string') {
          return total + part.length;
        } else if (part instanceof ArrayBuffer) {
          return total + part.byteLength;
        } else if (part instanceof Uint8Array) {
          return total + part.length;
        }
        return total;
      }, 0);
    }
    
    this.slice = () => new (MockBlob as any)([], { type: this.type });
    this.stream = () => new ReadableStream();
    this.text = () => Promise.resolve('');
    this.arrayBuffer = () => Promise.resolve(new ArrayBuffer(this.size));
  };
  
  const MockFile = function(this: any, parts: BlobPart[], name: string, options?: FilePropertyBag) {
    MockBlob.call(this, parts, options);
    this.name = name;
    this.lastModified = options?.lastModified || Date.now();
    this.webkitRelativePath = '';
  };
  
  MockFile.prototype = Object.create(MockBlob.prototype);
  MockFile.prototype.constructor = MockFile;
  
  return {
    Blob: MockBlob,
    File: MockFile,
  };
}

// Simple URL Mock
export function createSimpleURLMock() {
  const objectURLs = new Set<string>();
  
  return {
    createObjectURL: (object: any) => {
      const url = `blob:${Math.random().toString(36).substr(2, 9)}`;
      objectURLs.add(url);
      return url;
    },
    revokeObjectURL: (url: string) => {
      objectURLs.delete(url);
    },
  };
}

// Install all simple mocks
export function installSimpleBrowserMocks() {
  const mocks = {
    localStorage: createSimpleStorageMock(),
    sessionStorage: createSimpleStorageMock(),
    fetch: createSimpleFetchMock(),
    XMLHttpRequest: createSimpleXMLHttpRequestMock(),
    audioContext: createSimpleWebAudioMock(),
    fileBlobAPIs: createSimpleFileBlobMocks(),
    urlAPI: createSimpleURLMock(),
  };
  
  if (typeof globalThis !== 'undefined') {
    // Storage APIs
    Object.defineProperty(globalThis, 'localStorage', {
      value: mocks.localStorage,
      writable: true,
      configurable: true,
    });
    
    Object.defineProperty(globalThis, 'sessionStorage', {
      value: mocks.sessionStorage,
      writable: true,
      configurable: true,
    });
    
    // Network APIs
    Object.defineProperty(globalThis, 'fetch', {
      value: mocks.fetch,
      writable: true,
      configurable: true,
    });
    
    Object.defineProperty(globalThis, 'XMLHttpRequest', {
      value: mocks.XMLHttpRequest,
      writable: true,
      configurable: true,
    });
    
    // Web Audio API
    Object.defineProperty(globalThis, 'AudioContext', {
      value: mocks.audioContext.AudioContext,
      writable: true,
      configurable: true,
    });
    
    Object.defineProperty(globalThis, 'webkitAudioContext', {
      value: mocks.audioContext.webkitAudioContext,
      writable: true,
      configurable: true,
    });
    
    Object.defineProperty(globalThis, 'OfflineAudioContext', {
      value: mocks.audioContext.OfflineAudioContext,
      writable: true,
      configurable: true,
    });
    
    // File and Blob APIs
    Object.defineProperty(globalThis, 'Blob', {
      value: mocks.fileBlobAPIs.Blob,
      writable: true,
      configurable: true,
    });
    
    Object.defineProperty(globalThis, 'File', {
      value: mocks.fileBlobAPIs.File,
      writable: true,
      configurable: true,
    });
    
    // URL API
    if (globalThis.URL) {
      Object.assign(globalThis.URL, mocks.urlAPI);
    } else {
      Object.defineProperty(globalThis, 'URL', {
        value: mocks.urlAPI,
        writable: true,
        configurable: true,
      });
    }
  }
  
  return mocks;
}

// Reset all simple mocks
export function resetSimpleBrowserMocks(mocks: ReturnType<typeof installSimpleBrowserMocks>) {
  // Reset storage
  mocks.localStorage.clear();
  mocks.sessionStorage.clear();
  
  // Reset fetch mock response
  if ('setMockResponse' in mocks.fetch) {
    (mocks.fetch as any).setMockResponse({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: () => Promise.resolve({}),
      text: () => Promise.resolve(''),
      blob: () => Promise.resolve(new Blob()),
      arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    });
  }
}