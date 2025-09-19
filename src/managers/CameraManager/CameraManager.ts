/**
 * CameraManager - Handles camera controls, view modes, and smooth transitions
 * Requirements: 6.1, 6.2 - Camera controls and multiple view modes
 */

import * as THREE from 'three';
import { 
  CameraState, 
  CameraMode, 
  InputState, 
  CameraManagerInterface,
  CameraConstraints,
  CameraAnimation,
  CameraWaypoint,
  DEFAULT_CAMERA_STATES,
  DEFAULT_CAMERA_CONSTRAINTS,
  ControlType
} from '../../models/CameraState';

export class CameraManager implements CameraManagerInterface {
  private camera: THREE.PerspectiveCamera;
  private currentState: CameraState;
  private constraints: CameraConstraints;
  private activeAnimations: Map<string, CameraAnimation>;
  private presets: Map<string, CameraState>;
  private enabledControls: Set<ControlType>;

  // Orbital camera specific properties
  private spherical: THREE.Spherical;
  private target: THREE.Vector3;
  private panOffset: THREE.Vector3;

  constructor(camera: THREE.PerspectiveCamera) {
    this.camera = camera;
    this.activeAnimations = new Map();
    this.presets = new Map();
    this.enabledControls = new Set([ControlType.MOUSE, ControlType.KEYBOARD]);

    // Initialize orbital camera properties
    this.spherical = new THREE.Spherical();
    this.target = new THREE.Vector3();
    this.panOffset = new THREE.Vector3();

    // Initialize default state
    this.currentState = {
      position: [0, 10, 20],
      target: [0, 0, 0],
      orientation: [0, 0, 0, 1],
      fieldOfView: 75,
      mode: CameraMode.FREEFLY,
      movementSpeed: 10,
      rotationSpeed: 1,
      zoomLevel: 1,
      nearPlane: 0.1,
      farPlane: 10000
    };

    this.constraints = { ...DEFAULT_CAMERA_CONSTRAINTS };

    // Apply initial state to camera
    this.applyCameraState();
  }

  public updateCamera(state: CameraState, input: InputState): CameraState {
    // Update current state based on input
    const newState = { ...state };

    switch (state.mode) {
      case CameraMode.FREEFLY:
        this.updateFreeflyCamera(newState, input);
        break;
      case CameraMode.ORBITAL:
        this.updateOrbitalCamera(newState, input);
        break;
      case CameraMode.CINEMATIC:
        this.updateCinematicCamera(newState, input);
        break;
      case CameraMode.FIRST_PERSON:
        this.updateFirstPersonCamera(newState, input);
        break;
      case CameraMode.AERIAL:
        this.updateAerialCamera(newState, input);
        break;
    }

    // Apply constraints
    this.applyConstraints(newState);

    // Update the actual Three.js camera
    this.currentState = newState;
    this.applyCameraState();

    return newState;
  }

  private updateFreeflyCamera(state: CameraState, input: InputState): void {
    const deltaTime = 0.016; // Assume 60fps
    const moveSpeed = state.movementSpeed * deltaTime;
    const rotSpeed = state.rotationSpeed * deltaTime;

    // Get camera vectors
    const camera = this.camera;
    const forward = new THREE.Vector3(0, 0, -1).applyQuaternion(camera.quaternion);
    const right = new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion);
    const up = new THREE.Vector3(0, 1, 0);

    // Handle keyboard movement
    if (input.keyboard.forward) {
      const pos = new THREE.Vector3(...state.position);
      pos.addScaledVector(forward, moveSpeed);
      state.position = [pos.x, pos.y, pos.z];
    }
    if (input.keyboard.backward) {
      const pos = new THREE.Vector3(...state.position);
      pos.addScaledVector(forward, -moveSpeed);
      state.position = [pos.x, pos.y, pos.z];
    }
    if (input.keyboard.left) {
      const pos = new THREE.Vector3(...state.position);
      pos.addScaledVector(right, -moveSpeed);
      state.position = [pos.x, pos.y, pos.z];
    }
    if (input.keyboard.right) {
      const pos = new THREE.Vector3(...state.position);
      pos.addScaledVector(right, moveSpeed);
      state.position = [pos.x, pos.y, pos.z];
    }
    if (input.keyboard.up) {
      const pos = new THREE.Vector3(...state.position);
      pos.addScaledVector(up, moveSpeed);
      state.position = [pos.x, pos.y, pos.z];
    }
    if (input.keyboard.down) {
      const pos = new THREE.Vector3(...state.position);
      pos.addScaledVector(up, -moveSpeed);
      state.position = [pos.x, pos.y, pos.z];
    }

