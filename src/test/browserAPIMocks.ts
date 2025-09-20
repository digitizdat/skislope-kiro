/**
 * Comprehensive Browser API Mocks for Frontend Testing
 * Provides complete mocking for localStorage, sessionStorage, fetch, XMLHttpRequest, and Web Audio API
 */

import { vi } from 'vitest';

// Storage API Mock Implementation
export interface MockStorage {
  getItem: ReturnType<typeof vi.fn>;
  setItem: ReturnType<typeof vi.fn>;
  removeItem: ReturnType<typeof vi.fn>;
  clear: ReturnType<typeof vi.fn>;
  key: ReturnType<typeof vi.fn>;
  length: number;
}

export function createStorageMock(): MockStorage {
  const storage = new Map<string, string>();
  
  return {
    getItem: vi.fn((key: string) => storage.get(key) || null),
    setItem: vi.fn((key: string, value: string) => {
      storage.set(key, String(value));
    }),
    removeItem: vi.fn((key: string) => {
      storage.delete(key);
    }),
    clear: vi.fn(() => {
      storage.clear();
    }),
    key: vi.fn((index: number) => {
      const keys = Array.from(storage.keys());
      return keys[index] || null;
    }),
    get length() {
      return storage.size;
    },
  };
}

// Fetch API Mock Implementation
export interface MockResponse {
  ok: boolean;
  status: number;
  statusText: string;
  headers: Map<string, string>;
  url: string;
  json: () => Promise<any>;
  text: () => Promise<string>;
  blob: () => Promise<Blob>;
  arrayBuffer: () => Promise<ArrayBuffer>;
  clone: () => MockResponse;
}

export interface MockFetch {
  (input: RequestInfo | URL, init?: RequestInit): Promise<MockResponse>;
  mockResolvedValue: (response: Partial<MockResponse>) => void;
  mockRejectedValue: (error: Error) => void;
  mockImplementation: (fn: (input: RequestInfo | URL, init?: RequestInit) => Promise<MockResponse>) => void;
  mockClear: () => void;
  mockReset: () => void;
}

export function createFetchMock(): MockFetch {
  let defaultResponse: Partial<MockResponse> = {
    ok: true,
    status: 200,
    statusText: 'OK',
    headers: new Map(),
    url: '',
  };
  
  let customImplementation: ((input: RequestInfo | URL, init?: RequestInit) => Promise<MockResponse>) | null = null;
  let shouldReject: Error | null = null;
  
  const createResponse = (responseData: Partial<MockResponse>, url: string): MockResponse => ({
    ok: responseData.ok ?? true,
    status: responseData.status ?? 200,
    statusText: responseData.statusText ?? 'OK',
    headers: responseData.headers ?? new Map(),
    url: responseData.url ?? url,
    json: () => Promise.resolve(responseData.json ?? {}),
    text: () => Promise.resolve(responseData.text ?? ''),
    blob: () => Promise.resolve(responseData.blob ?? new Blob()),
    arrayBuffer: () => Promise.resolve(responseData.arrayBuffer ?? new ArrayBuffer(0)),
    clone: () => createResponse(responseData, url),
  });
  
  const fetchMock = async (input: RequestInfo | URL, init?: RequestInit): Promise<MockResponse> => {
    if (shouldReject) {
      throw shouldReject;
    }
    
    if (customImplementation) {
      return customImplementation(input, init);
    }
    
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    return createResponse(defaultResponse, url);
  };
  
  fetchMock.mockResolvedValue = (response: Partial<MockResponse>) => {
    defaultResponse = response;
    customImplementation = null;
    shouldReject = null;
  };
  
  fetchMock.mockRejectedValue = (error: Error) => {
    shouldReject = error;
    customImplementation = null;
  };
  
  fetchMock.mockImplementation = (fn: (input: RequestInfo | URL, init?: RequestInit) => Promise<MockResponse>) => {
    customImplementation = fn;
    shouldReject = null;
  };
  
  fetchMock.mockClear = () => {
    defaultResponse = {
      ok: true,
      status: 200,
      statusText: 'OK',
      headers: new Map(),
      url: '',
    };
    customImplementation = null;
    shouldReject = null;
  };
  
  fetchMock.mockReset = () => {
    defaultResponse = {
      ok: true,
      status: 200,
      statusText: 'OK',
      headers: new Map(),
      url: '',
    };
    customImplementation = null;
    shouldReject = null;
  };
  
  return fetchMock as MockFetch;
}

