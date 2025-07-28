const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Health check endpoint
  async healthCheck() {
    return this.request('/health');
  }

  // API test endpoint
  async apiTest() {
    return this.request('/api/test');
  }

  // Repository endpoints
  async getRepositories() {
    return this.request('/api/v1/repositories');
  }

  async addRepository(repoData: any) {
    return this.request('/api/v1/repositories', {
      method: 'POST',
      body: JSON.stringify(repoData),
    });
  }

  async updateRepositoryConfig(repoId: string, config: any) {
    return this.request(`/api/v1/repositories/${repoId}/config`, {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }

  // Feedback endpoints
  async getFeedback(filters?: any) {
    const params = filters ? `?${new URLSearchParams(filters)}` : '';
    return this.request(`/api/v1/feedback${params}`);
  }

  async approveFeedback(feedbackId: string) {
    return this.request(`/api/v1/feedback/${feedbackId}/approve`, {
      method: 'POST',
    });
  }

  async rejectFeedback(feedbackId: string, reason?: string) {
    return this.request(`/api/v1/feedback/${feedbackId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  async submitFeedback(feedback: any) {
    return this.request('/api/v1/feedback/submit', {
      method: 'POST',
      body: JSON.stringify(feedback),
    });
  }

  // Workflow endpoints
  async getWorkflows(filters?: any) {
    const params = filters ? `?${new URLSearchParams(filters)}` : '';
    return this.request(`/api/v1/workflows${params}`);
  }

  // Analytics endpoints
  async getDashboardAnalytics() {
    return this.request('/api/v1/analytics/dashboard');
  }

  // User endpoints
  async getUserProfile() {
    return this.request('/api/v1/users/me');
  }

  async updateUserProfile(profile: any) {
    return this.request('/api/v1/users/me', {
      method: 'PUT',
      body: JSON.stringify(profile),
    });
  }

  // GitHub API endpoints (using backend service with .env keys)
  async getRepositoryInfo(owner: string, repoName: string) {
    return this.request(`/api/v1/github/repository/${owner}/${repoName}`);
  }

  async searchRepositories(query: string, user?: string) {
    const params = new URLSearchParams({ query });
    if (user) params.append('user', user);
    return this.request(`/api/v1/github/search/repositories?${params}`);
  }

  async getRepositoryLanguages(owner: string, repoName: string) {
    return this.request(`/api/v1/github/repository/${owner}/${repoName}/languages`);
  }

  async getFileContent(owner: string, repoName: string, filePath: string, ref: string = 'main') {
    const params = new URLSearchParams({ ref });
    return this.request(`/api/v1/github/repository/${owner}/${repoName}/file?path=${encodeURIComponent(filePath)}&${params}`);
  }

  async getPullRequestFiles(owner: string, repoName: string, prNumber: number) {
    return this.request(`/api/v1/github/repository/${owner}/${repoName}/pull/${prNumber}/files`);
  }

  async createPullRequestComment(owner: string, repoName: string, prNumber: number, body: string) {
    return this.request(`/api/v1/github/repository/${owner}/${repoName}/pull/${prNumber}/comment`, {
      method: 'POST',
      body: JSON.stringify({ body }),
    });
  }
}

export const apiClient = new ApiClient();
export default apiClient;