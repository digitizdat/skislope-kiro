/**
 * Map Service for satellite imagery and topographical data
 * Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6
 */

import { SkiArea } from '../models/SkiArea';
import { 
  GeographicCoordinate, 
  RunStatistics, 
  ValidationResult, 
  TopographicalData,
  calculateDistance,
  calculatePolygonArea,
  calculateBoundingBox
} from '../models/SkiRun';

export interface MapServiceInterface {
  loadSatelliteImagery(area: SkiArea): Promise<string>;
  loadTopographicalOverlay(area: SkiArea): Promise<TopographicalData>;
  calculateRunStatistics(boundary: GeographicCoordinate[]): RunStatistics;
  validateRunBoundary(boundary: GeographicCoordinate[]): ValidationResult;
}

export class MapService implements MapServiceInterface {
  private readonly MIN_BOUNDARY_POINTS = 3;
  private readonly MAX_BOUNDARY_POINTS = 100;
  private readonly MIN_AREA_SQMETERS = 1000; // 1000 square meters minimum
  private readonly MAX_AREA_SQMETERS = 10000000; // 10 square kilometers maximum
  private readonly MAX_LENGTH_METERS = 10000; // 10 kilometers maximum

  /**
   * Load satellite imagery URL for the given ski area
   * Requirements: 10.1 - Display high-resolution satellite imagery
   */
  async loadSatelliteImagery(area: SkiArea): Promise<string> {
    // For now, return a placeholder satellite tile URL
    // In production, this would integrate with actual satellite imagery providers
    // The area parameter is used for future implementation of area-specific imagery
    console.log(`Loading satellite imagery for ${area.name}`);
    
    return `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`;
  }

  /**
   * Load topographical overlay data for the given ski area
   * Requirements: 10.2 - Overlay topographical contour lines
   */
  async loadTopographicalOverlay(area: SkiArea): Promise<TopographicalData> {
    // Mock topographical data - in production this would fetch real elevation data
    const contourLines = this.generateMockContourLines(area);
    const elevationPoints = this.generateMockElevationPoints(area);
    
    return {
      contourLines,
      elevationPoints,
      bounds: area.bounds
    };
  }

  /**
   * Calculate statistics for a run boundary
   * Requirements: 10.4, 10.5 - Visual feedback and run statistics
   */
  calculateRunStatistics(boundary: GeographicCoordinate[]): RunStatistics {
    if (boundary.length < 3) {
      return {
        estimatedLength: 0,
        verticalDrop: 0,
        averageSlope: 0,
        boundingBox: { northEast: { lat: 0, lng: 0 }, southWest: { lat: 0, lng: 0 } },
        area: 0
      };
    }

    // Calculate perimeter length
    let totalLength = 0;
    for (let i = 0; i < boundary.length; i++) {
      const next = (i + 1) % boundary.length;
      totalLength += calculateDistance(boundary[i], boundary[next]);
    }

    // Calculate area
    const area = calculatePolygonArea(boundary);

    // Calculate bounding box
    const boundingBox = calculateBoundingBox(boundary);

    // Mock elevation calculations - in production would use real elevation data
    const elevationRange = this.estimateElevationRange(boundary);
    const verticalDrop = elevationRange.max - elevationRange.min;
    const averageSlope = totalLength > 0 ? Math.atan(verticalDrop / totalLength) * (180 / Math.PI) : 0;

    return {
      estimatedLength: totalLength,
      verticalDrop,
      averageSlope,
      boundingBox,
      area
    };
  }

  /**
   * Validate run boundary for size and shape constraints
   * Requirements: 10.8 - Warn if defined area is too large for performance
   * Add run validation to ensure boundaries are reasonable size and shape
   */
  validateRunBoundary(boundary: GeographicCoordinate[]): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Check minimum points
    if (boundary.length < this.MIN_BOUNDARY_POINTS) {
      errors.push(`Run boundary must have at least ${this.MIN_BOUNDARY_POINTS} points`);
    }

    // Check maximum points
    if (boundary.length > this.MAX_BOUNDARY_POINTS) {
      errors.push(`Run boundary cannot have more than ${this.MAX_BOUNDARY_POINTS} points`);
    }

