/**
 * InputManager - Handles multi-input support for camera controls
 * Requirements: 6.1, 6.2 - Camera controls and multiple view modes
 */

import { InputState, ControlType } from '../../models/CameraState';

export interface InputManagerInterface {
  getInputState(): InputState;
  enableControls(type: ControlType): void;
  disableControls(type: ControlType): void;
  dispose(): void;
}

export class InputManager implements InputManagerInterface {
  private inputState: InputState;
  private enabledControls: Set<ControlType>;
  private element: HTMLElement;
  private boundHandlers: Map<string, any>;

  constructor(element: HTMLElement) {
    this.element = element;
    this.enabledControls = new Set();
    this.boundHandlers = new Map();
    
    // Initialize input state
    this.inputState = {
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
    };

    // Enable default controls
    this.enableControls(ControlType.MOUSE);
    this.enableControls(ControlType.KEYBOARD);
  }

  public getInputState(): InputState {
    // Reset delta values after each frame
    const state = { ...this.inputState };
    this.inputState.mouse.deltaX = 0;
    this.inputState.mouse.deltaY = 0;
    this.inputState.mouse.wheel = 0;
    
    return state;
  }

  public enableControls(type: ControlType): void {
    if (this.enabledControls.has(type)) return;
    
    this.enabledControls.add(type);
    
    switch (type) {
      case ControlType.MOUSE:
        this.setupMouseControls();
        break;
      case ControlType.KEYBOARD:
        this.setupKeyboardControls();
        break;
      case ControlType.GAMEPAD:
        this.setupGamepadControls();
        break;
      case ControlType.TOUCH:
        this.setupTouchControls();
        break;
    }
  }

  public disableControls(type: ControlType): void {
    if (!this.enabledControls.has(type)) return;
    
    this.enabledControls.delete(type);
    this.removeEventListeners(type);
  }

  private setupMouseControls(): void {
    const onMouseMove = (event: MouseEvent) => {
      const rect = this.element.getBoundingClientRect();
      const newX = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      const newY = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      
      this.inputState.mouse.deltaX = newX - this.inputState.mouse.x;
      this.inputState.mouse.deltaY = newY - this.inputState.mouse.y;
      this.inputState.mouse.x = newX;
      this.inputState.mouse.y = newY;
    };

    const onMouseDown = (event: MouseEvent) => {
      switch (event.button) {
        case 0: this.inputState.mouse.leftButton = true; break;
        case 1: this.inputState.mouse.middleButton = true; break;
        case 2: this.inputState.mouse.rightButton = true; break;
      }
      event.preventDefault();
    };

    const onMouseUp = (event: MouseEvent) => {
      switch (event.button) {
        case 0: this.inputState.mouse.leftButton = false; break;
        case 1: this.inputState.mouse.middleButton = false; break;
        case 2: this.inputState.mouse.rightButton = false; break;
      }
    };

    const onWheel = (event: WheelEvent) => {
      this.inputState.mouse.wheel = event.deltaY;
      event.preventDefault();
    };

    const onContextMenu = (event: Event) => {
      event.preventDefault();
    };

    // Add event listeners
    this.element.addEventListener('mousemove', onMouseMove);
    this.element.addEventListener('mousedown', onMouseDown);
    this.element.addEventListener('mouseup', onMouseUp);
    this.element.addEventListener('wheel', onWheel);
    this.element.addEventListener('contextmenu', onContextMenu);

    // Store bound handlers for cleanup
    this.boundHandlers.set('mousemove', onMouseMove);
    this.boundHandlers.set('mousedown', onMouseDown);
    this.boundHandlers.set('mouseup', onMouseUp);
    this.boundHandlers.set('wheel', onWheel);
    this.boundHandlers.set('contextmenu', onContextMenu);
  }

  private setupKeyboardControls(): void {
    const onKeyDown = (event: KeyboardEvent) => {
      switch (event.code) {
        case 'KeyW':
        case 'ArrowUp':
          this.inputState.keyboard.forward = true;
          break;
        case 'KeyS':
        case 'ArrowDown':
          this.inputState.keyboard.backward = true;
          break;
        case 'KeyA':
        case 'ArrowLeft':
          this.inputState.keyboard.left = true;
          break;
        case 'KeyD':
        case 'ArrowRight':
          this.inputState.keyboard.right = true;
          break;
        case 'KeyQ':
        case 'Space':
          this.inputState.keyboard.up = true;
          break;
        case 'KeyE':
        case 'KeyC':
          this.inputState.keyboard.down = true;
          break;
        case 'ShiftLeft':
        case 'ShiftRight':
          this.inputState.keyboard.shift = true;
          break;
        case 'ControlLeft':
        case 'ControlRight':
          this.inputState.keyboard.ctrl = true;
          break;
        case 'AltLeft':
        case 'AltRight':
          this.inputState.keyboard.alt = true;
          break;
      }
    };

    const onKeyUp = (event: KeyboardEvent) => {
      switch (event.code) {
        case 'KeyW':
        case 'ArrowUp':
          this.inputState.keyboard.forward = false;
          break;
        case 'KeyS':
        case 'ArrowDown':
          this.inputState.keyboard.backward = false;
          break;
        case 'KeyA':
        case 'ArrowLeft':
          this.inputState.keyboard.left = false;
          break;
        case 'KeyD':
        case 'ArrowRight':
          this.inputState.keyboard.right = false;
          break;
        case 'KeyQ':
        case 'Space':
          this.inputState.keyboard.up = false;
          break;
        case 'KeyE':
        case 'KeyC':
          this.inputState.keyboard.down = false;
          break;
        case 'ShiftLeft':
        case 'ShiftRight':
          this.inputState.keyboard.shift = false;
          break;
        case 'ControlLeft':
        case 'ControlRight':
          this.inputState.keyboard.ctrl = false;
          break;
        case 'AltLeft':
        case 'AltRight':
          this.inputState.keyboard.alt = false;
          break;
      }
    };

    // Add event listeners to window for global keyboard capture
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);

