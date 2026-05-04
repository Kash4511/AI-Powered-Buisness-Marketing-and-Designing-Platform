import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FileText, Loader2, AlertCircle, ChevronLeft, CheckCircle } from 'lucide-react';
import { dashboardApi } from '../../lib/dashboardApi';
import { apiClient } from '../../lib/apiClient';
import type { PDFTemplate } from '../../lib/dashboardApi';
import ImageUpload from './ImageUpload';
import './TemplateSelectionForm.css';
import '../CreateLeadMagnet.css';
import Modal from '../Modal';

interface TemplateSelectionFormProps {
  onClose: () => void;
  onSubmit: (templateId: string, templateName: string, architecturalImages?: File[]) => void;
  loading?: boolean;
}

const TemplateSelectionForm: React.FC<TemplateSelectionFormProps> = ({
  onClose,
  onSubmit,
  loading = false,
}) => {
  const [templates, setTemplates] = useState<PDFTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<PDFTemplate | null>(null);
  const [fetchingTemplates, setFetchingTemplates] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showImageUpload, setShowImageUpload] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [imageErrors, setImageErrors] = useState<Record<string, boolean>>({});
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewTemplate, setPreviewTemplate] = useState<PDFTemplate | null>(null);

  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        setFetchingTemplates(true);
        setError(null);
        const data = await dashboardApi.getTemplates();
        
        const baseUrl = String(apiClient.defaults.baseURL || '').replace(/\/$/, '');
        const photoUrl = `${baseUrl}/media/photo.png`;
        const hoverTempUrl = `${baseUrl}/media/tempphoto1.png`;
        
        const mapped: PDFTemplate[] = (data || []).map((t: any) => {
          const name = (t.name || '').toLowerCase();
          const isTemplate1 = name.includes('modern') || name.includes('template 1');
          
          return {
            ...t,
            preview_url: isTemplate1 ? photoUrl : (t.preview_url || t.preview || t.thumbnail || t.image || null),
            hover_preview_url: isTemplate1 ? hoverTempUrl : (t.hover_preview_url || null),
            secondary_preview_url: t.secondary_preview_url || t.image2 || t.hover_preview_url || null,
          };
        });
        
        setTemplates(mapped);
      } catch (err: unknown) {
        console.error('Failed to fetch templates:', err);
        setError('Failed to load templates. Please check your connection.');
      } finally {
        setFetchingTemplates(false);
      }
    };

    fetchTemplates();
  }, []);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null;
    if (loading) {
      setElapsed(0);
      timer = setInterval(() => setElapsed(s => s + 1), 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [loading]);

  const handleTemplateSelect = (template: PDFTemplate) => {
    setSelectedTemplate(template);
  };

  const handleImagesSelected = (images: File[]) => {
    setShowImageUpload(false);
    if (selectedTemplate) {
      onSubmit(selectedTemplate.id, selectedTemplate.name, images);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTemplate) {
      setError('Please select a template before continuing');
      return;
    }
    setShowImageUpload(true);
  };

  const renderTemplateThumbnail = (template: PDFTemplate) => {
    const isTemplate1 = template.name.toLowerCase().includes('modern') || template.name.toLowerCase().includes('template 1');
    const hasError = imageErrors[template.id];

    if (hasError || !template.preview_url) {
      return (
        <div className="template-placeholder">
          <FileText size={48} />
        </div>
      );
    }

    if (isTemplate1 && template.secondary_preview_url) {
      return (
        <div className="template-thumbnail-new template-dual-preview">
          <img
            src={template.preview_url}
            alt={template.name}
            className="dual-image-left"
            onError={() => setImageErrors(prev => ({ ...prev, [template.id]: true }))}
          />
          <img
            src={template.secondary_preview_url}
            alt={`${template.name} secondary`}
            className="dual-image-right"
            onError={() => setImageErrors(prev => ({ ...prev, [template.id]: true }))}
          />
        </div>
      );
    }

    return (
      <div className="template-thumbnail-new">
        <img
          src={template.preview_url}
          alt={template.name}
          className="image-primary"
          onError={() => setImageErrors(prev => ({ ...prev, [template.id]: true }))}
        />
        {template.hover_preview_url && (
          <img
            src={template.hover_preview_url}
            alt={`${template.name} hover`}
            className="image-hover"
            onError={() => setImageErrors(prev => ({ ...prev, [template.id]: true }))}
          />
        )}
      </div>
    );
  };

  if (fetchingTemplates) {
    return (
      <div className="template-loading">
        <Loader2 className="spinner" size={48} />
        <p>Loading templates...</p>
      </div>
    );
  }

  if (error && templates.length === 0) {
    return (
      <div className="template-error">
        <AlertCircle size={48} />
        <h3>Error</h3>
        <p>{error}</p>
        <button className="retry-btn" onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  if (showImageUpload) {
    return (
      <ImageUpload 
        onImagesSelected={handleImagesSelected} 
        onClose={() => setShowImageUpload(false)} 
      />
    );
  }

  return (
    <>
      <div className="template-selection-container">
        <div className="form-header-new">
          <button onClick={onClose} className="back-button-new">
            <ChevronLeft size={24} />
            <span>Back</span>
          </button>
        </div>

        <div className="template-grid-new">
          {templates.map((template) => (
            <motion.div
              key={template.id}
              className={`template-card ${selectedTemplate?.id === template.id ? 'selected' : ''}`}
              onClick={() => handleTemplateSelect(template)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              {selectedTemplate?.id === template.id && (
                <div className="selected-check">
                  <CheckCircle size={18} />
                </div>
              )}
              <div className="template-thumbnail-wrapper-new">
                {renderTemplateThumbnail(template)}
              </div>
              <div className="template-info-new">
                <h3>{template.name}</h3>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="form-actions-new">
          <button 
            type="button" 
            onClick={handleSubmit}
            className="submit-btn-new"
            disabled={!selectedTemplate || loading}
          >
            {loading ? (
              <><Loader2 className="spinner" size={18} /> Processing... ({elapsed}s)</>
            ) : (
              'Next'
            )}
          </button>
        </div>
      </div>

      {loading && (
        <div className="template-loading-overlay">
          <div className="overlay-content">
            <Loader2 className="spinner" size={32} />
            <p>Creating lead magnet… this can take up to 30s.</p>
            <p>Elapsed: {elapsed}s</p>
          </div>
        </div>
      )}
    </>
  );
};

export default TemplateSelectionForm;
