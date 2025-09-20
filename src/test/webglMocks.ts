/**
 * WebGL and Three.js Test Mocking Infrastructure
 * Provides comprehensive WebGL context mocking and Three.js utilities for headless testing
 */

import { vi } from 'vitest';
import * as THREE from 'three';
import { createCanvas } from 'canvas';

/**
 * Enhanced WebGL Context Mock
 * Creates a comprehensive WebGL context mock that supports all Three.js operations
 */
export class WebGLContextMock {
  private canvas: HTMLCanvasElement;
  private context: WebGLRenderingContext;
  private programs: Map<WebGLProgram, { vertexShader: WebGLShader; fragmentShader: WebGLShader }> = new Map();
  private buffers: Set<WebGLBuffer> = new Set();
  private textures: Set<WebGLTexture> = new Set();
  private shaders: Set<WebGLShader> = new Set();
  private vertexArrays: Set<WebGLVertexArrayObject> = new Set();
  private currentProgram: WebGLProgram | null = null;
  private currentBuffer: WebGLBuffer | null = null;
  private currentTexture: WebGLTexture | null = null;
  private glState: Map<number, any> = new Map();

  constructor(width: number = 800, height: number = 600) {
    // Create canvas using node-canvas package
    const nodeCanvas = createCanvas(width, height);
    this.canvas = nodeCanvas as unknown as HTMLCanvasElement;
    
    // Create WebGL context first (before accessing canvas properties)
    this.context = this.createWebGLContext(width, height);
    
    // Add missing HTMLCanvasElement properties and methods
    Object.defineProperties(this.canvas, {
      // Override width and height to ensure they're accessible
      width: { value: width, writable: true, configurable: true },
      height: { value: height, writable: true, configurable: true },
      clientWidth: { value: width, writable: true },
      clientHeight: { value: height, writable: true },
      offsetWidth: { value: width, writable: true },
      offsetHeight: { value: height, writable: true },
      getBoundingClientRect: {
        value: () => ({
          left: 0,
          top: 0,
          width,
          height,
          right: width,
          bottom: height,
          x: 0,
          y: 0,
          toJSON: () => ({})
        })
      },
      addEventListener: { value: vi.fn() },
      removeEventListener: { value: vi.fn() },
      style: { value: {}, writable: true },
      parentElement: { value: null, writable: true },
      parentNode: { value: null, writable: true },
      ownerDocument: { value: document, writable: true },
      tagName: { value: 'CANVAS', writable: false },
      nodeName: { value: 'CANVAS', writable: false },
      nodeType: { value: 1, writable: false }, // Node.ELEMENT_NODE
      // Add DOM manipulation methods
      appendChild: { value: vi.fn() },
      removeChild: { value: vi.fn() },
      insertBefore: { value: vi.fn() },
      replaceChild: { value: vi.fn() },
      cloneNode: { value: vi.fn(() => this.canvas) },
      contains: { value: vi.fn(() => false) },
      querySelector: { value: vi.fn(() => null) },
      querySelectorAll: { value: vi.fn(() => []) },
      // Make it look like a real HTMLCanvasElement
      constructor: { value: HTMLCanvasElement, writable: true },
      // Add getContext method directly to the canvas
      getContext: {
        value: (contextType: string, _attributes?: any) => {
          if (contextType === 'webgl' || contextType === 'experimental-webgl') {
            return this.context;
          }
          return null;
        },
        writable: true
      }
    });

    // Ensure the canvas is recognized as an HTMLCanvasElement instance
    Object.setPrototypeOf(this.canvas, HTMLCanvasElement.prototype);
  }