// XMLHttpRequest Mock Implementation
export interface MockXMLHttpRequest {
  new (): MockXMLHttpRequestInstance;
  UNSENT: number;
  OPENED: number;
  HEADERS_RECEIVED: number;
  LOADING: number;
  DONE: number;
}

export interface MockXMLHttpRequestInstance {
  readyState: number;
  response: any;
  responseText: string;
  responseType: XMLHttpRequestResponseType;
  responseURL: string;
  status: number;
  statusText: string;
  timeout: number;
  upload: XMLHttpRequestUpload;
  withCredentials: boolean;
  
  onreadystatechange: ((this: XMLHttpRequest, ev: Event) => any) | null;
  onload: ((this: XMLHttpRequest, ev: ProgressEvent) => any) | null;
  onerror: ((this: XMLHttpRequest, ev: ProgressEvent) => any) | null;
  onabort: ((this: XMLHttpRequest, ev: ProgressEvent) => any) | null;
  ontimeout: ((this: XMLHttpRequest, ev: ProgressEvent) => any) | null;
  onprogress: ((this: XMLHttpRequest, ev: ProgressEvent) => any) | null;
  
  open: ReturnType<typeof vi.fn>;
  send: ReturnType<typeof vi.fn>;
  abort: ReturnType<typeof vi.fn>;
  setRequestHeader: ReturnType<typeof vi.fn>;
  getResponseHeader: ReturnType<typeof vi.fn>;
  getAllResponseHeaders: ReturnType<typeof vi.fn>;
  overrideMimeType: ReturnType<typeof vi.fn>;
  
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
  dispatchEvent: ReturnType<typeof vi.fn>;
}

export function createXMLHttpRequestMock(): MockXMLHttpRequest {
  const MockXHR = function(this: MockXMLHttpRequestInstance) {
    this.readyState = 0;
    this.response = null;
    this.responseText = '';
    this.responseType = '';
    this.responseURL = '';
    this.status = 0;
    this.statusText = '';
    this.timeout = 0;
    this.upload = {} as XMLHttpRequestUpload;
    this.withCredentials = false;
    
    this.onreadystatechange = null;
    this.onload = null;
    this.onerror = null;
    this.onabort = null;
    this.ontimeout = null;
    this.onprogress = null;
    
    this.open = vi.fn((method: string, url: string) => {
      this.readyState = 1;
      this.responseURL = url;
      if (this.onreadystatechange) {
        this.onreadystatechange.call(this, new Event('readystatechange'));
      }
    });
    
    this.send = vi.fn((body?: Document | XMLHttpRequestBodyInit | null) => {
      // Simulate async request
      setTimeout(() => {
        this.readyState = 4;
        this.status = 200;
        this.statusText = 'OK';
        this.response = '{}';
        this.responseText = '{}';
        
        if (this.onreadystatechange) {
          this.onreadystatechange.call(this, new Event('readystatechange'));
        }
        if (this.onload) {
          this.onload.call(this, new ProgressEvent('load'));
        }
      }, 0);
    });
    
    this.abort = vi.fn(() => {
      this.readyState = 4;
      this.status = 0;
      this.statusText = '';
      if (this.onabort) {
        this.onabort.call(this, new ProgressEvent('abort'));
      }
    });
    
    this.setRequestHeader = vi.fn();
    this.getResponseHeader = vi.fn(() => null);
    this.getAllResponseHeaders = vi.fn(() => '');
    this.overrideMimeType = vi.fn();
    
    this.addEventListener = vi.fn();
    this.removeEventListener = vi.fn();
    this.dispatchEvent = vi.fn();
  } as any;
  
  MockXHR.UNSENT = 0;
  MockXHR.OPENED = 1;
  MockXHR.HEADERS_RECEIVED = 2;
  MockXHR.LOADING = 3;
  MockXHR.DONE = 4;
  
  return MockXHR;
}

// Web Audio API Mock Implementation
export interface MockAudioContext {
  state: AudioContextState;
  sampleRate: number;
  currentTime: number;
  destination: AudioDestinationNode;
  listener: AudioListener;
  
  createOscillator: ReturnType<typeof vi.fn>;
  createGain: ReturnType<typeof vi.fn>;
  createBuffer: ReturnType<typeof vi.fn>;
  createBufferSource: ReturnType<typeof vi.fn>;
  createAnalyser: ReturnType<typeof vi.fn>;
  createBiquadFilter: ReturnType<typeof vi.fn>;
  createConvolver: ReturnType<typeof vi.fn>;
  createDelay: ReturnType<typeof vi.fn>;
  createDynamicsCompressor: ReturnType<typeof vi.fn>;
  createPanner: ReturnType<typeof vi.fn>;
  createStereoPanner: ReturnType<typeof vi.fn>;
  createWaveShaper: ReturnType<typeof vi.fn>;
  
