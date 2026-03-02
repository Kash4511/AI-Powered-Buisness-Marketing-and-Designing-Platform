import type { AxiosError } from 'axios';
import { apiClient } from './apiClient';

let pdfGenerationRunning = false;

// Define types with valid choices
export interface FirmProfile {
  id?: number;
  firm_name: string;
  work_email: string;
  phone_number: string;
  firm_website: string;
  firm_size: string;
  industry_specialties: string[];
  location: string;
  primary_brand_color: string;
  secondary_brand_color: string;
  preferred_font_style: string;
  branding_guidelines: string;
  logo?: File | null;
}

export interface DashboardStats {
  total_lead_magnets: number;
  active_lead_magnets: number;
  total_downloads: number;
  leads_generated: number;
}

export interface LeadMagnet {
  id: number;
  title: string;
  description: string;
  status: string;
  created_at: string;
  downloads_count: number;
  leads_count: number;
}

// Define type for Lead Magnet generation form
export interface LeadMagnetGeneration {
  lead_magnet_type: string;
  main_topic: string;
  target_audience: string[];
  audience_pain_points: string[];
  desired_outcome: string;
  call_to_action: string;
  special_requests?: string;
}

// Define types for templates
export interface PDFTemplate {
  id: string;
  name: string;
  description?: string;
  preview_url?: string;
  // Optional secondary image used for hover preview in selection UI
  hover_preview_url?: string;
  thumbnail?: string;
  secondary_preview_url?: string;
}

export interface CreateLeadMagnetRequest {
  title: string;
  description?: string;
  firm_profile?: number | Partial<FirmProfile>;
  generation_data: LeadMagnetGeneration;
  template_type?: string;
  status?: string;
}

export interface TemplateSelectionRequest {
  lead_magnet_id: number;
  template_id: string;
  template_name: string;
  template_thumbnail?: string;
  captured_answers?: Record<string, unknown>;
  source?: string;
}

// Enhanced error handler
const handleApiError = (error: unknown, context: string) => {
  const err = error as AxiosError;
  if (err.response) {
    console.error(`${context} - Server Error:`, {
      status: err.response.status,
      statusText: err.response.statusText,
      data: err.response.data,
      headers: err.response.headers,
      url: err.response.config?.url
    });
    
    // Handle blob error responses (for PDF generation errors)
    let errorMessage: string;
    if (err.response.data instanceof Blob) {
      errorMessage = 'PDF generation failed. Check server logs for details.';
    } else if (typeof err.response.data === 'object' && err.response.data !== null) {
      const errorData = err.response.data as { error?: string; details?: any };
      const detailsStr = errorData.details ? JSON.stringify(errorData.details) : '';
      errorMessage = `${errorData.error || 'Validation error'} ${detailsStr}`.trim();
    } else {
      errorMessage = String(err.response.data || 'Unknown error');
    }
    
    throw new Error(
      `${context} failed: ${err.response.status} ${err.response.statusText}\n` +
      `Details: ${errorMessage}`
    );
  } else if (Object.prototype.hasOwnProperty.call(error as object, 'request')) {
    const reqErr = error as { request?: unknown; code?: string; config?: { timeout?: number } };
    if (reqErr.code === 'ECONNABORTED') {
      console.error(`${context} - Timeout after ${reqErr.config?.timeout}ms`);
      throw new Error(`${context} failed: Request timed out after ${reqErr.config?.timeout || 30000}ms. The server may still be processing. Please wait a moment and retry.`);
    }
    if (typeof navigator !== 'undefined' && navigator && navigator.onLine === false) {
      console.error(`${context} - Offline: Browser appears offline`);
      throw new Error(`${context} failed: You appear to be offline. Check your network connection.`);
    }
    console.error(`${context} - No Response:`, reqErr.request);
    throw new Error(`${context} failed: No response from server`);
  } else {
    console.error(`${context} - Request Error:`, (err as Error).message);
    throw new Error(`${context} failed: ${(err as Error).message}`);
  }
};

