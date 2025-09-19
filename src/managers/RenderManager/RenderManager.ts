/**
 * RenderManager - Handles Three.js scene setup, rendering, and lighting
 * Requirements: 6.1, 6.2 - Camera controls and multiple view modes
 */

import * as THREE from 'three';
import { CameraState } from '../../models/CameraState';
import { TerrainMesh } from '../../services/TerrainService';


export interface RenderManagerInterface {
  setupScene(): THREE.Scene;
  updateCamera(state: CameraState): void;
  renderFrame(scene: THREE.Scene, camera: THREE.PerspectiveCamera): void;
  setTimeOfDay(time: 'dawn' | 'morning' | 'noon' | 'afternoon' | 'dusk' | 'night'): void;
  addTerrainMesh(terrainMesh: TerrainMesh): void;
  removeTerrainMesh(): void;
  updateLOD(camera: THREE.Camera): void;
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
  private currentTerrainMesh: THREE.Mesh | null = null;

  private lodGroup: THREE.LOD | null = null;

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
    
    // Clean up terrain resources
    this.removeTerrainMesh();
    
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

  /**
   * Add terrain mesh to the scene with LOD support
   * Requirements: 7.5 - LOD system for different grid sizes applied to run boundaries
   */
  public addTerrainMesh(terrainMesh: TerrainMesh): void {
    // Remove existing terrain if present
    this.removeTerrainMesh();



    if (terrainMesh.lodLevels.length > 0) {
      // Create LOD group for automatic level switching
      this.lodGroup = new THREE.LOD();

      // Add main geometry at closest distance
      const mainMesh = new THREE.Mesh(terrainMesh.geometry, terrainMesh.materials[0]);
      mainMesh.castShadow = true;
      mainMesh.receiveShadow = true;
      this.lodGroup.addLevel(mainMesh, 0);

      // Add LOD levels
      for (const lodLevel of terrainMesh.lodLevels) {
        const lodMesh = new THREE.Mesh(lodLevel.geometry, terrainMesh.materials[0]);
        lodMesh.castShadow = true;
        lodMesh.receiveShadow = true;
        this.lodGroup.addLevel(lodMesh, lodLevel.distance);
      }

      this.scene.add(this.lodGroup);
    } else {
      // No LOD levels, add single mesh
      this.currentTerrainMesh = new THREE.Mesh(terrainMesh.geometry, terrainMesh.materials[0]);
      this.currentTerrainMesh.castShadow = true;
      this.currentTerrainMesh.receiveShadow = true;
      this.scene.add(this.currentTerrainMesh);
    }

    // Update shadow camera to encompass terrain
    this.updateShadowCamera(terrainMesh.boundingBox);
  }

  /**
   * Remove current terrain mesh from scene
   */
  public removeTerrainMesh(): void {
    if (this.lodGroup) {
      this.scene.remove(this.lodGroup);
      
      // Dispose of LOD geometries and materials
      this.lodGroup.levels.forEach(level => {
        const mesh = level.object as THREE.Mesh;
        mesh.geometry.dispose();
        if (Array.isArray(mesh.material)) {
          mesh.material.forEach(material => material.dispose());
        } else {
          mesh.material.dispose();
        }
      });
      
      this.lodGroup = null;
    }

    if (this.currentTerrainMesh) {
      this.scene.remove(this.currentTerrainMesh);
      this.currentTerrainMesh.geometry.dispose();
      
      if (Array.isArray(this.currentTerrainMesh.material)) {
        this.currentTerrainMesh.material.forEach(material => material.dispose());
      } else {
        this.currentTerrainMesh.material.dispose();
      }
      
      this.currentTerrainMesh = null;
    }


  }

  /**
   * Update LOD based on camera position
   * Requirements: 7.5 - Dynamic LOD based on camera distance
   */
  public updateLOD(camera: THREE.Camera): void {
    if (this.lodGroup) {
      this.lodGroup.update(camera);
    }
  }

  /**
   * Update shadow camera to encompass terrain bounds
   */
  private updateShadowCamera(boundingBox: THREE.Box3): void {
    const size = boundingBox.getSize(new THREE.Vector3());
    const center = boundingBox.getCenter(new THREE.Vector3());

    // Expand shadow camera to cover terrain
    const maxSize = Math.max(size.x, size.z) * 1.2; // Add 20% padding
    
    this.directionalLight.shadow.camera.left = -maxSize / 2;
    this.directionalLight.shadow.camera.right = maxSize / 2;
    this.directionalLight.shadow.camera.top = maxSize / 2;
    this.directionalLight.shadow.camera.bottom = -maxSize / 2;
    this.directionalLight.shadow.camera.near = 0.5;
    this.directionalLight.shadow.camera.far = size.y + 200; // Height + buffer

    // Position light above terrain center
    this.directionalLight.position.set(
      center.x + 50,
      center.y + size.y + 100,
      center.z + 50
    );
    this.directionalLight.target.position.copy(center);

    this.directionalLight.shadow.camera.updateProjectionMatrix();
  }
}