/**
 * RenderManager - Handles Three.js scene setup, rendering, and lighting
 * Requirements: 6.1, 6.2 - Camera controls and multiple view modes
 */

import * as THREE from 'three';
import { CameraState } from '../../models/CameraState';

export interface RenderManagerInterface {
  setupScene(): THREE.Scene;
  updateCamera(state: CameraState): void;
  renderFrame(scene: THREE.Scene, camera: THREE.PerspectiveCamera): void;
  setTimeOfDay(time: 'dawn' | 'morning' | 'noon' | 'afternoon' | 'dusk' | 'night'): void;
  dispose(): void;
  getRenderer(): THREE.WebGLRenderer;
  getScene(): THREE.Scene;
}

export class RenderManager implements RenderManagerInterface {
  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private ambientLight!: THREE.AmbientLight;
  private directionalLight!: THREE.DirectionalLight;
  private animationId: number | null = null;

  constructor(container: HTMLElement) {
    // Initialize renderer
    this.renderer = new THREE.WebGLRenderer({ 
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance'
    });
    
    this.renderer.setSize(container.clientWidth, container.clientHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;

    container.appendChild(this.renderer.domElement);

    // Initialize scene
    this.scene = this.setupScene();

    // Handle window resize
    window.addEventListener('resize', this.handleResize.bind(this));
  }

  public setupScene(): THREE.Scene {
    const scene = new THREE.Scene();
    
    // Set background to sky blue
    scene.background = new THREE.Color(0x87ceeb);
    
    // Add fog for depth perception
    scene.fog = new THREE.Fog(0x87ceeb, 100, 1000);

    // Setup lighting
    this.setupLighting(scene);

    return scene;
  }

  private setupLighting(scene: THREE.Scene): void {
    // Ambient light for general illumination
    this.ambientLight = new THREE.AmbientLight(0x404040, 0.4);
    scene.add(this.ambientLight);

    // Directional light (sun)
    this.directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
    this.directionalLight.position.set(50, 100, 50);
    this.directionalLight.castShadow = true;
    
    // Configure shadow properties
    this.directionalLight.shadow.mapSize.width = 2048;
    this.directionalLight.shadow.mapSize.height = 2048;
    this.directionalLight.shadow.camera.near = 0.5;
    this.directionalLight.shadow.camera.far = 500;
    this.directionalLight.shadow.camera.left = -100;
    this.directionalLight.shadow.camera.right = 100;
    this.directionalLight.shadow.camera.top = 100;
    this.directionalLight.shadow.camera.bottom = -100;
    
    scene.add(this.directionalLight);

    // Add hemisphere light for more natural lighting
    const hemisphereLight = new THREE.HemisphereLight(0x87ceeb, 0x362d1d, 0.3);
    scene.add(hemisphereLight);
  }

  public updateCamera(_state: CameraState): void {
    // Camera updates are handled by CameraManager
    // This method is for any render-specific camera updates
  }

  public renderFrame(scene: THREE.Scene, camera: THREE.PerspectiveCamera): void {
    this.renderer.render(scene, camera);
  }

  public setTimeOfDay(time: 'dawn' | 'morning' | 'noon' | 'afternoon' | 'dusk' | 'night'): void {
    const timeConfigs = {
      dawn: { 
        sunColor: 0xffa500, 
        sunIntensity: 0.6, 
        ambientIntensity: 0.3,
        fogColor: 0xffa500,
        backgroundColor: 0x87ceeb
      },
      morning: { 
        sunColor: 0xffffff, 
        sunIntensity: 0.8, 
        ambientIntensity: 0.4,
        fogColor: 0x87ceeb,
        backgroundColor: 0x87ceeb
      },
      noon: { 
        sunColor: 0xffffff, 
        sunIntensity: 1.0, 
        ambientIntensity: 0.5,
        fogColor: 0x87ceeb,
        backgroundColor: 0x87ceeb
      },
      afternoon: { 
        sunColor: 0xffd700, 
        sunIntensity: 0.9, 
        ambientIntensity: 0.4,
        fogColor: 0xffd700,
        backgroundColor: 0x87ceeb
      },
      dusk: { 
        sunColor: 0xff6347, 
        sunIntensity: 0.5, 
        ambientIntensity: 0.2,
        fogColor: 0xff6347,
        backgroundColor: 0x4682b4
      },
      night: { 
        sunColor: 0x404080, 
        sunIntensity: 0.1, 
        ambientIntensity: 0.1,
        fogColor: 0x191970,
        backgroundColor: 0x191970
      }
    };

    const config = timeConfigs[time];
    
    // Update lighting
    this.directionalLight.color.setHex(config.sunColor);
    this.directionalLight.intensity = config.sunIntensity;
    this.ambientLight.intensity = config.ambientIntensity;
    
    // Update scene background and fog
    this.scene.background = new THREE.Color(config.backgroundColor);
    if (this.scene.fog) {
      (this.scene.fog as THREE.Fog).color.setHex(config.fogColor);
    }
  }

  private handleResize(): void {
    const container = this.renderer.domElement.parentElement;
    if (!container) return;

    this.renderer.setSize(container.clientWidth, container.clientHeight);
  }

  public dispose(): void {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }

    window.removeEventListener('resize', this.handleResize.bind(this));
    
    // Clean up Three.js resources
    this.scene.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        object.geometry.dispose();
        if (Array.isArray(object.material)) {
          object.material.forEach(material => material.dispose());
        } else {
          object.material.dispose();
        }
      }
    });
    
    this.renderer.dispose();
  }

  public getRenderer(): THREE.WebGLRenderer {
    return this.renderer;
  }

  public getScene(): THREE.Scene {
    return this.scene;
  }
}