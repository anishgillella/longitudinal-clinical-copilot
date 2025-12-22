// API client for backend communication

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  // Health
  async healthCheck() {
    return this.request<{ status: string }>('/health');
  }

  // Clinicians
  async getClinicians() {
    return this.request<any[]>('/api/v1/clinicians');
  }

  async getClinician(id: string) {
    return this.request<any>(`/api/v1/clinicians/${id}`);
  }

  async createClinician(data: any) {
    return this.request<any>('/api/v1/clinicians', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Patients
  async getPatients(clinicianId?: string) {
    const params = clinicianId ? `?clinician_id=${clinicianId}` : '';
    return this.request<any[]>(`/api/v1/patients${params}`);
  }

  async getPatient(id: string) {
    return this.request<any>(`/api/v1/patients/${id}`);
  }

  async createPatient(data: any) {
    return this.request<any>('/api/v1/patients', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updatePatient(id: string, data: any) {
    return this.request<any>(`/api/v1/patients/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deletePatient(id: string) {
    return this.request<any>(`/api/v1/patients/${id}`, {
      method: 'DELETE',
    });
  }

  // Patient History
  async getPatientHistory(patientId: string) {
    return this.request<any[]>(`/api/v1/patients/${patientId}/history`);
  }

  async addPatientHistory(patientId: string, data: any) {
    return this.request<any>(`/api/v1/patients/${patientId}/history`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Sessions
  async getSessions(patientId?: string) {
    const params = patientId ? `?patient_id=${patientId}` : '';
    return this.request<any[]>(`/api/v1/sessions${params}`);
  }

  async getSession(id: string) {
    return this.request<any>(`/api/v1/sessions/${id}`);
  }

  async createSession(data: any) {
    return this.request<any>('/api/v1/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getSessionTranscripts(sessionId: string) {
    return this.request<any[]>(`/api/v1/sessions/${sessionId}/transcripts`);
  }

  // Assessment
  async getPatientAssessment(patientId: string) {
    return this.request<any>(`/api/v1/assessment/patients/${patientId}`);
  }

  async getPatientHypotheses(patientId: string) {
    return this.request<any[]>(`/api/v1/assessment/patients/${patientId}/hypotheses`);
  }

  async getPatientProgress(patientId: string) {
    return this.request<any>(`/api/v1/assessment/patients/${patientId}/progress`);
  }

  // Analytics
  async getDashboardMetrics(clinicianId: string) {
    return this.request<any>(`/api/v1/analytics/dashboard/${clinicianId}`);
  }

  async getPatientTimeline(patientId: string) {
    return this.request<any[]>(`/api/v1/memory/patients/${patientId}/timeline`);
  }
}

export const api = new ApiClient(API_BASE_URL);
