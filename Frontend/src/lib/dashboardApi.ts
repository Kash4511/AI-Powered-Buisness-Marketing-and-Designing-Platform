import type { AxiosError } from 'axios';
import { apiClient } from './apiClient';

// Define the base URL for API requests
const API_BASE_URL = '/api';
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
      const errorData = err.response.data as { error?: string; details?: string };
      errorMessage = errorData.error || errorData.details || JSON.stringify(err.response.data);
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
      const response = await apiClient.get(`${API_BASE_URL}/dashboard/stats/`);
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
      const response = await apiClient.get(`${API_BASE_URL}/valid-choices/`);
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
      const response = await apiClient.get(`${API_BASE_URL}/templates/`);
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
      await apiClient.post(`${API_BASE_URL}/select-template/`, request);
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
      const response = await apiClient.post(`${API_BASE_URL}/create-lead-magnet/`, data);
      
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

      const response = await apiClient.post(`${API_BASE_URL}/create-lead-magnet/`, validatedData);
      
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
      
      const response = await apiClient.post(`${API_BASE_URL}/create-lead-magnet/`, data);
      
      console.log('✅ Lead magnet created successfully:', response.data);
      return response.data;
    } catch (error) {
      handleApiError(error, 'Creating lead magnet with data');
      throw error;
    }
  },

  // Firm profile
  getFirmProfile: async (): Promise<FirmProfile> => {
    try {
      const response = await apiClient.get(`${API_BASE_URL}/firm-profile/`);
      return response.data;
    } catch (error) {
      handleApiError(error, 'Fetching firm profile');
      throw error;
    }
  },

  updateFirmProfile: async (profileData: Partial<FirmProfile>): Promise<FirmProfile> => {
    try {
      const formData = new FormData();
      
      Object.entries(profileData).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (key === 'logo' && value instanceof File) {
            formData.append('logo', value);
          } else if (Array.isArray(value)) {
            // Ensure arrays (e.g., industry_specialties) are sent as valid JSON
            formData.append(key, JSON.stringify(value));
          } else if (key === 'firm_website' && typeof value === 'string') {
            // Normalize website to include protocol for URLField validation
            const trimmed = value.trim();
            const hasProtocol = /^https?:\/\//i.test(trimmed);
            const normalized = trimmed && !hasProtocol ? `https://${trimmed}` : trimmed;
            formData.append(key, normalized);
          } else if (key === 'work_email' && typeof value === 'string') {
            const normalizedEmail = value.trim();
            formData.append(key, normalizedEmail);
          } else {
            formData.append(key, String(value));
          }
        }
      });
      const response = await apiClient.patch(`${API_BASE_URL}/firm-profile/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      return response.data;
    } catch (error) {
      handleApiError(error, 'Updating firm profile');
      throw error;
    }
  },

  // Lead magnets - THIS GENERATES THE PDF
  generatePDFWithAI: async (request: { 
    template_id: string; 
    lead_magnet_id: number; 
    use_ai_content: boolean;
    user_answers?: Record<string, unknown>;
    architectural_images?: string[];
  }): Promise<void> => {
    if (pdfGenerationRunning) {
      return;
    }
    pdfGenerationRunning = true;
    try {
      const response = await apiClient.post(`${API_BASE_URL}/generate-pdf/`, request, {
        responseType: 'blob'
      });
      const pdfBlob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(pdfBlob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `lead-magnet-${request.lead_magnet_id}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      return;
    } catch (error) {
      const err = error as AxiosError;
      if (err.response && err.response.status === 409) {
        const poll = async (): Promise<string> => {
          const statusResp = await apiClient.get(`${API_BASE_URL}/generate-pdf/status/`, {
            params: { lead_magnet_id: request.lead_magnet_id }
          });
          const data = statusResp.data as { status?: string; pdf_url?: string; error?: string };
          
          if (data && data.status === 'ready' && data.pdf_url) {
            return data.pdf_url;
          }
          
          if (data && data.status === 'error') {
            throw new Error(data.error || 'PDF generation failed on the server');
          }
          
          return '';
        };
        const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
        let attempts = 0;
        const maxAttempts = 40;
        const intervalMs = 2500;
        while (attempts < maxAttempts) {
          const pdfUrl = await poll();
          if (pdfUrl) {
            // Ensure the URL is absolute
            let finalUrl = pdfUrl;
            if (!pdfUrl.startsWith('http') && apiClient.defaults.baseURL) {
              const base = apiClient.defaults.baseURL.replace(/\/$/, '');
              const path = pdfUrl.startsWith('/') ? pdfUrl : `/${pdfUrl}`;
              finalUrl = `${base}${path}`;
            }

            console.log('PDF generation complete, downloading from:', finalUrl);
            
            try {
              // Fetch the PDF using apiClient to include the Authorization header
              const pdfResponse = await apiClient.get(finalUrl, {
                responseType: 'blob'
              });
              
              const blob = new Blob([pdfResponse.data], { type: 'application/pdf' });
              const blobUrl = window.URL.createObjectURL(blob);
              
              // Trigger download
              const link = document.createElement('a');
              link.href = blobUrl;
              link.setAttribute('download', `lead-magnet-${request.lead_magnet_id}.pdf`);
              document.body.appendChild(link);
              link.click();
              
              // Cleanup
              document.body.removeChild(link);
              setTimeout(() => window.URL.revokeObjectURL(blobUrl), 100);
              return;
            } catch (downloadError) {
              console.error('Error downloading PDF with auth:', downloadError);
              // Fallback to window.open if blob download fails, though it might still 401
              window.open(finalUrl, '_blank');
              return;
            }
          }
          attempts += 1;
          await wait(intervalMs);
        }
        throw new Error('PDF generation did not complete in time');
      }
      handleApiError(error, 'Generating PDF with AI');
      throw error;
    } finally {
      pdfGenerationRunning = false;
    }
  },

  getGeneratePDFStatus: async (lead_magnet_id: number): Promise<{ status: string; pdf_url?: string }> => {
    const response = await apiClient.get(`${API_BASE_URL}/generate-pdf/status/`, {
      params: { lead_magnet_id }
    });
    return response.data;
  },

  // Lead magnets - Generate PDF and return a preview URL (no auto-download)
  generatePDFWithAIUrl: async (request: {
    template_id: string;
    lead_magnet_id: number;
    user_answers?: Record<string, unknown>;
    architectural_images?: string[];
  }): Promise<string> => {
    try {
      const response = await apiClient.post(`${API_BASE_URL}/generate-pdf/`, request, {
        responseType: 'blob'
      });
      
      // Success response (status 200), check if response is actually a PDF
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const arrayBuffer = await blob.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);
      
      // Check for PDF magic bytes: %PDF (first 4 bytes should be 0x25 0x50 0x44 0x46)
      if (uint8Array.length >= 4 && 
          uint8Array[0] === 0x25 && 
          uint8Array[1] === 0x50 && 
          uint8Array[2] === 0x44 && 
          uint8Array[3] === 0x46) {
        const url = window.URL.createObjectURL(blob);
        return url; // caller should revoke when done
      } else {
        // Response is not a PDF, likely an error message in JSON format
        const text = await blob.text();
        let errorData: { error?: string; details?: string };
        try {
          errorData = JSON.parse(text);
        } catch {
          errorData = { error: 'PDF generation failed', details: 'Response was not a valid PDF' };
        }
        throw new Error(
          `PDF generation failed: ${errorData.error || 'Unknown error'}\n` +
          `Details: ${errorData.details || 'No details available'}`
        );
      }
    } catch (error) {
      const err = error as AxiosError;
      if (err.response && err.response.status === 409) {
        return '';
      }
      if (error instanceof Error && error.message.includes('Generating PDF preview URL failed')) {
        throw error;
      }
      
      if (err.response && err.response.data instanceof Blob) {
        const blob = err.response.data as Blob;
        let text = '';
        let parseError: Error | null = null;
        
        try {
          text = await blob.text();
        } catch (textError) {
          parseError = textError as Error;
          console.error('Generating PDF preview URL - Error reading blob as text:', textError);
        }
        
        if (text) {
          // Try to parse as JSON
          let errorData: { error?: string; details?: string; message?: string } | null = null;
          let errorMessage = 'Unknown error';
          let errorDetails = '';
          
          try {
            errorData = JSON.parse(text);
            // Extract error message from various possible fields
            if (errorData) {
              errorMessage = errorData.error || errorData.message || 'PDF generation failed';
              errorDetails = errorData.details || '';
            } else {
              errorMessage = text || 'PDF generation failed';
              errorDetails = 'Could not parse error response as JSON';
            }
          } catch {
            // If JSON parsing fails, use the raw text
            errorData = null;
            errorMessage = text || 'PDF generation failed';
            errorDetails = 'Could not parse error response as JSON';
          }
          
          // Build the full error message
          const fullErrorMessage = errorDetails 
            ? `${errorMessage}\nDetails: ${errorDetails}`
            : errorMessage;
          
          console.error('Generating PDF preview URL - Server Error:', {
            status: err.response.status,
            statusText: err.response.statusText,
            error: errorMessage,
            details: errorDetails,
            rawText: text.length > 200 ? text.substring(0, 200) + '...' : text
          });
          
          throw new Error(
            `Generating PDF preview URL failed: ${err.response.status} ${err.response.statusText}\n` +
            `${fullErrorMessage}`
          );
        } else {
          // Could not read blob text
          const status = err.response?.status || 500;
          const statusText = err.response?.statusText || 'Internal Server Error';
          console.error('Generating PDF preview URL - Could not read error blob:', parseError);
          throw new Error(
            `Generating PDF preview URL failed: ${status} ${statusText}\n` +
            `Details: Unable to read server error response. Please check server logs.`
          );
        }
      } else {
        if (err.response) {
          const status = err.response.status;
          if (status >= 500) {
            throw new Error('Server error, try again later');
          }
          const data = err.response.data as { error?: string; details?: string };
          const msg = (data && (data.error || data.details)) || `${status} Error`;
          throw new Error(msg);
        }
        handleApiError(error, 'Generating PDF preview URL');
        throw error;
      }
    }
  },

  generateSlogan: async (request: {
    user_answers: Record<string, unknown>;
    firm_profile: Record<string, unknown>;
  }): Promise<{ slogan: string }> => {
    try {
      const response = await apiClient.post(`${API_BASE_URL}/generate-slogan/`, request);
      return response.data;
    } catch (error) {
      handleApiError(error, 'Generating slogan');
      throw error;
    }
  },

  // Brand assets PDF preview
  generateBrandAssetsPDFPreview: async (): Promise<string> => {
    try {
      const response = await apiClient.post(`${API_BASE_URL}/brand-assets/preview-pdf/`, {}, {
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
      const response = await apiClient.get(`${API_BASE_URL}/lead-magnets/`);
      return response.data;
    } catch (error) {
      handleApiError(error, 'Fetching lead magnets');
      throw error;
    }
  },

  getLeadMagnet: async (id: number): Promise<LeadMagnet> => {
    try {
      const response = await apiClient.get(`${API_BASE_URL}/lead-magnets/${id}/`);
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
      const response = await apiClient.post(`${API_BASE_URL}/create-lead-magnet/`, testData);
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
      await apiClient.delete(`${API_BASE_URL}/lead-magnets/${id}/`);
    } catch (error) {
      handleApiError(error, `Deleting lead magnet ${id}`);
    }
  }
};