    if (boundary.length >= this.MIN_BOUNDARY_POINTS) {
      const stats = this.calculateRunStatistics(boundary);

      // Check area constraints
      if (stats.area < this.MIN_AREA_SQMETERS) {
        errors.push(`Run area is too small (minimum ${(this.MIN_AREA_SQMETERS / 10000).toFixed(2)} hectares)`);
      }

      if (stats.area > this.MAX_AREA_SQMETERS) {
        errors.push(`Run area is too large (maximum ${(this.MAX_AREA_SQMETERS / 1000000).toFixed(1)} km²)`);
        warnings.push('Large areas may impact performance on lower-end devices');
      }

      // Check length constraints
      if (stats.estimatedLength > this.MAX_LENGTH_METERS) {
        warnings.push('Very long runs may require higher detail levels for optimal experience');
      }

      // Performance warnings based on area
      if (stats.area > 5000000) { // 5 square kilometers
        warnings.push('Large run area detected - consider using lower grid sizes for better performance');
      }

      // Shape validation - check for self-intersecting polygon
      if (this.isPolygonSelfIntersecting(boundary)) {
        errors.push('Run boundary cannot intersect itself');
      }

      // Shape validation - check for reasonable aspect ratio
      const aspectRatio = this.calculateAspectRatio(stats.boundingBox);
      if (aspectRatio > 20) {
        warnings.push('Run boundary is very elongated - consider a more compact shape for better performance');
      }

      // Shape validation - check for minimum width
      const minWidth = this.calculateMinimumWidth(boundary);
      if (minWidth < 50) { // 50 meters minimum width
        warnings.push('Run boundary is very narrow - ensure adequate width for realistic skiing experience');
      }

      // Slope validation - check for reasonable slope angles
      if (stats.averageSlope > 45) {
        warnings.push('Very steep average slope detected - ensure this matches the intended difficulty level');
      } else if (stats.averageSlope < 5) {
        warnings.push('Very gentle slope detected - may not provide realistic skiing experience');
      }

      // Elevation validation
      if (stats.verticalDrop < 50) {
        warnings.push('Low vertical drop - consider including more elevation change for better skiing experience');
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * Generate mock contour lines for development
   */
  private generateMockContourLines(area: SkiArea): any[] {
    const contourLines = [];
    const elevationStep = (area.elevation.max - area.elevation.min) / 10;
    
    for (let i = 0; i < 10; i++) {
      const elevation = area.elevation.min + (i * elevationStep);
      contourLines.push({
        elevation: Math.round(elevation),
        coordinates: this.generateContourPath(area, elevation)
      });
    }
    
    return contourLines;
  }

  /**
   * Generate mock elevation points for development
   */
  private generateMockElevationPoints(area: SkiArea): any[] {
    const points = [];
    const latStep = (area.bounds.northEast.lat - area.bounds.southWest.lat) / 20;
    const lngStep = (area.bounds.northEast.lng - area.bounds.southWest.lng) / 20;
    
    for (let i = 0; i < 20; i++) {
      for (let j = 0; j < 20; j++) {
        const lat = area.bounds.southWest.lat + (i * latStep);
        const lng = area.bounds.southWest.lng + (j * lngStep);
        const elevation = area.elevation.min + 
          Math.random() * (area.elevation.max - area.elevation.min);
        
        points.push({
          coordinate: { lat, lng },
          elevation: Math.round(elevation)
        });
      }
    }
    
    return points;
  }

  /**
   * Generate a mock contour path
   */
  private generateContourPath(area: SkiArea, _elevation: number): GeographicCoordinate[] {
    const path = [];
    const centerLat = (area.bounds.northEast.lat + area.bounds.southWest.lat) / 2;
    const centerLng = (area.bounds.northEast.lng + area.bounds.southWest.lng) / 2;
    const radius = Math.min(
      (area.bounds.northEast.lat - area.bounds.southWest.lat) / 4,
      (area.bounds.northEast.lng - area.bounds.southWest.lng) / 4
    );
    
    for (let angle = 0; angle < 360; angle += 30) {
      const rad = (angle * Math.PI) / 180;
      const lat = centerLat + radius * Math.cos(rad) * (0.5 + Math.random() * 0.5);
      const lng = centerLng + radius * Math.sin(rad) * (0.5 + Math.random() * 0.5);
      path.push({ lat, lng });
    }
    
    return path;
  }

  /**
   * Estimate elevation range for a boundary (mock implementation)
   */
  private estimateElevationRange(_boundary: GeographicCoordinate[]): { min: number; max: number } {
    // Mock elevation calculation - in production would use real elevation API
    const baseElevation = 1500 + Math.random() * 1000;
    const elevationVariation = 200 + Math.random() * 500;
    
    return {
      min: baseElevation,
      max: baseElevation + elevationVariation
    };
  }

  /**
   * Check if polygon is self-intersecting
   */
  private isPolygonSelfIntersecting(boundary: GeographicCoordinate[]): boolean {
    if (boundary.length < 4) return false;
    
    for (let i = 0; i < boundary.length; i++) {
      const line1Start = boundary[i];
      const line1End = boundary[(i + 1) % boundary.length];
      
      for (let j = i + 2; j < boundary.length; j++) {
        if (j === boundary.length - 1 && i === 0) continue; // Skip adjacent segments
        
        const line2Start = boundary[j];
        const line2End = boundary[(j + 1) % boundary.length];
        
        if (this.linesIntersect(line1Start, line1End, line2Start, line2End)) {
          return true;
        }
      }
    }
    
    return false;
  }

  /**
   * Check if two line segments intersect
   */
  private linesIntersect(
    p1: GeographicCoordinate, 
    p2: GeographicCoordinate, 
    p3: GeographicCoordinate, 
    p4: GeographicCoordinate
  ): boolean {
    const denom = (p4.lng - p3.lng) * (p2.lat - p1.lat) - (p4.lat - p3.lat) * (p2.lng - p1.lng);
    if (Math.abs(denom) < 1e-10) return false; // Lines are parallel
    
    const ua = ((p4.lat - p3.lat) * (p1.lng - p3.lng) - (p4.lng - p3.lng) * (p1.lat - p3.lat)) / denom;
    const ub = ((p2.lat - p1.lat) * (p1.lng - p3.lng) - (p2.lng - p1.lng) * (p1.lat - p3.lat)) / denom;
    
    return ua >= 0 && ua <= 1 && ub >= 0 && ub <= 1;
  }

  /**
   * Calculate aspect ratio of bounding box (width/height)
   */
  private calculateAspectRatio(boundingBox: { northEast: GeographicCoordinate; southWest: GeographicCoordinate }): number {
    const width = calculateDistance(
      { lat: boundingBox.southWest.lat, lng: boundingBox.southWest.lng },
      { lat: boundingBox.southWest.lat, lng: boundingBox.northEast.lng }
    );
    const height = calculateDistance(
      { lat: boundingBox.southWest.lat, lng: boundingBox.southWest.lng },
      { lat: boundingBox.northEast.lat, lng: boundingBox.southWest.lng }
    );
    
    return height > 0 ? width / height : 1;
  }

  /**
   * Calculate minimum width of polygon by finding the shortest distance between parallel sides
   */
  private calculateMinimumWidth(boundary: GeographicCoordinate[]): number {
    if (boundary.length < 3) return 0;
    
    let minWidth = Infinity;
    
    // For each edge, calculate the distance to the farthest point
    for (let i = 0; i < boundary.length; i++) {
      const p1 = boundary[i];
      const p2 = boundary[(i + 1) % boundary.length];
      
      // Find the maximum distance from this edge to any other point
      let maxDistanceFromEdge = 0;
      for (let j = 0; j < boundary.length; j++) {
        if (j === i || j === (i + 1) % boundary.length) continue;
        
        const distance = this.pointToLineDistance(boundary[j], p1, p2);
        maxDistanceFromEdge = Math.max(maxDistanceFromEdge, distance);
      }
      
      minWidth = Math.min(minWidth, maxDistanceFromEdge);
    }
    
    return minWidth === Infinity ? 0 : minWidth;
  }

  /**
   * Calculate distance from a point to a line segment
   */
  private pointToLineDistance(point: GeographicCoordinate, lineStart: GeographicCoordinate, lineEnd: GeographicCoordinate): number {
    const A = point.lat - lineStart.lat;
    const B = point.lng - lineStart.lng;
    const C = lineEnd.lat - lineStart.lat;
    const D = lineEnd.lng - lineStart.lng;

    const dot = A * C + B * D;
    const lenSq = C * C + D * D;
    
    if (lenSq === 0) {
      // Line start and end are the same point
      return calculateDistance(point, lineStart);
    }
    
    let param = dot / lenSq;
    
    let closestPoint: GeographicCoordinate;
    if (param < 0) {
      closestPoint = lineStart;
    } else if (param > 1) {
      closestPoint = lineEnd;
    } else {
      closestPoint = {
        lat: lineStart.lat + param * C,
        lng: lineStart.lng + param * D
      };
    }
    
    return calculateDistance(point, closestPoint);
  }
}

export const mapService = new MapService();