  decodeAudioData: ReturnType<typeof vi.fn>;
  suspend: ReturnType<typeof vi.fn>;
  resume: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;
}

export interface MockAudioNode {
  context: MockAudioContext;
  numberOfInputs: number;
  numberOfOutputs: number;
  channelCount: number;
  channelCountMode: ChannelCountMode;
  channelInterpretation: ChannelInterpretation;
  
  connect: ReturnType<typeof vi.fn>;
  disconnect: ReturnType<typeof vi.fn>;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
  dispatchEvent: ReturnType<typeof vi.fn>;
}

export function createWebAudioAPIMock() {
  const createMockAudioNode = (context: MockAudioContext): MockAudioNode => ({
    context,
    numberOfInputs: 1,
    numberOfOutputs: 1,
    channelCount: 2,
    channelCountMode: 'max',
    channelInterpretation: 'speakers',
    connect: vi.fn(),
    disconnect: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  });
  
  const createMockAudioBuffer = (sampleRate: number, length: number, numberOfChannels: number) => ({
    sampleRate,
    length,
    duration: length / sampleRate,
    numberOfChannels,
    getChannelData: vi.fn(() => new Float32Array(length)),
    copyFromChannel: vi.fn(),
    copyToChannel: vi.fn(),
  });
  
  const MockAudioContext = function(this: MockAudioContext) {
    this.state = 'suspended';
    this.sampleRate = 44100;
    this.currentTime = 0;
    this.destination = createMockAudioNode(this) as AudioDestinationNode;
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
    } as AudioListener;
    
    this.createOscillator = vi.fn(() => ({
      ...createMockAudioNode(this),
      type: 'sine',
      frequency: { value: 440 },
      detune: { value: 0 },
      start: vi.fn(),
      stop: vi.fn(),
    }));
    
    this.createGain = vi.fn(() => ({
      ...createMockAudioNode(this),
      gain: { value: 1 },
    }));
    
    this.createBuffer = vi.fn((numberOfChannels: number, length: number, sampleRate: number) =>
      createMockAudioBuffer(sampleRate, length, numberOfChannels)
    );
    
    this.createBufferSource = vi.fn(() => ({
      ...createMockAudioNode(this),
      buffer: null,
      playbackRate: { value: 1 },
      detune: { value: 0 },
      loop: false,
      loopStart: 0,
      loopEnd: 0,
      start: vi.fn(),
      stop: vi.fn(),
    }));
    
    this.createAnalyser = vi.fn(() => ({
      ...createMockAudioNode(this),
      fftSize: 2048,
      frequencyBinCount: 1024,
      minDecibels: -100,
      maxDecibels: -30,
      smoothingTimeConstant: 0.8,
      getByteFrequencyData: vi.fn(),
      getByteTimeDomainData: vi.fn(),
      getFloatFrequencyData: vi.fn(),
      getFloatTimeDomainData: vi.fn(),
    }));
    
    this.createBiquadFilter = vi.fn(() => ({
      ...createMockAudioNode(this),
      type: 'lowpass',
      frequency: { value: 350 },
      detune: { value: 0 },
      Q: { value: 1 },
      gain: { value: 0 },
      getFrequencyResponse: vi.fn(),
    }));
    
    this.createConvolver = vi.fn(() => ({
      ...createMockAudioNode(this),
      buffer: null,
      normalize: true,
    }));
    
    this.createDelay = vi.fn(() => ({
      ...createMockAudioNode(this),
      delayTime: { value: 0 },
    }));
    
    this.createDynamicsCompressor = vi.fn(() => ({
      ...createMockAudioNode(this),
      threshold: { value: -24 },
      knee: { value: 30 },
      ratio: { value: 12 },
      attack: { value: 0.003 },
      release: { value: 0.25 },
      reduction: 0,
    }));
    
    this.createPanner = vi.fn(() => ({
      ...createMockAudioNode(this),
      panningModel: 'equalpower',
      distanceModel: 'inverse',
      refDistance: 1,
      maxDistance: 10000,
      rolloffFactor: 1,
      coneInnerAngle: 360,
      coneOuterAngle: 360,
      coneOuterGain: 0,
      positionX: { value: 0 },
      positionY: { value: 0 },
      positionZ: { value: 0 },
      orientationX: { value: 1 },
      orientationY: { value: 0 },
      orientationZ: { value: 0 },
    }));
    
    this.createStereoPanner = vi.fn(() => ({
      ...createMockAudioNode(this),
      pan: { value: 0 },
    }));
    
    this.createWaveShaper = vi.fn(() => ({
      ...createMockAudioNode(this),
      curve: null,
      oversample: 'none',
    }));
    
    this.decodeAudioData = vi.fn(() => 
      Promise.resolve(createMockAudioBuffer(44100, 44100, 2))
    );
    
    this.suspend = vi.fn(() => {
      this.state = 'suspended';
      return Promise.resolve();
    });
    
    this.resume = vi.fn(() => {
      this.state = 'running';
      return Promise.resolve();
    });
    
    this.close = vi.fn(() => {
      this.state = 'closed';
      return Promise.resolve();
    });
  } as any;
  
  return {
    AudioContext: MockAudioContext,
    webkitAudioContext: MockAudioContext,
    OfflineAudioContext: MockAudioContext,
  };
}

