/**
 * Ski Area Card Component - Individual ski area display with preview and metadata
 * Requirements: 7.1 - Ski area cards with preview images and metadata display
 */

import { FC } from 'react';
import { SkiArea } from '../../models/SkiArea';
import './SkiAreaCard.css';

interface SkiAreaCardProps {
  area: SkiArea;
  isSelected: boolean;
  onSelect: () => void;
}

const SkiAreaCard: FC<SkiAreaCardProps> = ({ area, isSelected, onSelect }) => {
  const verticalDrop = area.elevation.max - area.elevation.min;

  return (
    <div 
      className={`ski-area-card ${isSelected ? 'selected' : ''}`}
      onClick={onSelect}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect();
        }
      }}
    >
      <div className="card-image-container">
        <img 
          src={area.previewImage} 
          alt={`${area.name} ski area preview`}
          className="card-image"
          onError={(e) => {
            // Fallback to a placeholder if image fails to load
            const target = e.target as HTMLImageElement;
            target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjNjM2MzYzIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIyNCIgZmlsbD0id2hpdGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5Ta2kgQXJlYTwvdGV4dD48L3N2Zz4=';
          }}
        />
        <div className="card-overlay">
          <div className="fis-badge">
            {area.fisCompatible && (
              <span className="fis-compatible">FIS Compatible</span>
            )}
          </div>
        </div>
      </div>

      <div className="card-content">
        <h3 className="area-name">{area.name}</h3>
        <p className="area-location">{area.location}, {area.country}</p>
        
        <div className="area-stats">
          <div className="stat">
            <span className="stat-label">Elevation</span>
            <span className="stat-value">{area.elevation.min}m - {area.elevation.max}m</span>
          </div>
          <div className="stat">
            <span className="stat-label">Vertical Drop</span>
            <span className="stat-value">{verticalDrop}m</span>
          </div>
        </div>

        <div className="selection-indicator">
          {isSelected ? (
            <span className="selected-text">✓ Selected</span>
          ) : (
            <span className="select-text">Click to select</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default SkiAreaCard;