  private createWebGLContext(width: number = 800, height: number = 600): WebGLRenderingContext {
    const mockContext = {
      // Canvas reference
      canvas: this.canvas,
      drawingBufferWidth: width,
      drawingBufferHeight: height,

      // State management
      enable: vi.fn((cap: number) => {
        this.glState.set(cap, true);
      }),
      disable: vi.fn((cap: number) => {
        this.glState.set(cap, false);
      }),
      isEnabled: vi.fn((cap: number) => {
        return this.glState.get(cap) || false;
      }),

      // Clear operations
      clear: vi.fn(),
      clearColor: vi.fn(),
      clearDepth: vi.fn(),
      clearStencil: vi.fn(),

      // Viewport and scissor
      viewport: vi.fn(),
      scissor: vi.fn(),

      // Shader operations
      createShader: vi.fn((type: number) => {
        const shader = { type, source: '', compiled: false } as WebGLShader;
        this.shaders.add(shader);
        return shader;
      }),
      shaderSource: vi.fn((shader: WebGLShader, source: string) => {
        (shader as any).source = source;
      }),
      compileShader: vi.fn((shader: WebGLShader) => {
        (shader as any).compiled = true;
      }),
      getShaderParameter: vi.fn((shader: WebGLShader, pname: number) => {
        if (pname === this.context.COMPILE_STATUS) {
          return (shader as any).compiled || true;
        }
        return true;
      }),
      getShaderInfoLog: vi.fn(() => ''),
      deleteShader: vi.fn((shader: WebGLShader) => {
        this.shaders.delete(shader);
      }),

      // Program operations
      createProgram: vi.fn(() => {
        const program = { linked: false } as WebGLProgram;
        return program;
      }),
      attachShader: vi.fn((program: WebGLProgram, shader: WebGLShader) => {
        if (!this.programs.has(program)) {
          this.programs.set(program, { vertexShader: null as any, fragmentShader: null as any });
        }
        const programData = this.programs.get(program)!;
        if ((shader as any).type === this.context.VERTEX_SHADER) {
          programData.vertexShader = shader;
        } else {
          programData.fragmentShader = shader;
        }
      }),
      linkProgram: vi.fn((program: WebGLProgram) => {
        (program as any).linked = true;
      }),
      getProgramParameter: vi.fn((program: WebGLProgram, pname: number) => {
        if (pname === this.context.LINK_STATUS) {
          return (program as any).linked || true;
        }
        return true;
      }),
      getProgramInfoLog: vi.fn(() => ''),
      useProgram: vi.fn((program: WebGLProgram | null) => {
        this.currentProgram = program;
      }),
      deleteProgram: vi.fn((program: WebGLProgram) => {
        this.programs.delete(program);
      }),

      // Buffer operations
      createBuffer: vi.fn(() => {
        const buffer = { data: null, target: null, usage: null } as WebGLBuffer;
        this.buffers.add(buffer);
        return buffer;
      }),
      bindBuffer: vi.fn((target: number, buffer: WebGLBuffer | null) => {
        this.currentBuffer = buffer;
        if (buffer) {
          (buffer as any).target = target;
        }
      }),
      bufferData: vi.fn((_target: number, data: ArrayBuffer | ArrayBufferView, usage: number) => {
        if (this.currentBuffer) {
          (this.currentBuffer as any).data = data;
          (this.currentBuffer as any).usage = usage;
        }
      }),
      bufferSubData: vi.fn(),
      deleteBuffer: vi.fn((buffer: WebGLBuffer) => {
        this.buffers.delete(buffer);
      }),

      // Vertex array operations (WebGL 2.0 compatibility)
      createVertexArray: vi.fn(() => {
        const vao = {} as WebGLVertexArrayObject;
        this.vertexArrays.add(vao);
        return vao;
      }),
      bindVertexArray: vi.fn(),
      deleteVertexArray: vi.fn((vao: WebGLVertexArrayObject) => {
        this.vertexArrays.delete(vao);
      }),

      // Texture operations
      activeTexture: vi.fn(),
      createTexture: vi.fn(() => {
        const texture = { 
          width: 0, 
          height: 0, 
          format: null, 
          type: null,
          data: null 
        } as WebGLTexture;
        this.textures.add(texture);
        return texture;
      }),
      bindTexture: vi.fn((_target: number, texture: WebGLTexture | null) => {
        this.currentTexture = texture;
      }),
      texImage2D: vi.fn((_target: number, _level: number, _internalformat: number, 
                        width: number, height: number, _border: number, 
                        format: number, type: number, pixels: ArrayBufferView | null) => {
        if (this.currentTexture) {
          (this.currentTexture as any).width = width;
          (this.currentTexture as any).height = height;
          (this.currentTexture as any).format = format;
          (this.currentTexture as any).type = type;
          (this.currentTexture as any).data = pixels;
        }
      }),
      texSubImage2D: vi.fn(),
      texParameteri: vi.fn(),
      texParameterf: vi.fn(),
      generateMipmap: vi.fn(),
      deleteTexture: vi.fn((texture: WebGLTexture) => {
        this.textures.delete(texture);
      }),

      // Attribute operations
      getAttribLocation: vi.fn((_program: WebGLProgram, name: string) => {
        // Return predictable attribute locations for testing
        const locations: Record<string, number> = {
          'position': 0,
          'normal': 1,
          'uv': 2,
          'color': 3
        };
        return locations[name] ?? Math.floor(Math.random() * 16);
      }),
      enableVertexAttribArray: vi.fn(),
      disableVertexAttribArray: vi.fn(),
      vertexAttribPointer: vi.fn(),
      vertexAttrib1f: vi.fn(),
      vertexAttrib2f: vi.fn(),
      vertexAttrib3f: vi.fn(),
      vertexAttrib4f: vi.fn(),

      // Uniform operations
      getUniformLocation: vi.fn((program: WebGLProgram, name: string) => {
        return { name, program } as WebGLUniformLocation;
      }),
      getActiveUniform: vi.fn((_program: WebGLProgram, index: number) => {
        return {
          name: `uniform_${index}`,
          size: 1,
          type: this.context.FLOAT,
        };
      }),
      getActiveAttrib: vi.fn((_program: WebGLProgram, index: number) => {
        return {
          name: `attribute_${index}`,
          size: 1,
          type: this.context.FLOAT_VEC3,
        };
      }),
      uniform1f: vi.fn(),
      uniform1i: vi.fn(),
      uniform2f: vi.fn(),
      uniform2i: vi.fn(),
      uniform3f: vi.fn(),
      uniform3i: vi.fn(),
      uniform4f: vi.fn(),
      uniform4i: vi.fn(),
      uniform1fv: vi.fn(),
      uniform1iv: vi.fn(),
      uniform2fv: vi.fn(),
      uniform2iv: vi.fn(),
      uniform3fv: vi.fn(),
      uniform3iv: vi.fn(),
      uniform4fv: vi.fn(),
      uniform4iv: vi.fn(),
      uniformMatrix2fv: vi.fn(),
      uniformMatrix3fv: vi.fn(),
      uniformMatrix4fv: vi.fn(),

      // Drawing operations
      drawArrays: vi.fn(),
      drawElements: vi.fn(),

      // Framebuffer operations
      createFramebuffer: vi.fn(() => ({})),
      bindFramebuffer: vi.fn(),
      framebufferTexture2D: vi.fn(),
      framebufferRenderbuffer: vi.fn(),
      checkFramebufferStatus: vi.fn(() => this.context.FRAMEBUFFER_COMPLETE),
      deleteFramebuffer: vi.fn(),

      // Renderbuffer operations
      createRenderbuffer: vi.fn(() => ({})),
      bindRenderbuffer: vi.fn(),
      renderbufferStorage: vi.fn(),
      deleteRenderbuffer: vi.fn(),

      // State queries
      getParameter: vi.fn((pname: number) => {
        const parameters: Record<number, any> = {
          [this.context.VERSION]: 'WebGL 1.0 (Mock)',
          [this.context.VENDOR]: 'Mock Vendor',
          [this.context.RENDERER]: 'Mock Renderer',
          [this.context.MAX_TEXTURE_SIZE]: 2048,
          [this.context.MAX_VERTEX_ATTRIBS]: 16,
          [this.context.MAX_VERTEX_UNIFORM_VECTORS]: 256,
          [this.context.MAX_FRAGMENT_UNIFORM_VECTORS]: 256,
          [this.context.MAX_VARYING_VECTORS]: 8,
          [this.context.MAX_COMBINED_TEXTURE_IMAGE_UNITS]: 32,
        };
        return parameters[pname] || 0;
      }),

      // Context attributes
      getContextAttributes: vi.fn(() => ({
        alpha: true,
        antialias: true,
        depth: true,
        desynchronized: false,
        failIfMajorPerformanceCaveat: false,
        powerPreference: 'default',
        premultipliedAlpha: true,
        preserveDrawingBuffer: false,
        stencil: false,
      })),

      // Extension support
      getExtension: vi.fn((name: string) => {
        // Mock common extensions that Three.js uses
        const extensions: Record<string, any> = {
          'OES_vertex_array_object': {
            createVertexArrayOES: (this.context as any).createVertexArray,
            bindVertexArrayOES: (this.context as any).bindVertexArray,
            deleteVertexArrayOES: (this.context as any).deleteVertexArray,
          },
          'WEBGL_lose_context': {
            loseContext: vi.fn(),
            restoreContext: vi.fn(),
          },
          'EXT_blend_minmax': {
            MIN_EXT: 0x8007,
            MAX_EXT: 0x8008,
          },
          'OES_standard_derivatives': {},
          'OES_element_index_uint': {},
          'WEBGL_depth_texture': {
            UNSIGNED_INT_24_8_WEBGL: 0x84FA,
          },
          'EXT_texture_filter_anisotropic': {
            TEXTURE_MAX_ANISOTROPY_EXT: 0x84FE,
            MAX_TEXTURE_MAX_ANISOTROPY_EXT: 0x84FF,
          },
          'WEBGL_compressed_texture_s3tc': {
            COMPRESSED_RGB_S3TC_DXT1_EXT: 0x83F0,
            COMPRESSED_RGBA_S3TC_DXT1_EXT: 0x83F1,
            COMPRESSED_RGBA_S3TC_DXT3_EXT: 0x83F2,
            COMPRESSED_RGBA_S3TC_DXT5_EXT: 0x83F3,
          },
          'WEBGL_compressed_texture_pvrtc': {
            COMPRESSED_RGB_PVRTC_4BPPV1_IMG: 0x8C00,
            COMPRESSED_RGB_PVRTC_2BPPV1_IMG: 0x8C01,
            COMPRESSED_RGBA_PVRTC_4BPPV1_IMG: 0x8C02,
            COMPRESSED_RGBA_PVRTC_2BPPV1_IMG: 0x8C03,
          },
          'WEBGL_compressed_texture_etc1': {
            COMPRESSED_RGB_ETC1_WEBGL: 0x8D64,
          },
          'EXT_disjoint_timer_query': {
            QUERY_COUNTER_BITS_EXT: 0x8864,
            CURRENT_QUERY_EXT: 0x8865,
            QUERY_RESULT_EXT: 0x8866,
            QUERY_RESULT_AVAILABLE_EXT: 0x8867,
            TIME_ELAPSED_EXT: 0x88BF,
            TIMESTAMP_EXT: 0x8E28,
            GPU_DISJOINT_EXT: 0x8FBB,
          },
        };
        return extensions[name] || null;
      }),
      getSupportedExtensions: vi.fn(() => [
        'OES_vertex_array_object',
        'WEBGL_lose_context',
        'EXT_blend_minmax',
        'OES_standard_derivatives',
        'OES_element_index_uint',
        'WEBGL_depth_texture',
        'EXT_texture_filter_anisotropic',
        'WEBGL_compressed_texture_s3tc',
        'WEBGL_compressed_texture_pvrtc',
        'WEBGL_compressed_texture_etc1',
        'EXT_disjoint_timer_query'
      ]),

      // Error handling
      getError: vi.fn(() => 0), // GL_NO_ERROR

      // Pixel operations
      readPixels: vi.fn(),
      pixelStorei: vi.fn(),

      // Depth and stencil
      depthFunc: vi.fn(),
      depthMask: vi.fn(),
      depthRange: vi.fn(),
      stencilFunc: vi.fn(),
      stencilMask: vi.fn(),
      stencilOp: vi.fn(),
      
      // Color operations
      colorMask: vi.fn(),

      // Blending
      blendFunc: vi.fn(),
      blendFuncSeparate: vi.fn(),
      blendEquation: vi.fn(),
      blendEquationSeparate: vi.fn(),
      blendColor: vi.fn(),

      // Culling
      cullFace: vi.fn(),
      frontFace: vi.fn(),

      // Polygon offset
      polygonOffset: vi.fn(),

      // Sample coverage
      sampleCoverage: vi.fn(),

      // Line width
      lineWidth: vi.fn(),

      // Hint
      hint: vi.fn(),

      // Validation
      isBuffer: vi.fn((buffer: WebGLBuffer) => this.buffers.has(buffer)),
      isTexture: vi.fn((texture: WebGLTexture) => this.textures.has(texture)),
      isProgram: vi.fn((program: WebGLProgram) => this.programs.has(program)),
      isShader: vi.fn((shader: WebGLShader) => this.shaders.has(shader)),
      isFramebuffer: vi.fn(() => true),
      isRenderbuffer: vi.fn(() => true),

      // WebGL constants
      DEPTH_BUFFER_BIT: 0x00000100,
      STENCIL_BUFFER_BIT: 0x00000400,
      COLOR_BUFFER_BIT: 0x00004000,
      POINTS: 0x0000,
      LINES: 0x0001,
      LINE_LOOP: 0x0002,
      LINE_STRIP: 0x0003,
      TRIANGLES: 0x0004,
      TRIANGLE_STRIP: 0x0005,
      TRIANGLE_FAN: 0x0006,
      ZERO: 0,
      ONE: 1,
      SRC_COLOR: 0x0300,
      ONE_MINUS_SRC_COLOR: 0x0301,
      SRC_ALPHA: 0x0302,
      ONE_MINUS_SRC_ALPHA: 0x0303,
      DST_ALPHA: 0x0304,
      ONE_MINUS_DST_ALPHA: 0x0305,
      DST_COLOR: 0x0306,
      ONE_MINUS_DST_COLOR: 0x0307,
      SRC_ALPHA_SATURATE: 0x0308,
      FUNC_ADD: 0x8006,
      BLEND_EQUATION: 0x8009,
      BLEND_EQUATION_RGB: 0x8009,
      BLEND_EQUATION_ALPHA: 0x883D,
      FUNC_SUBTRACT: 0x800A,
      FUNC_REVERSE_SUBTRACT: 0x800B,
      BLEND_DST_RGB: 0x80C8,
      BLEND_SRC_RGB: 0x80C9,
      BLEND_DST_ALPHA: 0x80CA,
      BLEND_SRC_ALPHA: 0x80CB,
      CONSTANT_COLOR: 0x8001,
      ONE_MINUS_CONSTANT_COLOR: 0x8002,
      CONSTANT_ALPHA: 0x8003,
      ONE_MINUS_CONSTANT_ALPHA: 0x8004,
      BLEND_COLOR: 0x8005,
      ARRAY_BUFFER: 0x8892,
      ELEMENT_ARRAY_BUFFER: 0x8893,
      ARRAY_BUFFER_BINDING: 0x8894,
      ELEMENT_ARRAY_BUFFER_BINDING: 0x8895,
      STREAM_DRAW: 0x88E0,
      STATIC_DRAW: 0x88E4,
      DYNAMIC_DRAW: 0x88E8,
      BUFFER_SIZE: 0x8764,
      BUFFER_USAGE: 0x8765,
      CURRENT_VERTEX_ATTRIB: 0x8626,
      FRONT: 0x0404,
      BACK: 0x0405,
      FRONT_AND_BACK: 0x0408,
      TEXTURE_2D: 0x0DE1,
      CULL_FACE: 0x0B44,
      BLEND: 0x0BE2,
      DITHER: 0x0BD0,
      STENCIL_TEST: 0x0B90,
      DEPTH_TEST: 0x0B71,
      SCISSOR_TEST: 0x0C11,
      POLYGON_OFFSET_FILL: 0x8037,
      SAMPLE_ALPHA_TO_COVERAGE: 0x809E,
      SAMPLE_COVERAGE: 0x80A0,
      NO_ERROR: 0,
      INVALID_ENUM: 0x0500,
      INVALID_VALUE: 0x0501,
      INVALID_OPERATION: 0x0502,
      OUT_OF_MEMORY: 0x0505,
      CW: 0x0900,
      CCW: 0x0901,
      LINE_WIDTH: 0x0B21,
      ALIASED_POINT_SIZE_RANGE: 0x846D,
      ALIASED_LINE_WIDTH_RANGE: 0x846E,
      CULL_FACE_MODE: 0x0B45,
      FRONT_FACE: 0x0B46,
      DEPTH_RANGE: 0x0B70,
      DEPTH_WRITEMASK: 0x0B72,
      DEPTH_CLEAR_VALUE: 0x0B73,
      DEPTH_FUNC: 0x0B74,
      STENCIL_CLEAR_VALUE: 0x0B91,
      STENCIL_FUNC: 0x0B92,
      STENCIL_FAIL: 0x0B94,
      STENCIL_PASS_DEPTH_FAIL: 0x0B95,
      STENCIL_PASS_DEPTH_PASS: 0x0B96,
      STENCIL_REF: 0x0B97,
      STENCIL_VALUE_MASK: 0x0B93,
      STENCIL_WRITEMASK: 0x0B98,
      STENCIL_BACK_FUNC: 0x8800,
      STENCIL_BACK_FAIL: 0x8801,
      STENCIL_BACK_PASS_DEPTH_FAIL: 0x8802,
      STENCIL_BACK_PASS_DEPTH_PASS: 0x8803,
      STENCIL_BACK_REF: 0x8CA3,
      STENCIL_BACK_VALUE_MASK: 0x8CA4,
      STENCIL_BACK_WRITEMASK: 0x8CA5,
      VIEWPORT: 0x0BA2,
      SCISSOR_BOX: 0x0C10,
      COLOR_CLEAR_VALUE: 0x0C22,
      COLOR_WRITEMASK: 0x0C23,
      UNPACK_ALIGNMENT: 0x0CF5,
      PACK_ALIGNMENT: 0x0D05,
      MAX_TEXTURE_SIZE: 0x0D33,
      MAX_VIEWPORT_DIMS: 0x0D3A,
      SUBPIXEL_BITS: 0x0D50,
      RED_BITS: 0x0D52,
      GREEN_BITS: 0x0D53,
      BLUE_BITS: 0x0D54,
      ALPHA_BITS: 0x0D55,
      DEPTH_BITS: 0x0D56,
      STENCIL_BITS: 0x0D57,
      POLYGON_OFFSET_UNITS: 0x2A00,
      POLYGON_OFFSET_FACTOR: 0x8038,
      TEXTURE_BINDING_2D: 0x8069,
      SAMPLE_BUFFERS: 0x80A8,
      SAMPLES: 0x80A9,
      SAMPLE_COVERAGE_VALUE: 0x80AA,
      SAMPLE_COVERAGE_INVERT: 0x80AB,
      NUM_COMPRESSED_TEXTURE_FORMATS: 0x86A2,
      COMPRESSED_TEXTURE_FORMATS: 0x86A3,
      DONT_CARE: 0x1100,
      FASTEST: 0x1101,
      NICEST: 0x1102,
      GENERATE_MIPMAP_HINT: 0x8192,
      BYTE: 0x1400,
      UNSIGNED_BYTE: 0x1401,
      SHORT: 0x1402,
      UNSIGNED_SHORT: 0x1403,
      INT: 0x1404,
      UNSIGNED_INT: 0x1405,
      FLOAT: 0x1406,
      FIXED: 0x140C,
      DEPTH_COMPONENT: 0x1902,
      ALPHA: 0x1906,
      RGB: 0x1907,
      RGBA: 0x1908,
      LUMINANCE: 0x1909,
      LUMINANCE_ALPHA: 0x190A,
      UNSIGNED_SHORT_4_4_4_4: 0x8033,
      UNSIGNED_SHORT_5_5_5_1: 0x8034,
      UNSIGNED_SHORT_5_6_5: 0x8363,
      FRAGMENT_SHADER: 0x8B30,
      VERTEX_SHADER: 0x8B31,
      MAX_VERTEX_ATTRIBS: 0x8869,
      MAX_VERTEX_UNIFORM_VECTORS: 0x8DFB,
      MAX_VARYING_VECTORS: 0x8DFC,
      MAX_COMBINED_TEXTURE_IMAGE_UNITS: 0x8B4D,
      MAX_VERTEX_TEXTURE_IMAGE_UNITS: 0x8B4C,
      MAX_TEXTURE_IMAGE_UNITS: 0x8872,
      MAX_FRAGMENT_UNIFORM_VECTORS: 0x8DFD,
      SHADER_TYPE: 0x8B4F,
      DELETE_STATUS: 0x8B80,
      LINK_STATUS: 0x8B82,
      VALIDATE_STATUS: 0x8B83,
      ATTACHED_SHADERS: 0x8B85,
      ACTIVE_UNIFORMS: 0x8B86,
      ACTIVE_UNIFORM_MAX_LENGTH: 0x8B87,
      ACTIVE_ATTRIBUTES: 0x8B89,
      ACTIVE_ATTRIBUTE_MAX_LENGTH: 0x8B8A,
      SHADING_LANGUAGE_VERSION: 0x8B8C,
      CURRENT_PROGRAM: 0x8B8D,
      NEVER: 0x0200,
      LESS: 0x0201,
      EQUAL: 0x0202,
      LEQUAL: 0x0203,
      GREATER: 0x0204,
      NOTEQUAL: 0x0205,
      GEQUAL: 0x0206,
      ALWAYS: 0x0207,
      KEEP: 0x1E00,
      REPLACE: 0x1E01,
      INCR: 0x1E02,
      DECR: 0x1E03,
      INVERT: 0x150A,
      INCR_WRAP: 0x8507,
      DECR_WRAP: 0x8508,
      VENDOR: 0x1F00,
      RENDERER: 0x1F01,
      VERSION: 0x1F02,
      EXTENSIONS: 0x1F03,
      NEAREST: 0x2600,
      LINEAR: 0x2601,
      NEAREST_MIPMAP_NEAREST: 0x2700,
      LINEAR_MIPMAP_NEAREST: 0x2701,
      NEAREST_MIPMAP_LINEAR: 0x2702,
      LINEAR_MIPMAP_LINEAR: 0x2703,
      TEXTURE_MAG_FILTER: 0x2800,
      TEXTURE_MIN_FILTER: 0x2801,
      TEXTURE_WRAP_S: 0x2802,
      TEXTURE_WRAP_T: 0x2803,
      TEXTURE: 0x1702,
      TEXTURE_CUBE_MAP: 0x8513,
      TEXTURE_BINDING_CUBE_MAP: 0x8514,
      TEXTURE_CUBE_MAP_POSITIVE_X: 0x8515,
      TEXTURE_CUBE_MAP_NEGATIVE_X: 0x8516,
      TEXTURE_CUBE_MAP_POSITIVE_Y: 0x8517,
      TEXTURE_CUBE_MAP_NEGATIVE_Y: 0x8518,
      TEXTURE_CUBE_MAP_POSITIVE_Z: 0x8519,
      TEXTURE_CUBE_MAP_NEGATIVE_Z: 0x851A,
      MAX_CUBE_MAP_TEXTURE_SIZE: 0x851C,
      TEXTURE0: 0x84C0,
      TEXTURE1: 0x84C1,
      TEXTURE2: 0x84C2,
      TEXTURE3: 0x84C3,
      TEXTURE4: 0x84C4,
      TEXTURE5: 0x84C5,
      TEXTURE6: 0x84C6,
      TEXTURE7: 0x84C7,
      TEXTURE8: 0x84C8,
      TEXTURE9: 0x84C9,
      TEXTURE10: 0x84CA,
      TEXTURE11: 0x84CB,
      TEXTURE12: 0x84CC,
      TEXTURE13: 0x84CD,
      TEXTURE14: 0x84CE,
      TEXTURE15: 0x84CF,
      TEXTURE16: 0x84D0,
      TEXTURE17: 0x84D1,
      TEXTURE18: 0x84D2,
      TEXTURE19: 0x84D3,
      TEXTURE20: 0x84D4,
      TEXTURE21: 0x84D5,
      TEXTURE22: 0x84D6,
      TEXTURE23: 0x84D7,
      TEXTURE24: 0x84D8,
      TEXTURE25: 0x84D9,
      TEXTURE26: 0x84DA,
      TEXTURE27: 0x84DB,
      TEXTURE28: 0x84DC,
      TEXTURE29: 0x84DD,
      TEXTURE30: 0x84DE,
      TEXTURE31: 0x84DF,
      ACTIVE_TEXTURE: 0x84E0,
      REPEAT: 0x2901,
      CLAMP_TO_EDGE: 0x812F,
      MIRRORED_REPEAT: 0x8370,
      FLOAT_VEC2: 0x8B50,
      FLOAT_VEC3: 0x8B51,
      FLOAT_VEC4: 0x8B52,
      INT_VEC2: 0x8B53,
      INT_VEC3: 0x8B54,
      INT_VEC4: 0x8B55,
      BOOL: 0x8B56,
      BOOL_VEC2: 0x8B57,
      BOOL_VEC3: 0x8B58,
      BOOL_VEC4: 0x8B59,
      FLOAT_MAT2: 0x8B5A,
      FLOAT_MAT3: 0x8B5B,
      FLOAT_MAT4: 0x8B5C,
      SAMPLER_2D: 0x8B5E,
      SAMPLER_CUBE: 0x8B60,
      VERTEX_ATTRIB_ARRAY_ENABLED: 0x8622,
      VERTEX_ATTRIB_ARRAY_SIZE: 0x8623,
      VERTEX_ATTRIB_ARRAY_STRIDE: 0x8624,
      VERTEX_ATTRIB_ARRAY_TYPE: 0x8625,
      VERTEX_ATTRIB_ARRAY_NORMALIZED: 0x886A,
      VERTEX_ATTRIB_ARRAY_POINTER: 0x8645,
      VERTEX_ATTRIB_ARRAY_BUFFER_BINDING: 0x889F,
      IMPLEMENTATION_COLOR_READ_TYPE: 0x8B9A,
      IMPLEMENTATION_COLOR_READ_FORMAT: 0x8B9B,
      COMPILE_STATUS: 0x8B81,
      INFO_LOG_LENGTH: 0x8B84,
      SHADER_SOURCE_LENGTH: 0x8B88,
      SHADER_COMPILER: 0x8DFA,
      SHADER_BINARY_FORMATS: 0x8DF8,
      NUM_SHADER_BINARY_FORMATS: 0x8DF9,
      LOW_FLOAT: 0x8DF0,
      MEDIUM_FLOAT: 0x8DF1,
      HIGH_FLOAT: 0x8DF2,
      LOW_INT: 0x8DF3,
      MEDIUM_INT: 0x8DF4,
      HIGH_INT: 0x8DF5,
      FRAMEBUFFER: 0x8D40,
      RENDERBUFFER: 0x8D41,
      RGBA4: 0x8056,
      RGB5_A1: 0x8057,
      RGB565: 0x8D62,
      DEPTH_COMPONENT16: 0x81A5,
      STENCIL_INDEX8: 0x8D48,
      RENDERBUFFER_WIDTH: 0x8D42,
      RENDERBUFFER_HEIGHT: 0x8D43,
      RENDERBUFFER_INTERNAL_FORMAT: 0x8D44,
      RENDERBUFFER_RED_SIZE: 0x8D50,
      RENDERBUFFER_GREEN_SIZE: 0x8D51,
      RENDERBUFFER_BLUE_SIZE: 0x8D52,
      RENDERBUFFER_ALPHA_SIZE: 0x8D53,
      RENDERBUFFER_DEPTH_SIZE: 0x8D54,
      RENDERBUFFER_STENCIL_SIZE: 0x8D55,
      FRAMEBUFFER_ATTACHMENT_OBJECT_TYPE: 0x8CD0,
      FRAMEBUFFER_ATTACHMENT_OBJECT_NAME: 0x8CD1,
      FRAMEBUFFER_ATTACHMENT_TEXTURE_LEVEL: 0x8CD2,
      FRAMEBUFFER_ATTACHMENT_TEXTURE_CUBE_MAP_FACE: 0x8CD3,
      COLOR_ATTACHMENT0: 0x8CE0,
      DEPTH_ATTACHMENT: 0x8D00,
      STENCIL_ATTACHMENT: 0x8D20,
      NONE: 0,
      FRAMEBUFFER_COMPLETE: 0x8CD5,
      FRAMEBUFFER_INCOMPLETE_ATTACHMENT: 0x8CD6,
      FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT: 0x8CD7,
      FRAMEBUFFER_INCOMPLETE_DIMENSIONS: 0x8CD9,
      FRAMEBUFFER_UNSUPPORTED: 0x8CDD,
      FRAMEBUFFER_BINDING: 0x8CA6,
      RENDERBUFFER_BINDING: 0x8CA7,
      MAX_RENDERBUFFER_SIZE: 0x84E8,
      INVALID_FRAMEBUFFER_OPERATION: 0x0506,
    } as unknown as WebGLRenderingContext;

    return mockContext;
  }