// File and Blob API Mocks
export interface MockFile extends Blob {
  name: string;
  lastModified: number;
  webkitRelativePath: string;
}

export interface MockBlob {
  size: number;
  type: string;
  slice: ReturnType<typeof vi.fn>;
  stream: ReturnType<typeof vi.fn>;
  text: ReturnType<typeof vi.fn>;
  arrayBuffer: ReturnType<typeof vi.fn>;
}

export function createFileBlobMocks() {
  const MockBlob = function(this: MockBlob, parts?: BlobPart[], options?: BlobPropertyBag) {
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
    
    this.slice = vi.fn((start?: number, end?: number, contentType?: string) => 
      new (MockBlob as any)([], { type: contentType })
    );
    
    this.stream = vi.fn(() => new ReadableStream());
    this.text = vi.fn(() => Promise.resolve(''));
    this.arrayBuffer = vi.fn(() => Promise.resolve(new ArrayBuffer(this.size)));
  } as any;
  
  const MockFile = function(this: MockFile, parts: BlobPart[], name: string, options?: FilePropertyBag) {
    MockBlob.call(this, parts, options);
    this.name = name;
    this.lastModified = options?.lastModified || Date.now();
    this.webkitRelativePath = '';
  } as any;
  
  // Set up prototype chain
  MockFile.prototype = Object.create(MockBlob.prototype);
  MockFile.prototype.constructor = MockFile;
  
  return {
    Blob: MockBlob,
    File: MockFile,
  };
}

// URL API Mock
export function createURLMock() {
  const objectURLs = new Set<string>();
  
  return {
    createObjectURL: vi.fn((object: Blob | MediaSource) => {
      const url = `blob:${Math.random().toString(36).substr(2, 9)}`;
      objectURLs.add(url);
      return url;
    }),
    revokeObjectURL: vi.fn((url: string) => {
      objectURLs.delete(url);
    }),
  };
}

// Complete Browser API Mock Setup
export interface BrowserAPIMocks {
  localStorage: MockStorage;
  sessionStorage: MockStorage;
  fetch: MockFetch;
  XMLHttpRequest: MockXMLHttpRequest;
  audioContext: ReturnType<typeof createWebAudioAPIMock>;
  fileBlobAPIs: ReturnType<typeof createFileBlobMocks>;
  urlAPI: ReturnType<typeof createURLMock>;
}

export function createBrowserAPIMocks(): BrowserAPIMocks {
  return {
    localStorage: createStorageMock(),
    sessionStorage: createStorageMock(),
    fetch: createFetchMock(),
    XMLHttpRequest: createXMLHttpRequestMock(),
    audioContext: createWebAudioAPIMock(),
    fileBlobAPIs: createFileBlobMocks(),
    urlAPI: createURLMock(),
  };
}

// Install all browser API mocks
export function installBrowserAPIMocks(): BrowserAPIMocks {
  const mocks = createBrowserAPIMocks();
  
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
    Object.defineProperty(globalThis, 'URL', {
      value: {
        ...globalThis.URL,
        createObjectURL: mocks.urlAPI.createObjectURL,
        revokeObjectURL: mocks.urlAPI.revokeObjectURL,
      },
      writable: true,
      configurable: true,
    });
  }
  
  return mocks;
}

// Reset all browser API mocks
export function resetBrowserAPIMocks(mocks: BrowserAPIMocks): void {
  // Reset storage
  mocks.localStorage.clear();
  mocks.sessionStorage.clear();
  
  // Reset fetch
  mocks.fetch.mockClear();
  
  // Note: We don't need to reset vitest mocks recursively since we're using simpler implementations
}