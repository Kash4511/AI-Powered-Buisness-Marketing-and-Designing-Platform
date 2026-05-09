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

// Import local images for the modern template
import modernFront from '../../images/tmp1-front.png';
import modernBack from '../../images/temp1-back.png';

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
        
        let mapped: PDFTemplate[] = (data || []).map((t: any) => {
          const name = (t.name || '').toLowerCase();
          const id = (t.id || '').toLowerCase();
          const isModern = name.includes('modern') || id.startsWith('template');
          
          return {
            ...t,
            preview_url: isModern ? photoUrl : (t.preview_url || t.preview || t.thumbnail || t.image || null),
            hover_preview_url: isModern ? hoverTempUrl : (t.hover_preview_url || null),
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

  const renderTemplateThumbnail = (template: PDFTemplate, index: number) => {
    const name = template.name.toLowerCase();
    const id = template.id.toLowerCase();
    const isModernTemplate = name.includes('modern') || id.startsWith('template');
    const hasError = imageErrors[template.id];
    const isEager = index < 4;

    // Placeholder content for templates without images
    const renderPlaceholder = () => {
      let icon = <FileText size={48} />;
      let bgColor = 'linear-gradient(135deg, #3a3a3e 0%, #2a2a2e 100%)';

      return (
        <div className="template-placeholder" style={{ background: bgColor }}>
          {icon}
        </div>
      );
    };

    // Special case for the modern template to use local images with hover interaction
    if (isModernTemplate) {
      return (
        <div className="template-thumbnail-new">
          <img
            src={modernFront}
            alt={`${template.name} front`}
            className="image-primary"
            loading={isEager ? "eager" : "lazy"}
            onError={() => setImageErrors(prev => ({ ...prev, [template.id]: true }))}
          />
          <img
            src={modernBack}
            alt={`${template.name} back`}
            className="image-hover"
            loading="lazy"
            onError={() => setImageErrors(prev => ({ ...prev, [template.id]: true }))}
          />
        </div>
      );
    }

    if (hasError || !template.preview_url) {
      return renderPlaceholder();
    }

    return (
      <div className="template-thumbnail-new">
        <img
          src={template.preview_url}
          alt={template.name}
          className="image-primary"
          loading={isEager ? "eager" : "lazy"}
          onError={() => setImageErrors(prev => ({ ...prev, [template.id]: true }))}
        />
        {template.hover_preview_url && (
          <img
            src={template.hover_preview_url}
            alt={`${template.name} hover`}
            className="image-hover"
            loading="lazy"
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
          {templates.map((template, index) => (
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
                {renderTemplateThumbnail(template, index)}
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