  public getContext(): WebGLRenderingContext {
    return this.context;
  }

  public getCanvas(): HTMLCanvasElement {
    return this.canvas;
  }

  public reset(): void {
    // Clear all mock call history
    Object.values(this.context).forEach(method => {
      if (typeof method === 'function' && 'mockClear' in method) {
        (method as any).mockClear();
      }
    });

    // Reset internal state
    this.programs.clear();
    this.buffers.clear();
    this.textures.clear();
    this.shaders.clear();
    this.vertexArrays.clear();
    this.currentProgram = null;
    this.currentBuffer = null;
    this.currentTexture = null;
    this.glState.clear();
  }

  public getState(): any {
    return {
      programs: this.programs.size,
      buffers: this.buffers.size,
      textures: this.textures.size,
      shaders: this.shaders.size,
      vertexArrays: this.vertexArrays.size,
      currentProgram: this.currentProgram,
      currentBuffer: this.currentBuffer,
      currentTexture: this.currentTexture,
      glState: Object.fromEntries(this.glState)
    };
  }
}

/**
 * Three.js Terrain Rendering Test Utilities
 * Provides specialized mocking for terrain rendering operations
 */
export class ThreeJSTerrainMocks {
  private webglMock: WebGLContextMock;

  constructor(webglMock: WebGLContextMock) {
    this.webglMock = webglMock;
  }

