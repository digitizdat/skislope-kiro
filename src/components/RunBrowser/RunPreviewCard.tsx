/**
 * Run Preview Card Component - Display run metadata, statistics, and thumbnail maps
 * Requirements: 10.7, 10.8 - Run preview cards with metadata, statistics, editing functionality
 */

import { useState, FC } from 'react';
import { SkiArea } from '../../models/SkiArea';
import { SkiRun, SurfaceType } from '../../models/SkiRun';
import './RunPreviewCard.css';

interface RunPreviewCardProps {
  run: SkiRun;
  skiArea: SkiArea;
  isSelected: boolean;
  isEditing: boolean;
  onSelect: () => void;
  onEdit: () => void;
  onSaveEdit: (updatedRun: SkiRun) => void;
  onCancelEdit: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
}

const RunPreviewCard: FC<RunPreviewCardProps> = ({
  run,
  skiArea: _skiArea, // Prefix with underscore to indicate intentionally unused
  isSelected,
  isEditing,
  onSelect,
  onEdit,
  onSaveEdit,
  onCancelEdit,
  onDuplicate,
  onDelete
}) => {
  const [editForm, setEditForm] = useState({
    name: run.name,
    difficulty: run.metadata.difficulty,
    surfaceType: run.metadata.surfaceType,
    notes: run.metadata.notes || '',
    tags: run.metadata.tags.join(', ')
  });

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const updatedRun: SkiRun = {
      ...run,
      name: editForm.name.trim(),
      metadata: {
        ...run.metadata,
        difficulty: editForm.difficulty,
        surfaceType: editForm.surfaceType,
        notes: editForm.notes.trim() || undefined,
        tags: editForm.tags
          .split(',')
          .map(tag => tag.trim())
          .filter(tag => tag.length > 0)
          .filter((tag, index, arr) => arr.indexOf(tag) === index) // Remove duplicates
      }
    };

    onSaveEdit(updatedRun);
  };

  const getDifficultyColor = (difficulty: string): string => {
    switch (difficulty) {
      case 'beginner': return '#22c55e';
      case 'intermediate': return '#3b82f6';
      case 'advanced': return '#f59e0b';
      case 'expert': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getSurfaceTypeIcon = (surfaceType: SurfaceType): string => {
    switch (surfaceType) {
      case SurfaceType.POWDER: return '❄️';
      case SurfaceType.PACKED: return '🎿';
      case SurfaceType.ICE: return '🧊';
      case SurfaceType.MOGULS: return '⛰️';
      case SurfaceType.TREES: return '🌲';
      case SurfaceType.ROCKS: return '🪨';
      default: return '❄️';
    }
  };

  const formatDate = (date: Date): string => {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    }).format(date);
  };

  const generateThumbnailMap = (): string => {
    // Generate a simple SVG thumbnail representing the run boundary
    const width = 200;
    const height = 120;
    const padding = 10;
    
    if (run.boundary.length < 3) {
      return `data:image/svg+xml;base64,${btoa(`
        <svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
          <rect width="100%" height="100%" fill="#f3f4f6"/>
          <text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="#6b7280" font-family="Arial, sans-serif" font-size="12">
            No boundary data
          </text>
        </svg>
      `)}`;
    }

    // Calculate bounds
    const lats = run.boundary.map(coord => coord.lat);
    const lngs = run.boundary.map(coord => coord.lng);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);

    // Scale coordinates to fit in thumbnail
    const scaleX = (width - 2 * padding) / (maxLng - minLng || 1);
    const scaleY = (height - 2 * padding) / (maxLat - minLat || 1);
    const scale = Math.min(scaleX, scaleY);

    const points = run.boundary.map(coord => {
      const x = padding + (coord.lng - minLng) * scale;
      const y = height - padding - (coord.lat - minLat) * scale; // Flip Y axis
      return `${x},${y}`;
    }).join(' ');

    const difficultyColor = getDifficultyColor(run.metadata.difficulty);

    return `data:image/svg+xml;base64,${btoa(`
      <svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
        <rect width="100%" height="100%" fill="#f8fafc"/>
        <polygon points="${points}" fill="${difficultyColor}" fill-opacity="0.3" stroke="${difficultyColor}" stroke-width="2"/>
        <circle cx="${padding + (width - 2 * padding) / 2}" cy="${height - padding}" r="3" fill="#ef4444"/>
        <text x="${width - 5}" y="15" text-anchor="end" fill="#6b7280" font-family="Arial, sans-serif" font-size="10">
          ${run.boundary.length} pts
        </text>
      </svg>
    `)}`;
  };

  if (isEditing) {
    return (
      <div className={`run-preview-card editing ${isSelected ? 'selected' : ''}`}>
        <form onSubmit={handleEditSubmit} className="edit-form">
          <div className="edit-header">
            <h3>Edit Run</h3>
          </div>

          <div className="edit-fields">
            <div className="field-group">
              <label htmlFor="name">Name</label>
              <input
                id="name"
                type="text"
                value={editForm.name}
                onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                required
                maxLength={100}
              />
            </div>

            <div className="field-group">
              <label htmlFor="difficulty">Difficulty</label>
              <select
                id="difficulty"
                value={editForm.difficulty}
                onChange={(e) => setEditForm(prev => ({ ...prev, difficulty: e.target.value as any }))}
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
                <option value="expert">Expert</option>
                <option value="custom">Custom</option>
              </select>
            </div>

            <div className="field-group">
              <label htmlFor="surfaceType">Surface Type</label>
              <select
                id="surfaceType"
                value={editForm.surfaceType}
                onChange={(e) => setEditForm(prev => ({ ...prev, surfaceType: e.target.value as SurfaceType }))}
              >
                <option value={SurfaceType.POWDER}>Powder</option>
                <option value={SurfaceType.PACKED}>Packed</option>
                <option value={SurfaceType.ICE}>Ice</option>
                <option value={SurfaceType.MOGULS}>Moguls</option>
                <option value={SurfaceType.TREES}>Trees</option>
                <option value={SurfaceType.ROCKS}>Rocks</option>
              </select>
            </div>

            <div className="field-group">
              <label htmlFor="tags">Tags (comma-separated)</label>
              <input
                id="tags"
                type="text"
                value={editForm.tags}
                onChange={(e) => setEditForm(prev => ({ ...prev, tags: e.target.value }))}
                placeholder="steep, scenic, challenging"
              />
            </div>

            <div className="field-group">
              <label htmlFor="notes">Notes</label>
              <textarea
                id="notes"
                value={editForm.notes}
                onChange={(e) => setEditForm(prev => ({ ...prev, notes: e.target.value }))}
                rows={3}
                maxLength={500}
                placeholder="Additional notes about this run..."
              />
            </div>
          </div>

          <div className="edit-actions">
            <button type="button" onClick={onCancelEdit} className="cancel-button">
              Cancel
            </button>
            <button type="submit" className="save-button">
              Save Changes
            </button>
          </div>
        </form>
      </div>
    );
  }

  return (
    <div 
      className={`run-preview-card ${isSelected ? 'selected' : ''}`}
      onClick={onSelect}
    >
      <div className="card-thumbnail">
        <img 
          src={generateThumbnailMap()} 
          alt={`${run.name} boundary map`}
          className="thumbnail-map"
        />
        <div className="difficulty-badge" style={{ backgroundColor: getDifficultyColor(run.metadata.difficulty) }}>
          {run.metadata.difficulty}
        </div>
      </div>

      <div className="card-content">
        <div className="card-header">
          <h3 className="run-name">{run.name}</h3>
          <div className="surface-type">
            {getSurfaceTypeIcon(run.metadata.surfaceType)}
          </div>
        </div>

        <div className="run-statistics">
          <div className="stat">
            <span className="stat-label">Length</span>
            <span className="stat-value">{Math.round(run.statistics.estimatedLength)}m</span>
          </div>
          <div className="stat">
            <span className="stat-label">Drop</span>
            <span className="stat-value">{Math.round(run.statistics.verticalDrop)}m</span>
          </div>
          <div className="stat">
            <span className="stat-label">Slope</span>
            <span className="stat-value">{run.statistics.averageSlope.toFixed(1)}°</span>
          </div>
          <div className="stat">
            <span className="stat-label">Area</span>
            <span className="stat-value">{(run.statistics.area / 10000).toFixed(1)}ha</span>
          </div>
        </div>

        {run.metadata.tags.length > 0 && (
          <div className="run-tags">
            {run.metadata.tags
              .filter(tag => tag && tag.trim().length > 0)
              .slice(0, 3)
              .map((tag, index) => (
                <span key={index} className="tag" title={`Tag: "${tag}"`}>
                  {tag.trim()}
                </span>
              ))}
            {run.metadata.tags.filter(tag => tag && tag.trim().length > 0).length > 3 && (
              <span className="tag-more">+{run.metadata.tags.filter(tag => tag && tag.trim().length > 0).length - 3}</span>
            )}
          </div>
        )}

        {run.metadata.notes && (
          <div className="run-notes">
            <p>{run.metadata.notes.length > 100 ? 
              `${run.metadata.notes.substring(0, 100)}...` : 
              run.metadata.notes
            }</p>
          </div>
        )}

        <div className="card-footer">
          <div className="run-dates">
            <span className="created-date">Created {formatDate(run.createdAt)}</span>
            {run.lastModified.getTime() !== run.createdAt.getTime() && (
              <span className="modified-date">Modified {formatDate(run.lastModified)}</span>
            )}
          </div>
        </div>
      </div>

      <div className="card-actions">
        <button 
          className="action-button edit-button"
          onClick={(e) => {
            e.stopPropagation();
            onEdit();
          }}
          title="Edit run"
        >
          ✏️
        </button>
        <button 
          className="action-button duplicate-button"
          onClick={(e) => {
            e.stopPropagation();
            onDuplicate();
          }}
          title="Duplicate run"
        >
          📋
        </button>
        <button 
          className="action-button delete-button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          title="Delete run"
        >
          🗑️
        </button>
      </div>
    </div>
  );
};

export default RunPreviewCard;