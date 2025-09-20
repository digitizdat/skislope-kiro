/**
 * ThreeSetup Integration Tests
 * Tests to verify the complete Three.js setup with managers
 */

import { ThreeSetup } from './ThreeSetup';
import { CameraMode } from '../models/CameraState';

// Mock DOM element for testing
const createMockContainer = (): HTMLElement => {
  const container = document.createElement('div');
  container.style.width = '800px';
  container.style.height = '600px';
  
  // Mock clientWidth and clientHeight since JSDOM doesn't calculate layout
  Object.defineProperties(container, {
    clientWidth: { value: 800, writable: true },
    clientHeight: { value: 600, writable: true },
    offsetWidth: { value: 800, writable: true },
    offsetHeight: { value: 600, writable: true },
  });
  
  document.body.appendChild(container);
  return container;
};

describe('ThreeSetup Integration', () => {
  let container: HTMLElement;
  let threeSetup: ThreeSetup;

  beforeEach(() => {
    container = createMockContainer();
    threeSetup = new ThreeSetup(container);
  });

  afterEach(() => {
    if (threeSetup) {
      threeSetup.dispose();
    }
    if (container && container.parentNode) {
      container.parentNode.removeChild(container);
    }
  });

  test('should initialize Three.js scene and managers', () => {
    expect(threeSetup.getScene()).toBeDefined();
    expect(threeSetup.getCamera()).toBeDefined();
    expect(threeSetup.getRenderer()).toBeDefined();
    expect(threeSetup.getRenderManager()).toBeDefined();
    expect(threeSetup.getCameraManager()).toBeDefined();
    expect(threeSetup.getInputManager()).toBeDefined();
  });

  test('should have canvas element in container', () => {
    const canvas = container.querySelector('canvas');
    expect(canvas).toBeTruthy();
    expect(canvas?.width).toBeGreaterThan(0);
    expect(canvas?.height).toBeGreaterThan(0);
  });

  test('should change camera mode', () => {
    threeSetup.setCameraMode(CameraMode.ORBITAL);
    const cameraState = threeSetup.getCameraManager().getCurrentState();
    expect(cameraState.mode).toBe(CameraMode.ORBITAL);
  });

  test('should change time of day', () => {
    // This should not throw an error
    expect(() => {
      threeSetup.setTimeOfDay('dawn');
      threeSetup.setTimeOfDay('noon');
      threeSetup.setTimeOfDay('night');
    }).not.toThrow();
  });

  test('should handle flyToPosition', async () => {
    const promise = threeSetup.flyToPosition([10, 10, 10], 100);
    expect(promise).toBeInstanceOf(Promise);
    await expect(promise).resolves.toBeUndefined();
  });

  test('should start and stop animation', () => {
    expect(() => {
      threeSetup.startAnimation();
      threeSetup.stopAnimation();
    }).not.toThrow();
  });

  test('should dispose cleanly', () => {
    expect(() => {
      threeSetup.dispose();
    }).not.toThrow();
  });
});