  /**
   * Create a mock Three.js renderer with terrain-specific capabilities
   */
  public createTerrainRenderer(): THREE.WebGLRenderer {
    const canvas = this.webglMock.getCanvas();
    const context = this.webglMock.getContext();

    const mockRenderer = {
      domElement: canvas,
      context,
      
      // Renderer capabilities
      capabilities: {
        isWebGL2: false,
        precision: 'highp',
        logarithmicDepthBuffer: false,
        maxTextures: 16,
        maxVertexTextures: 4,
        maxTextureSize: 2048,
        maxCubemapSize: 1024,
        maxAttributes: 16,
        maxVertexUniforms: 1024,
        maxVaryings: 8,
        maxFragmentUniforms: 1024,
        vertexTextures: true,
        floatFragmentTextures: true,
        floatVertexTextures: true,
      },

      // Rendering methods
      render: vi.fn((scene: THREE.Scene, camera: THREE.Camera) => {
        // Mock terrain-specific rendering operations
        this.mockTerrainRenderPass(scene, camera);
      }),
      
      setSize: vi.fn((width: number, height: number) => {
        // Update canvas dimensions
        Object.defineProperty(canvas, 'width', { value: width, writable: true, configurable: true });
        Object.defineProperty(canvas, 'height', { value: height, writable: true, configurable: true });
        Object.defineProperty(canvas, 'clientWidth', { value: width, writable: true, configurable: true });
        Object.defineProperty(canvas, 'clientHeight', { value: height, writable: true, configurable: true });
        
        // Update WebGL context dimensions
        (context as any).drawingBufferWidth = width;
        (context as any).drawingBufferHeight = height;
      }),
      
      setPixelRatio: vi.fn(),
      setClearColor: vi.fn(),
      clear: vi.fn(() => {
        context.clear(context.COLOR_BUFFER_BIT | context.DEPTH_BUFFER_BIT);
      }),

      // State management
      setViewport: vi.fn((x: number, y: number, width: number, height: number) => {
        context.viewport(x, y, width, height);
      }),
      setScissor: vi.fn(),
      setScissorTest: vi.fn(),

      // Shadow mapping
      shadowMap: {
        enabled: true,
        type: THREE.PCFShadowMap,
        autoUpdate: true,
        needsUpdate: false,
      },

      // Disposal
      dispose: vi.fn(() => {
        this.webglMock.reset();
      }),

      // Info
      info: {
        memory: {
          geometries: 0,
          textures: 0,
        },
        render: {
          frame: 0,
          calls: 0,
          triangles: 0,
          points: 0,
          lines: 0,
        },
        programs: [],
      },

      // Additional properties for terrain rendering
      outputColorSpace: THREE.SRGBColorSpace,
      toneMapping: THREE.ACESFilmicToneMapping,
      toneMappingExposure: 1.0,
    } as unknown as THREE.WebGLRenderer;

    return mockRenderer;
  }

