/**
 * Camera state and control interfaces
 * Requirements: 6.1, 6.2 - Camera controls and multiple view modes
 */

/**
 * Camera modes for different viewing experiences
 */
export enum CameraMode {
  FREEFLY = 'freefly',
  ORBITAL = 'orbital',
  CINEMATIC = 'cinematic',
  FIRST_PERSON = 'firstPerson',
  AERIAL = 'aerial'
}

/**
 * Input control types
 */
export enum ControlType {
  MOUSE = 'mouse',
  KEYBOARD = 'keyboard',
  GAMEPAD = 'gamepad',
  TOUCH = 'touch'
}

/**
 * Camera state interface
 */
export interface CameraState {
  position: [number, number, number]; // Vector3 as array
  target: [number, number, number]; // Vector3 as array
  orientation: [number, number, number, number]; // Quaternion as array
  fieldOfView: number;
  mode: CameraMode;
  movementSpeed: number;
  rotationSpeed: number;
  zoomLevel: number;
  nearPlane: number;
  farPlane: number;
}

/**
 * Input state for camera controls
 */
export interface InputState {
  mouse: {
    x: number;
    y: number;
    deltaX: number;
    deltaY: number;
    leftButton: boolean;
    rightButton: boolean;
    middleButton: boolean;
    wheel: number;
  };
  keyboard: {
    forward: boolean;
    backward: boolean;
    left: boolean;
    right: boolean;
    up: boolean;
    down: boolean;
    shift: boolean;
    ctrl: boolean;
    alt: boolean;
  };
  gamepad?: {
    leftStick: [number, number];
    rightStick: [number, number];
    triggers: [number, number];
    buttons: boolean[];
  };
  touch?: {
    touches: Array<{
      id: number;
      x: number;
      y: number;
      deltaX: number;
      deltaY: number;
    }>;
    pinchScale: number;
    pinchDelta: number;
  };
}

/**
 * Camera movement constraints
 */
export interface CameraConstraints {
  minDistance: number;
  maxDistance: number;
  minPolarAngle: number;
  maxPolarAngle: number;
  minAzimuthAngle: number;
  maxAzimuthAngle: number;
  enablePan: boolean;
  enableZoom: boolean;
  enableRotate: boolean;
}

/**
 * Camera animation interface
 */
export interface CameraAnimation {
  id: string;
  startState: CameraState;
  endState: CameraState;
  duration: number;
  easing: 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out';
  onComplete?: () => void;
}

/**
 * Camera waypoint for cinematic paths
 */
export interface CameraWaypoint {
  position: [number, number, number];
  target: [number, number, number];
  duration: number;
  easing?: 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out';
}

/**
 * Camera manager interface
 */
export interface CameraManagerInterface {
  // State management
  updateCamera(state: CameraState, input: InputState): CameraState;
  getCurrentState(): CameraState;
  setState(state: Partial<CameraState>): void;
  
  // View modes
  setViewMode(mode: CameraMode): void;
  getViewMode(): CameraMode;
  
  // Movement and animation
  flyToPosition(position: [number, number, number], duration: number): Promise<void>;
  followPath(waypoints: CameraWaypoint[], speed: number): Promise<void>;
  lookAt(target: [number, number, number]): void;
  
  // Controls
  enableControls(type: ControlType): void;
  disableControls(type: ControlType): void;
  setConstraints(constraints: Partial<CameraConstraints>): void;
  
  // Presets
  savePreset(name: string, state: CameraState): void;
  loadPreset(name: string): Promise<void>;
  getPresets(): string[];
}

/**
 * Default camera states for different modes
 */
export const DEFAULT_CAMERA_STATES: Record<CameraMode, Partial<CameraState>> = {
  [CameraMode.FREEFLY]: {
    movementSpeed: 10,
    rotationSpeed: 1,
    fieldOfView: 75,
    nearPlane: 0.1,
    farPlane: 10000
  },
  [CameraMode.ORBITAL]: {
    movementSpeed: 5,
    rotationSpeed: 0.5,
    fieldOfView: 60,
    nearPlane: 1,
    farPlane: 5000
  },
  [CameraMode.CINEMATIC]: {
    movementSpeed: 2,
    rotationSpeed: 0.2,
    fieldOfView: 50,
    nearPlane: 0.5,
    farPlane: 8000
  },
  [CameraMode.FIRST_PERSON]: {
    movementSpeed: 8,
    rotationSpeed: 1.2,
    fieldOfView: 80,
    nearPlane: 0.1,
    farPlane: 3000
  },
  [CameraMode.AERIAL]: {
    movementSpeed: 15,
    rotationSpeed: 0.3,
    fieldOfView: 90,
    nearPlane: 10,
    farPlane: 15000
  }
};

/**
 * Default camera constraints
 */
export const DEFAULT_CAMERA_CONSTRAINTS: CameraConstraints = {
  minDistance: 1,
  maxDistance: 1000,
  minPolarAngle: 0,
  maxPolarAngle: Math.PI,
  minAzimuthAngle: -Infinity,
  maxAzimuthAngle: Infinity,
  enablePan: true,
  enableZoom: true,
  enableRotate: true
};