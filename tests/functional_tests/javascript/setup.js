// Mock the BaseApiClient
jest.mock('../../../core/clients/base_api_client', () => {
  return class MockBaseApiClient {
    constructor(baseUrl, headers = {}) {
      this.baseUrl = baseUrl;
      this.headers = headers;
      this.client = {
        defaults: {
          headers: headers
        }
      };
    }

    setAuthorization(type, token) {
      this.headers['Authorization'] = `${type} ${token}`;
    }

    clearAuthorization() {
      delete this.headers['Authorization'];
    }

    async get(endpoint, params = {}) {
      if (endpoint === '/orders') {
        return {
          status: 200,
          data: [
            {
              id: 'order1',
              customer_id: 'user123',
              items: [],
              total: 0,
              status: 'pending',
              created_at: '2023-01-01T00:00:00Z'
            }
          ],
          headers: { 'content-type': 'application/json' },
          config: { metadata: { responseTime: 50 } }
        };
      } else if (endpoint.startsWith('/orders/')) {
        const orderId = endpoint.split('/').pop();
        if (orderId === 'order1') {
          return {
            status: 200,
            data: {
              id: 'order1',
              customer_id: 'user123',
              items: [],
              total: 0,
              status: 'pending',
              created_at: '2023-01-01T00:00:00Z'
            },
            headers: { 'content-type': 'application/json' },
            config: { metadata: { responseTime: 50 } }
          };
        }
      }
      
      // Default 404 response
      const error = new Error('Not found');
      error.response = {
        status: 404,
        data: { error: 'Not found' },
        headers: { 'content-type': 'application/json' }
      };
      throw error;
    }

    async post(endpoint, data) {
      if (endpoint === '/orders') {
        return {
          status: 201,
          data: {
            id: 'order-new',
            customer_id: data.customer_id,
            items: data.items || [],
            total: (data.items || []).reduce((sum, item) => sum + (item.price * item.quantity), 0),
            status: 'pending',
            created_at: '2023-01-01T00:00:00Z'
          },
          headers: { 'content-type': 'application/json' }
        };
      }
      
      // Default 404 response
      const error = new Error('Not found');
      error.response = {
        status: 404,
        data: { error: 'Not found' },
        headers: { 'content-type': 'application/json' }
      };
      throw error;
    }

    async patch(endpoint, data) {
      if (endpoint.startsWith('/orders/')) {
        if (endpoint.endsWith('/cancel')) {
          return {
            status: 200,
            data: {
              id: 'order1',
              status: 'cancelled',
              cancellation_reason: data.cancellation_reason,
              cancelled_at: '2023-01-01T01:00:00Z'
            },
            headers: { 'content-type': 'application/json' }
          };
        } else {
          return {
            status: 200,
            data: {
              id: 'order1',
              status: data.status || 'pending',
              tracking_number: data.tracking_number,
              updated_at: '2023-01-01T01:00:00Z'
            },
            headers: { 'content-type': 'application/json' }
          };
        }
      }
      
      // Default 404 response
      const error = new Error('Not found');
      error.response = {
        status: 404,
        data: { error: 'Not found' },
        headers: { 'content-type': 'application/json' }
      };
      throw error;
    }

    async delete(endpoint) {
      return {
        status: 204,
        data: {},
        headers: {}
      };
    }
  };
});

// Mock the environment loader
jest.mock('../../../core/config/env_loader', () => ({
  getEnvironmentConfig: jest.fn().mockReturnValue({
    base_url: 'https://api-mock.example.com',
    auth: { type: 'oauth2' }
  }),
  getBaseUrl: jest.fn().mockReturnValue('https://api-mock.example.com')
}));

// Mock the allure reporter
jest.mock('../../../core/reporting/allure_reporter', () => ({
  startTest: jest.fn(),
  endTest: jest.fn(),
  addTag: jest.fn(),
  addSeverity: jest.fn(),
  addStep: jest.fn(),
  addApiRequest: jest.fn(),
  addApiResponse: jest.fn()
}));