    // Store bound handlers for cleanup
    this.boundHandlers.set('keydown', onKeyDown);
    this.boundHandlers.set('keyup', onKeyUp);
  }

  private setupGamepadControls(): void {
    // Gamepad support - basic implementation
    const updateGamepad = () => {
      const gamepads = navigator.getGamepads();
      const gamepad = gamepads[0];
      
      if (gamepad) {
        this.inputState.gamepad = {
          leftStick: [gamepad.axes[0] || 0, gamepad.axes[1] || 0],
          rightStick: [gamepad.axes[2] || 0, gamepad.axes[3] || 0],
          triggers: [gamepad.buttons[6]?.value || 0, gamepad.buttons[7]?.value || 0],
          buttons: gamepad.buttons.map(button => button.pressed)
        };
      }
    };

    // Poll gamepad state
    const gamepadInterval = setInterval(updateGamepad, 16); // ~60fps
    this.boundHandlers.set('gamepadInterval', () => clearInterval(gamepadInterval));
  }

  private setupTouchControls(): void {
    const onTouchStart = (event: TouchEvent) => {
      event.preventDefault();
      this.updateTouchState(event);
    };

    const onTouchMove = (event: TouchEvent) => {
      event.preventDefault();
      this.updateTouchState(event);
    };

    const onTouchEnd = (event: TouchEvent) => {
      event.preventDefault();
      this.inputState.touch = {
        touches: [],
        pinchScale: 1,
        pinchDelta: 0
      };
    };

    this.element.addEventListener('touchstart', onTouchStart, { passive: false });
    this.element.addEventListener('touchmove', onTouchMove, { passive: false });
    this.element.addEventListener('touchend', onTouchEnd, { passive: false });

    this.boundHandlers.set('touchstart', onTouchStart);
    this.boundHandlers.set('touchmove', onTouchMove);
    this.boundHandlers.set('touchend', onTouchEnd);
  }

  private updateTouchState(event: TouchEvent): void {
    const rect = this.element.getBoundingClientRect();
    const touches = Array.from(event.touches).map((touch) => {
      const x = ((touch.clientX - rect.left) / rect.width) * 2 - 1;
      const y = -((touch.clientY - rect.top) / rect.height) * 2 + 1;
      
      const prevTouch = this.inputState.touch?.touches.find(t => t.id === touch.identifier);
      
      return {
        id: touch.identifier,
        x,
        y,
        deltaX: prevTouch ? x - prevTouch.x : 0,
        deltaY: prevTouch ? y - prevTouch.y : 0
      };
    });

    let pinchScale = 1;
    let pinchDelta = 0;

    if (touches.length === 2) {
      const distance = Math.sqrt(
        Math.pow(touches[1].x - touches[0].x, 2) + 
        Math.pow(touches[1].y - touches[0].y, 2)
      );
      
      if (this.inputState.touch && this.inputState.touch.touches.length === 2) {
        const prevDistance = Math.sqrt(
          Math.pow(this.inputState.touch.touches[1].x - this.inputState.touch.touches[0].x, 2) + 
          Math.pow(this.inputState.touch.touches[1].y - this.inputState.touch.touches[0].y, 2)
        );
        pinchScale = distance / prevDistance;
        pinchDelta = distance - prevDistance;
      }
    }

    this.inputState.touch = {
      touches,
      pinchScale,
      pinchDelta
    };
  }

  private removeEventListeners(type: ControlType): void {
    switch (type) {
      case ControlType.MOUSE:
        this.element.removeEventListener('mousemove', this.boundHandlers.get('mousemove')!);
        this.element.removeEventListener('mousedown', this.boundHandlers.get('mousedown')!);
        this.element.removeEventListener('mouseup', this.boundHandlers.get('mouseup')!);
        this.element.removeEventListener('wheel', this.boundHandlers.get('wheel')!);
        this.element.removeEventListener('contextmenu', this.boundHandlers.get('contextmenu')!);
        break;
      case ControlType.KEYBOARD:
        window.removeEventListener('keydown', this.boundHandlers.get('keydown')!);
        window.removeEventListener('keyup', this.boundHandlers.get('keyup')!);
        break;
      case ControlType.GAMEPAD:
        const gamepadCleanup = this.boundHandlers.get('gamepadInterval');
        if (gamepadCleanup) gamepadCleanup();
        break;
      case ControlType.TOUCH:
        this.element.removeEventListener('touchstart', this.boundHandlers.get('touchstart')!);
        this.element.removeEventListener('touchmove', this.boundHandlers.get('touchmove')!);
        this.element.removeEventListener('touchend', this.boundHandlers.get('touchend')!);
        break;
    }
  }

  public dispose(): void {
    // Remove all event listeners
    for (const type of this.enabledControls) {
      this.removeEventListeners(type);
    }
    this.enabledControls.clear();
    this.boundHandlers.clear();
  }
}