    // Handle mouse rotation (when left button is pressed)
    if (input.mouse.leftButton && (input.mouse.deltaX !== 0 || input.mouse.deltaY !== 0)) {
      const euler = new THREE.Euler().setFromQuaternion(new THREE.Quaternion(...state.orientation));
      euler.y -= input.mouse.deltaX * rotSpeed;
      euler.x -= input.mouse.deltaY * rotSpeed;
      
      // Clamp vertical rotation
      euler.x = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, euler.x));
      
      const quat = new THREE.Quaternion().setFromEuler(euler);
      state.orientation = [quat.x, quat.y, quat.z, quat.w];
    }

    // Handle zoom with mouse wheel
    if (input.mouse.wheel !== 0) {
      state.fieldOfView = Math.max(10, Math.min(120, state.fieldOfView + input.mouse.wheel * 0.1));
    }
  }

  private updateOrbitalCamera(state: CameraState, input: InputState): void {
    const deltaTime = 0.016;
    const rotSpeed = state.rotationSpeed * deltaTime;
    const zoomSpeed = state.movementSpeed * deltaTime;

    // Update target from state
    this.target.set(...state.target);

    // Convert position to spherical coordinates relative to target
    const position = new THREE.Vector3(...state.position);
    const offset = position.clone().sub(this.target);
    this.spherical.setFromVector3(offset);

    // Handle mouse rotation (when left button is pressed)
    if (input.mouse.leftButton && (input.mouse.deltaX !== 0 || input.mouse.deltaY !== 0)) {
      this.spherical.theta -= input.mouse.deltaX * rotSpeed;
      this.spherical.phi += input.mouse.deltaY * rotSpeed;
      
      // Clamp phi to prevent flipping
      this.spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, this.spherical.phi));
    }

    // Handle zoom with mouse wheel
    if (input.mouse.wheel !== 0) {
      this.spherical.radius *= (1 + input.mouse.wheel * 0.001);
      this.spherical.radius = Math.max(this.constraints.minDistance, 
                                      Math.min(this.constraints.maxDistance, this.spherical.radius));
    }

    // Handle panning (when right button is pressed)
    if (input.mouse.rightButton && (input.mouse.deltaX !== 0 || input.mouse.deltaY !== 0)) {
      const camera = this.camera;
      const right = new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion);
      const up = new THREE.Vector3(0, 1, 0).applyQuaternion(camera.quaternion);
      
      this.panOffset.addScaledVector(right, -input.mouse.deltaX * zoomSpeed);
      this.panOffset.addScaledVector(up, input.mouse.deltaY * zoomSpeed);
      
      this.target.add(this.panOffset);
      this.panOffset.set(0, 0, 0);
    }

    // Update position from spherical coordinates
    offset.setFromSpherical(this.spherical);
    position.copy(this.target).add(offset);
    
    state.position = [position.x, position.y, position.z];
    state.target = [this.target.x, this.target.y, this.target.z];
  }

  private updateCinematicCamera(state: CameraState, input: InputState): void {
    // Cinematic mode has slower, smoother movements
    // Use freefly logic but with smoothing
    this.updateFreeflyCamera(state, input);
    
    // Apply smoothing to movements (this would be enhanced with proper interpolation)
    // For now, just reduce the movement speed
    state.movementSpeed = Math.min(state.movementSpeed, 5);
    state.rotationSpeed = Math.min(state.rotationSpeed, 0.5);
  }

  private updateFirstPersonCamera(state: CameraState, input: InputState): void {
    // First person is similar to freefly but with different constraints
    this.updateFreeflyCamera(state, input);
    
    // Constrain vertical movement in first person
    if (input.keyboard.up || input.keyboard.down) {
      // Limit vertical movement
      const pos = new THREE.Vector3(...state.position);
      pos.y = Math.max(0.5, Math.min(50, pos.y)); // Keep camera above ground
      state.position = [pos.x, pos.y, pos.z];
    }
  }

  private updateAerialCamera(state: CameraState, input: InputState): void {
    // Aerial view maintains higher altitude and different movement patterns
    this.updateFreeflyCamera(state, input);
    
    // Maintain minimum altitude for aerial view
    const pos = new THREE.Vector3(...state.position);
    pos.y = Math.max(20, pos.y); // Minimum altitude
    state.position = [pos.x, pos.y, pos.z];
    
    // Increase movement speed for aerial view
    state.movementSpeed = Math.max(state.movementSpeed, 15);
  }

  private applyConstraints(state: CameraState): void {
    // Apply field of view constraints
    state.fieldOfView = Math.max(10, Math.min(120, state.fieldOfView));
    
    // Apply movement speed constraints
    state.movementSpeed = Math.max(0.1, Math.min(100, state.movementSpeed));
    state.rotationSpeed = Math.max(0.1, Math.min(5, state.rotationSpeed));
  }

  private applyCameraState(): void {
    const state = this.currentState;
    
    // Update camera position
    this.camera.position.set(...state.position);
    
    // Update camera orientation
    this.camera.quaternion.set(...state.orientation);
    
    // Update camera properties
    this.camera.fov = state.fieldOfView;
    this.camera.near = state.nearPlane;
    this.camera.far = state.farPlane;
    this.camera.updateProjectionMatrix();
    
    // For orbital mode, make camera look at target
    if (state.mode === CameraMode.ORBITAL) {
      this.camera.lookAt(...state.target);
    }
  }

  public getCurrentState(): CameraState {
    return { ...this.currentState };
  }

  public setState(state: Partial<CameraState>): void {
    this.currentState = { ...this.currentState, ...state };
    this.applyCameraState();
  }

  public setViewMode(mode: CameraMode): void {
    const defaultState = DEFAULT_CAMERA_STATES[mode];
    this.currentState = { 
      ...this.currentState, 
      mode,
      ...defaultState 
    };
    this.applyCameraState();
  }

  public getViewMode(): CameraMode {
    return this.currentState.mode;
  }

  public async flyToPosition(position: [number, number, number], duration: number): Promise<void> {
    return new Promise((resolve) => {
      const startState = { ...this.currentState };
      const endState = { ...this.currentState, position };
      
      const animation: CameraAnimation = {
        id: 'flyTo_' + Date.now(),
        startState,
        endState,
        duration,
        easing: 'ease-out',
        onComplete: resolve
      };
      
      this.startAnimation(animation);
    });
  }

  public async followPath(waypoints: CameraWaypoint[], _speed: number): Promise<void> {
    for (const waypoint of waypoints) {
      await this.flyToPosition(waypoint.position, waypoint.duration);
      if (waypoint.target) {
        this.lookAt(waypoint.target);
      }
    }
  }

  public lookAt(target: [number, number, number]): void {
    this.currentState.target = target;
    this.camera.lookAt(...target);
  }

  public enableControls(type: ControlType): void {
    this.enabledControls.add(type);
  }

  public disableControls(type: ControlType): void {
    this.enabledControls.delete(type);
  }

  public setConstraints(constraints: Partial<CameraConstraints>): void {
    this.constraints = { ...this.constraints, ...constraints };
  }

  public savePreset(name: string, state: CameraState): void {
    this.presets.set(name, { ...state });
  }

  public async loadPreset(name: string): Promise<void> {
    const preset = this.presets.get(name);
    if (preset) {
      await this.flyToPosition(preset.position, 1000);
      this.setState(preset);
    }
  }

  public getPresets(): string[] {
    return Array.from(this.presets.keys());
  }

  private startAnimation(animation: CameraAnimation): void {
    this.activeAnimations.set(animation.id, animation);
    
    const startTime = Date.now();
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / animation.duration, 1);
      
      // Apply easing
      const easedProgress = this.applyEasing(progress, animation.easing);
      
      // Interpolate between start and end states
      const interpolatedState = this.interpolateStates(
        animation.startState, 
        animation.endState, 
        easedProgress
      );
      
      this.setState(interpolatedState);
      
      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        this.activeAnimations.delete(animation.id);
        if (animation.onComplete) {
          animation.onComplete();
        }
      }
    };
    
    animate();
  }

  private applyEasing(t: number, easing: string): number {
    switch (easing) {
      case 'ease-in':
        return t * t;
      case 'ease-out':
        return 1 - (1 - t) * (1 - t);
      case 'ease-in-out':
        return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      default:
        return t; // linear
    }
  }

  private interpolateStates(start: CameraState, end: CameraState, t: number): CameraState {
    return {
      position: [
        start.position[0] + (end.position[0] - start.position[0]) * t,
        start.position[1] + (end.position[1] - start.position[1]) * t,
        start.position[2] + (end.position[2] - start.position[2]) * t
      ],
      target: [
        start.target[0] + (end.target[0] - start.target[0]) * t,
        start.target[1] + (end.target[1] - start.target[1]) * t,
        start.target[2] + (end.target[2] - start.target[2]) * t
      ],
      orientation: start.orientation, // Quaternion interpolation would be more complex
      fieldOfView: start.fieldOfView + (end.fieldOfView - start.fieldOfView) * t,
      mode: end.mode,
      movementSpeed: start.movementSpeed + (end.movementSpeed - start.movementSpeed) * t,
      rotationSpeed: start.rotationSpeed + (end.rotationSpeed - start.rotationSpeed) * t,
      zoomLevel: start.zoomLevel + (end.zoomLevel - start.zoomLevel) * t,
      nearPlane: start.nearPlane,
      farPlane: start.farPlane
    };
  }
}