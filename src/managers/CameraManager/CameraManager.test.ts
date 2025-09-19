/**
 * CameraManager Tests
 * Basic tests to verify camera functionality
 */

import * as THREE from 'three';
import { CameraManager } from './CameraManager';
import { CameraMode, InputState } from '../../models/CameraState';

// Mock Three.js camera for testing
const createMockCamera = (): THREE.PerspectiveCamera => {
  const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
  camera.position.set(0, 10, 20);
  return camera;
};

// Mock input state
const createMockInputState = (): InputState => ({
  mouse: {
    x: 0,
    y: 0,
    deltaX: 0,
    deltaY: 0,
    leftButton: false,
    rightButton: false,
    middleButton: false,
    wheel: 0
  },
  keyboard: {
    forward: false,
    backward: false,
    left: false,
    right: false,
    up: false,
    down: false,
    shift: false,
    ctrl: false,
    alt: false
  }
});

describe('CameraManager', () => {
  let cameraManager: CameraManager;
  let mockCamera: THREE.PerspectiveCamera;

  beforeEach(() => {
    mockCamera = createMockCamera();
    cameraManager = new CameraManager(mockCamera);
  });

  test('should initialize with default state', () => {
    const state = cameraManager.getCurrentState();
    expect(state.mode).toBe(CameraMode.FREEFLY);
    expect(state.fieldOfView).toBe(75);
    expect(state.position).toEqual([0, 10, 20]);
  });

  test('should change camera mode', () => {
    cameraManager.setViewMode(CameraMode.ORBITAL);
    const state = cameraManager.getCurrentState();
    expect(state.mode).toBe(CameraMode.ORBITAL);
  });

  test('should update camera state with input', () => {
    const initialState = cameraManager.getCurrentState();
    const inputState = createMockInputState();
    
    // Simulate forward movement
    inputState.keyboard.forward = true;
    
    const newState = cameraManager.updateCamera(initialState, inputState);
    expect(newState).toBeDefined();
    expect(newState.mode).toBe(CameraMode.FREEFLY);
  });

  test('should handle mouse rotation input', () => {
    const initialState = cameraManager.getCurrentState();
    const inputState = createMockInputState();
    
    // Simulate mouse rotation
    inputState.mouse.leftButton = true;
    inputState.mouse.deltaX = 0.1;
    inputState.mouse.deltaY = 0.1;
    
    const newState = cameraManager.updateCamera(initialState, inputState);
    expect(newState).toBeDefined();
  });

  test('should save and load presets', () => {
    const testState = cameraManager.getCurrentState();
    testState.position = [10, 20, 30];
    
    cameraManager.savePreset('test', testState);
    const presets = cameraManager.getPresets();
    
    expect(presets).toContain('test');
  });

  test('should handle flyToPosition', async () => {
    const promise = cameraManager.flyToPosition([5, 5, 5], 100);
    expect(promise).toBeInstanceOf(Promise);
    
    // For testing, we'll just verify the promise resolves
    await expect(promise).resolves.toBeUndefined();
  });
});

// Export for potential use in other tests
export { createMockCamera, createMockInputState };