  /**
   * Mock terrain-specific rendering operations
   */
  private mockTerrainRenderPass(scene: THREE.Scene, camera: THREE.Camera): void {
    // Mock the rendering pipeline for terrain
    const context = this.webglMock.getContext();
    
    // Clear buffers
    context.clear(context.COLOR_BUFFER_BIT | context.DEPTH_BUFFER_BIT);
    
    // Mock terrain mesh rendering
    scene.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        this.mockMeshRender(object, camera);
      }
    });
  }

  /**
   * Mock individual mesh rendering
   */
  private mockMeshRender(mesh: THREE.Mesh, _camera: THREE.Camera): void {
    const context = this.webglMock.getContext();
    const geometry = mesh.geometry;
    
    // Mock vertex buffer binding
    if (geometry.attributes.position) {
      const positionBuffer = context.createBuffer();
      context.bindBuffer(context.ARRAY_BUFFER, positionBuffer);
      context.bufferData(context.ARRAY_BUFFER, geometry.attributes.position.array, context.STATIC_DRAW);
    }
    
    // Mock normal buffer binding
    if (geometry.attributes.normal) {
      const normalBuffer = context.createBuffer();
      context.bindBuffer(context.ARRAY_BUFFER, normalBuffer);
      context.bufferData(context.ARRAY_BUFFER, geometry.attributes.normal.array, context.STATIC_DRAW);
    }
    
    // Mock UV buffer binding
    if (geometry.attributes.uv) {
      const uvBuffer = context.createBuffer();
      context.bindBuffer(context.ARRAY_BUFFER, uvBuffer);
      context.bufferData(context.ARRAY_BUFFER, geometry.attributes.uv.array, context.STATIC_DRAW);
    }
    
    // Mock index buffer binding
    if (geometry.index) {
      const indexBuffer = context.createBuffer();
      context.bindBuffer(context.ELEMENT_ARRAY_BUFFER, indexBuffer);
      context.bufferData(context.ELEMENT_ARRAY_BUFFER, geometry.index.array, context.STATIC_DRAW);
    }
    
    // Mock draw call
    if (geometry.index) {
      context.drawElements(context.TRIANGLES, geometry.index.count, context.UNSIGNED_SHORT, 0);
    } else {
      const positionAttribute = geometry.attributes.position;
      if (positionAttribute) {
        context.drawArrays(context.TRIANGLES, 0, positionAttribute.count);
      }
    }
  }

  /**
   * Create mock terrain geometry with realistic properties
   */
  public createMockTerrainGeometry(width: number = 32, height: number = 32): THREE.BufferGeometry {
    const geometry = new THREE.BufferGeometry();
    
    // Generate vertices for a terrain grid
    const vertices = new Float32Array(width * height * 3);
    const normals = new Float32Array(width * height * 3);
    const uvs = new Float32Array(width * height * 2);
    const indices = new Uint16Array((width - 1) * (height - 1) * 6);
    
    // Fill with mock terrain data
    let vertexIndex = 0;
    let uvIndex = 0;
    
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        // Position
        vertices[vertexIndex] = x - width / 2;
        vertices[vertexIndex + 1] = Math.sin(x * 0.1) * Math.cos(y * 0.1) * 2; // Mock elevation
        vertices[vertexIndex + 2] = y - height / 2;
        
        // Normal (pointing up for simplicity)
        normals[vertexIndex] = 0;
        normals[vertexIndex + 1] = 1;
        normals[vertexIndex + 2] = 0;
        
        // UV
        uvs[uvIndex] = x / (width - 1);
        uvs[uvIndex + 1] = y / (height - 1);
        
        vertexIndex += 3;
        uvIndex += 2;
      }
    }
    
    // Generate indices
    let indexIndex = 0;
    for (let y = 0; y < height - 1; y++) {
      for (let x = 0; x < width - 1; x++) {
        const a = y * width + x;
        const b = y * width + x + 1;
        const c = (y + 1) * width + x;
        const d = (y + 1) * width + x + 1;
        
        // First triangle
        indices[indexIndex] = a;
        indices[indexIndex + 1] = b;
        indices[indexIndex + 2] = c;
        
        // Second triangle
        indices[indexIndex + 3] = b;
        indices[indexIndex + 4] = d;
        indices[indexIndex + 5] = c;
        
        indexIndex += 6;
      }
    }
    
    geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
    geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
    geometry.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
    geometry.setIndex(new THREE.BufferAttribute(indices, 1));
    
    return geometry;
  }

  /**
   * Create mock terrain materials
   */
  public createMockTerrainMaterials(): THREE.Material[] {
    return [
      new THREE.MeshLambertMaterial({ color: 0xffffff, name: 'snow' }),
      new THREE.MeshLambertMaterial({ color: 0x8B4513, name: 'dirt' }),
      new THREE.MeshLambertMaterial({ color: 0x228B22, name: 'grass' }),
      new THREE.MeshLambertMaterial({ color: 0x696969, name: 'rock' }),
    ];
  }
}

