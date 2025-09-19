import * as THREE from 'three'
import { RenderManager } from '../managers/RenderManager/RenderManager'
import { CameraManager } from '../managers/CameraManager/CameraManager'
import { InputManager } from '../managers/InputManager/InputManager'
import { CameraMode } from '../models/CameraState'
import { TerrainMesh } from '../services/TerrainService'

/**
 * Enhanced Three.js setup with integrated camera and input management
 * Requirements: 6.1, 6.2 - Camera controls and multiple view modes
 */
export class ThreeSetup {
  private scene: THREE.Scene
  private camera: THREE.PerspectiveCamera
  private renderManager: RenderManager
  private cameraManager: CameraManager
  private inputManager: InputManager
  private animationId: number | null = null
  private hasTerrainMesh: boolean = false

  constructor(container: HTMLElement) {
    // Initialize camera first
    this.camera = new THREE.PerspectiveCamera(
      75,
      container.clientWidth / container.clientHeight,
      0.1,
      10000
    )
    this.camera.position.set(0, 10, 20)
    this.camera.lookAt(0, 0, 0)

    // Initialize managers
    this.renderManager = new RenderManager(container)
    this.cameraManager = new CameraManager(this.camera)
    this.inputManager = new InputManager(container)

    // Get scene from render manager
    this.scene = this.renderManager.getScene()

    // Add a test cube to verify rendering (only if no terrain is loaded)
    if (!this.hasTerrainMesh) {
      this.addTestGeometry()
    }

    // Handle window resize
    window.addEventListener('resize', this.handleResize.bind(this))
  }

  // Lighting is now handled by RenderManager

  private addTestGeometry(): void {
    // Create a simple terrain-like plane
    const geometry = new THREE.PlaneGeometry(50, 50, 64, 64)
    const material = new THREE.MeshLambertMaterial({ 
      color: 0xffffff,
      wireframe: false 
    })
    
    const plane = new THREE.Mesh(geometry, material)
    plane.rotation.x = -Math.PI / 2
    plane.receiveShadow = true
    this.scene.add(plane)

    // Add multiple test objects to demonstrate camera movement
    const cubeGeometry = new THREE.BoxGeometry(2, 2, 2)
    const cubeMaterial = new THREE.MeshLambertMaterial({ color: 0x00ff00 })
    const cube = new THREE.Mesh(cubeGeometry, cubeMaterial)
    cube.position.set(0, 1, 0)
    cube.castShadow = true
    this.scene.add(cube)

    // Add some reference objects
    for (let i = 0; i < 5; i++) {
      const sphereGeometry = new THREE.SphereGeometry(1, 16, 16)
      const sphereMaterial = new THREE.MeshLambertMaterial({ 
        color: new THREE.Color().setHSL(i / 5, 0.7, 0.5) 
      })
      const sphere = new THREE.Mesh(sphereGeometry, sphereMaterial)
      sphere.position.set(
        (Math.random() - 0.5) * 40,
        1,
        (Math.random() - 0.5) * 40
      )
      sphere.castShadow = true
      this.scene.add(sphere)
    }

    // Animate the cube
    const animate = () => {
      cube.rotation.x += 0.01
      cube.rotation.y += 0.01
    }

    this.animate = animate
  }

  private animate = (): void => {
    // Override in addTestGeometry
  }

  public startAnimation(): void {
    const renderLoop = () => {
      this.animationId = requestAnimationFrame(renderLoop)
      
      // Update camera based on input
      const inputState = this.inputManager.getInputState()
      const currentCameraState = this.cameraManager.getCurrentState()
      this.cameraManager.updateCamera(currentCameraState, inputState)
      
      // Update LOD based on camera
      this.renderManager.updateLOD(this.camera)
      
      // Animate test geometry (only if no terrain)
      if (!this.hasTerrainMesh) {
        this.animate()
      }
      
      // Render the frame
      this.renderManager.renderFrame(this.scene, this.camera)
    }
    renderLoop()
  }

  public stopAnimation(): void {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId)
      this.animationId = null
    }
  }

  private handleResize(): void {
    const container = this.renderManager.getRenderer().domElement.parentElement
    if (!container) return

    this.camera.aspect = container.clientWidth / container.clientHeight
    this.camera.updateProjectionMatrix()
    this.renderManager.getRenderer().setSize(container.clientWidth, container.clientHeight)
  }

  public dispose(): void {
    this.stopAnimation()
    window.removeEventListener('resize', this.handleResize.bind(this))
    
    // Dispose managers
    this.renderManager.dispose()
    this.inputManager.dispose()
  }

  // Getters for external access
  public getScene(): THREE.Scene {
    return this.scene
  }

  public getCamera(): THREE.PerspectiveCamera {
    return this.camera
  }

  public getRenderer(): THREE.WebGLRenderer {
    return this.renderManager.getRenderer()
  }

  public getRenderManager(): RenderManager {
    return this.renderManager
  }

  public getCameraManager(): CameraManager {
    return this.cameraManager
  }

  public getInputManager(): InputManager {
    return this.inputManager
  }

  // Camera control methods
  public setCameraMode(mode: CameraMode): void {
    this.cameraManager.setViewMode(mode)
  }

  public setTimeOfDay(time: 'dawn' | 'morning' | 'noon' | 'afternoon' | 'dusk' | 'night'): void {
    this.renderManager.setTimeOfDay(time)
  }

  public async flyToPosition(position: [number, number, number], duration: number = 2000): Promise<void> {
    return this.cameraManager.flyToPosition(position, duration)
  }

  // Terrain mesh methods
  public addTerrainMesh(terrainMesh: TerrainMesh): void {
    // Remove test geometry if present
    if (!this.hasTerrainMesh) {
      this.clearTestGeometry()
    }

    // Add terrain mesh to render manager
    this.renderManager.addTerrainMesh(terrainMesh)
    this.hasTerrainMesh = true
  }

  public removeTerrainMesh(): void {
    this.renderManager.removeTerrainMesh()
    this.hasTerrainMesh = false
    
    // Add test geometry back if no terrain
    this.addTestGeometry()
  }

  private clearTestGeometry(): void {
    // Remove test objects from scene
    const objectsToRemove: THREE.Object3D[] = []
    
    this.scene.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        objectsToRemove.push(object)
      }
    })

    objectsToRemove.forEach(object => {
      this.scene.remove(object)
      if (object instanceof THREE.Mesh) {
        object.geometry.dispose()
        if (Array.isArray(object.material)) {
          object.material.forEach(material => material.dispose())
        } else {
          object.material.dispose()
        }
      }
    })
  }
}