// API functions
export const dashboardApi = {
  // Dashboard stats
  getStats: async (): Promise<DashboardStats> => {
    try {
      const response = await apiClient.get('/api/dashboard/stats/');
      return response.data;
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
      return {
        total_lead_magnets: 0,
        active_lead_magnets: 0,
        total_downloads: 0,
        leads_generated: 0
      };
    }
  },
  
  // Get valid choices from server
  getValidChoices: async (): Promise<{lead_magnet_types: string[], main_topics: string[]}> => {
    try {
      const response = await apiClient.get('/api/valid-choices/');
      return response.data;
    } catch {
      console.log('Valid choices endpoint not available, using discovered choices');
      return {
        lead_magnet_types: ['CHECKLIST', 'CHEATSHEET', 'GUIDE', 'TEMPLATE'],
        main_topics: ['FINANCE', 'MARKETING', 'TECHNOLOGY', 'HEALTH', 'EDUCATION']
      };
    }
  },
  
  // Templates - FIXED VERSION
  getTemplates: async (): Promise<PDFTemplate[]> => {
    try {
      const response = await apiClient.get('/api/templates/');
      // Handle different response structures
      if (response.data.templates) {
        return response.data.templates;
      } else if (Array.isArray(response.data)) {
        return response.data;
      } else {
        return [];
      }
    } catch (error: unknown) {
      console.error('Error fetching templates:', error);
      // Return empty array instead of throwing if you want to handle gracefully
      return [];
    }
  },
  
  selectTemplate: async (request: TemplateSelectionRequest): Promise<void> => {
    try {
      await apiClient.post('/api/select-template/', request);
    } catch (error) {
      handleApiError(error, 'Selecting template');
    }
  },
  
  // Create lead magnet with comprehensive error handling
  createLeadMagnet: async (data: CreateLeadMagnetRequest): Promise<LeadMagnet> => {
    try {
      console.log('🚀 Sending lead magnet data:', JSON.stringify(data, null, 2));
      
      // Validate required fields
      if (!data.title || !data.generation_data) {
        throw new Error('Title and generation_data are required');
      }
      const response = await apiClient.post('/api/create-lead-magnet/', data);
      
      console.log('✅ Lead magnet created successfully:', response.data);
      return response.data;
    } catch (error) {
      handleApiError(error, 'Creating lead magnet');
      throw error;
    }
  },

  // Create lead magnet with validated choices
  createLeadMagnetWithValidData: async (data: { 
    title: string; 
    description?: string; 
    firm_profile?: number | Partial<FirmProfile>; 
    generation_data: LeadMagnetGeneration;
  }): Promise<LeadMagnet> => {
    try {
      console.log('🚀 Creating lead magnet with validated data...');
      
      // Convert to uppercase as Django choices are often uppercase
      const validatedData = {
        title: data.title,
        description: data.description || '',
        firm_profile: data.firm_profile || null,
        generation_data: {
          ...data.generation_data,
          lead_magnet_type: data.generation_data.lead_magnet_type.toUpperCase(),
          main_topic: data.generation_data.main_topic.toUpperCase()
        },
        template_type: 'GUIDE',
        status: 'DRAFT'
      };

      console.log('📤 Sending validated data:', JSON.stringify(validatedData, null, 2));

      const response = await apiClient.post('/api/create-lead-magnet/', validatedData);
      
      console.log('✅ Lead magnet created successfully:', response.data);
      return response.data;
    } catch (error) {
      handleApiError(error, 'Creating lead magnet with validated data');
      throw error;
    }
  },

  // Add missing function used by CreateLeadMagnet.tsx
  createLeadMagnetWithData: async (data: { 
    title: string; 
    description?: string; 
    firm_profile?: number | Partial<FirmProfile>; 
    generation_data: LeadMagnetGeneration; 
  }): Promise<LeadMagnet> => {
    try {
      console.log('🚀 Creating lead magnet with data:', JSON.stringify(data, null, 2));
      
      const response = await apiClient.post('/api/create-lead-magnet/', data);
      
      console.log('✅ Lead magnet created successfully:', response.data);
      return response.data;
    } catch (error) {
      handleApiError(error, 'Creating lead magnet with data');
      throw error;
    }
  },

  // Firm profile
  getFirmProfile: async (): Promise<FirmProfile | null> => {
    try {
      const response = await apiClient.get('/api/firm-profile/');
      return response.data;
    } catch (error) {
      console.error('Error fetching firm profile:', error);
      return null;
    }
  },

  updateFirmProfile: async (data: Partial<FirmProfile>): Promise<FirmProfile> => {
    try {
      const formData = new FormData();
      Object.entries(data).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (key === 'industry_specialties' && Array.isArray(value)) {
            value.forEach(v => formData.append('industry_specialties', v));
          } else if (key === 'logo') {
            if (value instanceof File) {
              formData.append('logo', value);
            }
            // Skip if logo is a string (URL) or anything else
          } else if (key === 'preferred_cover_image') {
            if (value instanceof File) {
              formData.append('preferred_cover_image', value);
            }
            // Skip if it's a string (URL)
          } else {
            formData.append(key, String(value));
          }
        }
      });
      const response = await apiClient.patch('/api/firm-profile/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      handleApiError(error, 'Updating firm profile');
      throw error;
    }
  },

  // Lead magnets - ASYNC JOB PATTERN
  generatePDFWithAI: async (data: { 
    template_id: string; 
    lead_magnet_id: number; 
    use_ai_content: boolean;
    user_answers?: Record<string, unknown>;
    architectural_images?: string[];
  }): Promise<void> => {
    if (pdfGenerationRunning) return;
    pdfGenerationRunning = true;
    
    try {
      // 1. Start the job
      const startRes = await apiClient.post('/api/generate-pdf/start/', data);
      const { job_id } = startRes.data;

      // 2. Poll for status
      const pdf_url = await (async () => { 
          const deadline = Date.now() + 180000; // 3 minutes
          while (Date.now() < deadline) { 
              await new Promise(r => setTimeout(r, 3000)); 
              const jobRes = await apiClient.get(`/api/generate-pdf/status/${job_id}/`);
              const job = jobRes.data;
              
              console.log(`PDF ${job.progress}% — ${job.message}`); 
              
              if (job.status === 'complete') return job.pdf_url; 
              if (job.status === 'failed')   throw new Error(job.error || 'Generation failed'); 
          } 
          throw new Error('PDF generation timed out'); 
      })(); 

      // 3. Download the result
      if (pdf_url) {
        try {
          // If it's a relative path starting with /api or /media, download it using apiClient
          // to ensure we send the Authorization header and use the correct base URL.
          const isRelative = pdf_url.startsWith('/') || !pdf_url.startsWith('http');
          
          if (isRelative) {
            const downloadRes = await apiClient.get(pdf_url, { responseType: 'blob' });
            const blob = new Blob([downloadRes.data], { type: 'application/pdf' });
            const url = window.URL.createObjectURL(blob);
            
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `lead-magnet-${data.lead_magnet_id}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
          } else {
            // If it's an absolute URL (like Cloudinary), try direct download
            const link = document.createElement('a');
            link.href = pdf_url;
            link.setAttribute('download', `lead-magnet-${data.lead_magnet_id}.pdf`);
            link.setAttribute('target', '_blank'); // Open in new tab if download fails
            document.body.appendChild(link);
            link.click();
            link.remove();
          }
        } catch (downloadErr) {
          console.error('Failed to trigger PDF download:', downloadErr);
          // Fallback to direct navigation if Axios download fails
          window.open(pdf_url, '_blank');
        }
      }
    } catch (error) {
      handleApiError(error, 'Generating PDF with AI');
      throw error;
    } finally {
      pdfGenerationRunning = false;
    }
  },

  getGeneratePDFStatus: async (job_id: string): Promise<{ 
    status: string; 
    progress: number; 
    message: string; 
    pdf_url?: string; 
    error?: string; 
  }> => {
    try {
      const response = await apiClient.get(`/api/generate-pdf/status/${job_id}/`);
      return response.data;
    } catch (error) {
      handleApiError(error, 'Fetching PDF status');
      throw error;
    }
  },

  generateSlogan: async (request: {
    user_answers: Record<string, unknown>;
    firm_profile: Record<string, unknown>;
  }): Promise<{ slogan: string }> => {
    try {
      const response = await apiClient.post('/api/generate-slogan/', request);
      return response.data;
    } catch (error) {
      handleApiError(error, 'Generating slogan');
      throw error;
    }
  },

  // Brand assets PDF preview
  generateBrandAssetsPDFPreview: async (): Promise<string> => {
    try {
      const response = await apiClient.post('/api/brand-assets/preview-pdf/', {}, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      return url; // caller should revoke when done
    } catch (error) {
      handleApiError(error, 'Generating brand assets PDF preview');
      throw error;
    }
  },

  getLeadMagnets: async (): Promise<LeadMagnet[]> => {
    try {
      const response = await apiClient.get('/api/lead-magnets/');
      return response.data;
    } catch (error) {
      console.error('Error fetching lead magnets:', error);
      return [];
    }
  },

  getLeadMagnetById: async (id: number): Promise<LeadMagnet> => {
    try {
      const response = await apiClient.get(`/api/lead-magnets/${id}/`);
      return response.data;
    } catch (error) {
      handleApiError(error, `Fetching lead magnet ${id}`);
      throw error;
    }
  },

  // Test function with valid choices
  testCreateLeadMagnet: async (): Promise<LeadMagnet> => {
    const testData = {
      title: "Test Lead Magnet - " + Date.now(),
      description: "This is a test lead magnet",
      generation_data: {
        lead_magnet_type: "GUIDE",
        main_topic: "MARKETING",
        target_audience: ["small business owners", "entrepreneurs"],
        audience_pain_points: ["lack of online presence", "difficulty generating leads"],
        desired_outcome: "increase online visibility and generate more leads",
        call_to_action: "Download our free guide to boost your online presence",
        special_requests: "Please make it professional and easy to understand"
      }
    };

    try {
      console.log('🧪 Testing lead magnet creation with valid choices:', testData);
      const response = await apiClient.post('/api/create-lead-magnet/', testData);
      console.log('✅ Test successful:', response.data);
      return response.data;
    } catch (error) {
      handleApiError(error, 'Testing lead magnet creation');
      throw error;
    }
  },

  // Complete workflow: Create lead magnet -> Select template -> Generate PDF
  createAndGeneratePDF: async (leadMagnetData: { title: string; generation_data: LeadMagnetGeneration }, templateId: string): Promise<void> => {
    try {
      // Step 1: Create lead magnet
      console.log('📝 Step 1: Creating lead magnet...');
      const leadMagnet = await dashboardApi.createLeadMagnetWithValidData(leadMagnetData);
      
      // Step 2: Select template
      console.log('🎨 Step 2: Selecting template...');
      await dashboardApi.selectTemplate({
        lead_magnet_id: leadMagnet.id,
        template_id: templateId,
        template_name: 'Selected Template'
      });
      
      // Step 3: Generate PDF
      console.log('📄 Step 3: Generating PDF...');
      await dashboardApi.generatePDFWithAI({
        template_id: templateId,
        lead_magnet_id: leadMagnet.id,
        use_ai_content: true
      });
      
      console.log('✅ Complete workflow finished successfully!');
      return;
    } catch (error) {
      console.error('❌ Workflow failed:', error);
      throw error;
    }
  },

  // Delete lead magnet
  deleteLeadMagnet: async (id: number): Promise<void> => {
    try {
      await apiClient.delete(`/api/lead-magnets/${id}/`);
    } catch (error) {
      handleApiError(error, `Deleting lead magnet ${id}`);
      throw error;
    }
  }
};
