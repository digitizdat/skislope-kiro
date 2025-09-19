/**
 * Run Creation Form - Form for naming and configuring new runs
 * Requirements: 10.6 - Require name and allow optional metadata
 */

import React, { useState } from 'react';
import { RunStatistics, SurfaceType } from '../../models/SkiRun';
import './RunCreationForm.css';

interface RunCreationFormProps {
  onSubmit: (runData: {
    name: string;
    difficulty: 'beginner' | 'intermediate' | 'advanced' | 'expert' | 'custom';
    surfaceType: SurfaceType;
    notes?: string;
    tags: string[];
  }) => void;
  onCancel: () => void;
  statistics: RunStatistics;
}

const RunCreationForm: React.FC<RunCreationFormProps> = ({ onSubmit, onCancel, statistics }) => {
  const [formData, setFormData] = useState({
    name: '',
    difficulty: 'intermediate' as const,
    surfaceType: SurfaceType.PACKED,
    notes: '',
    tags: [] as string[]
  });
  const [tagInput, setTagInput] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    // Name validation
    if (!formData.name.trim()) {
      newErrors.name = 'Run name is required';
    } else if (formData.name.length < 3) {
      newErrors.name = 'Run name must be at least 3 characters';
    } else if (formData.name.length > 50) {
      newErrors.name = 'Run name must be less than 50 characters';
    } else if (!/^[a-zA-Z0-9\s\-_'()]+$/.test(formData.name)) {
      newErrors.name = 'Run name contains invalid characters';
    }

    // Notes validation
    if (formData.notes && formData.notes.length > 500) {
      newErrors.notes = 'Notes must be less than 500 characters';
    }

    // Statistics validation
    if (statistics.area < 1000) {
      newErrors.general = 'Run area is too small for a realistic skiing experience';
    } else if (statistics.area > 10000000) {
      newErrors.general = 'Run area is too large and may cause performance issues';
    }

    if (statistics.estimatedLength < 100) {
      newErrors.general = 'Run is too short for a meaningful skiing experience';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (validateForm()) {
      onSubmit(formData);
    }
  };

  const handleAddTag = () => {
    const tag = tagInput.trim().toLowerCase();
    if (tag && !formData.tags.includes(tag) && formData.tags.length < 10) {
      setFormData(prev => ({
        ...prev,
        tags: [...prev.tags, tag]
      }));
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(tag => tag !== tagToRemove)
    }));
  };

  const handleTagInputKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const getDifficultyDescription = (difficulty: string): string => {
    switch (difficulty) {
      case 'beginner': return 'Easy slopes, gentle gradients';
      case 'intermediate': return 'Moderate slopes, some challenging sections';
      case 'advanced': return 'Steep slopes, requires good skiing skills';
      case 'expert': return 'Very steep, challenging terrain';
      case 'custom': return 'Custom difficulty level';
      default: return '';
    }
  };

  const getSurfaceDescription = (surface: SurfaceType): string => {
    switch (surface) {
      case SurfaceType.POWDER: return 'Fresh, ungroomed snow';
      case SurfaceType.PACKED: return 'Groomed, compacted snow';
      case SurfaceType.ICE: return 'Hard, icy surface';
      case SurfaceType.MOGULS: return 'Bumpy, mogul terrain';
      case SurfaceType.TREES: return 'Tree skiing, off-piste';
      case SurfaceType.ROCKS: return 'Rocky terrain, advanced only';
      default: return '';
    }
  };

  return (
    <div className="run-creation-form">
      <h3>Create New Run</h3>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="name">Run Name *</label>
          <input
            type="text"
            id="name"
            value={formData.name}
            onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
            placeholder="Enter run name..."
            className={errors.name ? 'error' : ''}
          />
          {errors.name && <span className="error-message">{errors.name}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="difficulty">Difficulty Level</label>
          <select
            id="difficulty"
            value={formData.difficulty}
            onChange={(e) => setFormData(prev => ({ 
              ...prev, 
              difficulty: e.target.value as any 
            }))}
          >
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
            <option value="expert">Expert</option>
            <option value="custom">Custom</option>
          </select>
          <small className="form-help">
            {getDifficultyDescription(formData.difficulty)}
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="surfaceType">Surface Type</label>
          <select
            id="surfaceType"
            value={formData.surfaceType}
            onChange={(e) => setFormData(prev => ({ 
              ...prev, 
              surfaceType: e.target.value as SurfaceType 
            }))}
          >
            <option value={SurfaceType.POWDER}>Powder</option>
            <option value={SurfaceType.PACKED}>Packed</option>
            <option value={SurfaceType.ICE}>Ice</option>
            <option value={SurfaceType.MOGULS}>Moguls</option>
            <option value={SurfaceType.TREES}>Trees</option>
            <option value={SurfaceType.ROCKS}>Rocks</option>
          </select>
          <small className="form-help">
            {getSurfaceDescription(formData.surfaceType)}
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="tags">Tags</label>
          <div className="tag-input-container">
            <input
              type="text"
              id="tags"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyPress={handleTagInputKeyPress}
              placeholder="Add tags..."
              maxLength={20}
            />
            <button 
              type="button" 
              onClick={handleAddTag}
              disabled={!tagInput.trim() || formData.tags.length >= 10}
              className="add-tag-button"
            >
              Add
            </button>
          </div>
          
          {formData.tags.length > 0 && (
            <div className="tags-list">
              {formData.tags.map((tag, index) => (
                <span key={index} className="tag">
                  <span className="tag-text">{tag}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveTag(tag)}
                    className="remove-tag"
                    title="Remove tag"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
          <small className="form-help">
            Add up to 10 tags to help categorize your run
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="notes">Notes</label>
          <textarea
            id="notes"
            value={formData.notes}
            onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
            placeholder="Optional notes about this run..."
            rows={3}
            maxLength={500}
            className={errors.notes ? 'error' : ''}
          />
          {errors.notes && <span className="error-message">{errors.notes}</span>}
          <small className="form-help">
            {formData.notes.length}/500 characters
          </small>
        </div>

        <div className="run-summary">
          <h4>Run Summary</h4>
          <div className="summary-stats">
            <span>Length: {(statistics.estimatedLength / 1000).toFixed(2)} km</span>
            <span>Drop: {Math.round(statistics.verticalDrop)} m</span>
            <span>Slope: {statistics.averageSlope.toFixed(1)}°</span>
            <span>Area: {(statistics.area / 10000).toFixed(2)} ha</span>
          </div>
        </div>

        {errors.general && (
          <div className="form-error">
            <span className="error-message">{errors.general}</span>
          </div>
        )}

        <div className="form-actions">
          <button type="button" onClick={onCancel} className="cancel-button">
            Cancel
          </button>
          <button type="submit" className="submit-button">
            Create Run
          </button>
        </div>
      </form>
    </div>
  );
};

export default RunCreationForm;