/**
 * WebGL Test Environment Setup
 * Provides complete WebGL testing environment setup and teardown
 */
export class WebGLTestEnvironment {
  private static instance: WebGLTestEnvironment | null = null;
  private webglMock: WebGLContextMock;
  private terrainMocks: ThreeJSTerrainMocks;
  private originalCreateElement: typeof document.createElement;
  private originalGetContext: HTMLCanvasElement['getContext'];
  private originalAppendChild: typeof Element.prototype.appendChild;

  private constructor() {
    this.webglMock = new WebGLContextMock();
    this.terrainMocks = new ThreeJSTerrainMocks(this.webglMock);
    this.originalCreateElement = document.createElement;
    this.originalGetContext = HTMLCanvasElement.prototype.getContext;
    this.originalAppendChild = Element.prototype.appendChild;
  }

  public static getInstance(): WebGLTestEnvironment {
    if (!WebGLTestEnvironment.instance) {
      WebGLTestEnvironment.instance = new WebGLTestEnvironment();
    }
    return WebGLTestEnvironment.instance;
  }

  public setup(): void {
    const mockCanvas = this.webglMock.getCanvas();
    
    // Mock document.createElement for canvas
    document.createElement = vi.fn((tagName: string) => {
      if (tagName.toLowerCase() === 'canvas') {
        return mockCanvas;
      }
      return this.originalCreateElement.call(document, tagName);
    }) as any;

    // Mock HTMLCanvasElement.getContext - need to handle 'this' context properly
    const webglContext = this.webglMock.getContext();
    HTMLCanvasElement.prototype.getContext = vi.fn(function(this: HTMLCanvasElement, contextType: string, attributes?: any) {
      if (contextType === 'webgl' || contextType === 'experimental-webgl') {
        // Set the canvas property on the context to reference this canvas element
        (webglContext as any).canvas = this;
        return webglContext;
      }
      // For non-WebGL contexts, try to use original method if available
      if (typeof WebGLTestEnvironment.instance?.originalGetContext === 'function') {
        try {
          return WebGLTestEnvironment.instance.originalGetContext.call(this, contextType, attributes);
        } catch (e) {
          // If original method fails, return null for non-WebGL contexts
          return null;
        }
      }
      return null;
    }) as any;

    // Mock appendChild to ensure our canvas is properly tracked in the DOM
    const originalAppendChild = Element.prototype.appendChild;
    Element.prototype.appendChild = vi.fn(function<T extends Node>(this: Element, child: T): T {
      if (child === (mockCanvas as any)) {
        // Set parent relationship
        Object.defineProperty(mockCanvas, 'parentElement', { value: this, writable: true });
        Object.defineProperty(mockCanvas, 'parentNode', { value: this, writable: true });
        
        // Mock querySelector to find our canvas
        const originalQuerySelector = this.querySelector;
        this.querySelector = vi.fn((selector: string) => {
          if (selector === 'canvas' || selector === 'CANVAS') {
            return mockCanvas;
          }
          return originalQuerySelector?.call(this, selector) || null;
        }) as any;
      }
      return originalAppendChild.call(this, child) as T;
    }) as any;
  }

  public teardown(): void {
    // Restore original methods
    document.createElement = this.originalCreateElement;
    HTMLCanvasElement.prototype.getContext = this.originalGetContext;
    Element.prototype.appendChild = this.originalAppendChild;
    
    // Reset WebGL mock
    this.webglMock.reset();
  }

  public reset(): void {
    this.webglMock.reset();
  }

  public getWebGLMock(): WebGLContextMock {
    return this.webglMock;
  }

  public getTerrainMocks(): ThreeJSTerrainMocks {
    return this.terrainMocks;
  }

  public static reset(): void {
    if (WebGLTestEnvironment.instance) {
      WebGLTestEnvironment.instance.reset();
    }
  }

  public static teardownAll(): void {
    if (WebGLTestEnvironment.instance) {
      WebGLTestEnvironment.instance.teardown();
      WebGLTestEnvironment.instance = null;
    }
  }
}