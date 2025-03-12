import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate } from 'k6/metrics';
import { randomString, randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// Custom metrics
const errorRate = new Rate('errors');

// Default options
export const options = {
  vus: 50,              // Number of virtual users
  duration: '1m',       // Test duration
  thresholds: {
    http_req_duration: ['p(95)<1000'], // 95% of requests should be below 1s
    errors: ['rate<0.01'],             // Error rate should be less than 1%
  },
  stages: [
    { duration: '10s', target: 50 },   // Ramp-up to 50 users over 10 seconds
    { duration: '40s', target: 50 },   // Stay at 50 users for 40 seconds
    { duration: '10s', target: 0 },    // Ramp-down to 0 users over 10 seconds
  ],
};

// Get base URL from environment variable or use default
const BASE_URL = __ENV.BASE_URL || 'https://api-dev.example.com';

// Shared parameters
const THINK_TIME = parseFloat(__ENV.THINK_TIME || '1');

// Utility function to generate random user data
function generateUserData() {
  return {
    name: `Test User ${randomString(5)}`,
    email: `test.${randomString(8)}@example.com`,
    phone: `+1${randomIntBetween(2, 9)}${randomIntBetween(0, 9)}${randomString(8, '0123456789')}`,
  };
}

// Utility function to generate random product data
function generateProductData() {
  return {
    name: `Test Product ${randomString(5)}`,
    description: 'A test product created via performance tests',
    price: parseFloat((randomIntBetween(10, 200) + 0.99).toFixed(2)),
    category: 'test',
    stock: randomIntBetween(50, 500),
    sku: `TEST-${randomString(6, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')}`,
  };
}

// Utility function to generate random order data
function generateOrderData() {
  return {
    customer_id: randomIntBetween(100, 999),
    items: [
      {
        product_id: randomIntBetween(1, 10),
        quantity: randomIntBetween(1, 5),
        price: parseFloat((randomIntBetween(10, 100) + 0.99).toFixed(2)),
      },
      {
        product_id: randomIntBetween(11, 20),
        quantity: randomIntBetween(1, 3),
        price: parseFloat((randomIntBetween(20, 200) + 0.99).toFixed(2)),
      },
    ],
    shipping_address: {
      street: `${randomIntBetween(100, 999)} Main St`,
      city: 'Test City',
      state: 'TS',
      zip: randomString(5, '0123456789'),
      country: 'Test Country',
    },
  };
}

// Main test function
export default function() {
  let userId, productId, orderId;

  // Common headers
  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  // Users API tests
  group('Users API', () => {
    // GET All Users
    let getAllUsersResponse = http.get(`${BASE_URL}/users`, { headers });
    
    check(getAllUsersResponse, {
      'GET All Users status is 200': (r) => r.status === 200,
      'GET All Users has valid JSON response': (r) => r.json().length > 0,
    }) || errorRate.add(1);

    // GET User by ID
    let getUserResponse = http.get(`${BASE_URL}/users/1`, { headers });
    
    check(getUserResponse, {
      'GET User status is 200': (r) => r.status === 200,
      'GET User has correct ID': (r) => r.json().id === 1,
    }) || errorRate.add(1);

    // POST Create User
    let userData = generateUserData();
    let createUserResponse = http.post(
      `${BASE_URL}/users`,
      JSON.stringify(userData),
      { headers }
    );
    
    check(createUserResponse, {
      'POST Create User status is 201': (r) => r.status === 201,
      'POST Create User has valid ID': (r) => r.json().id !== undefined,
    }) || errorRate.add(1);

    if (createUserResponse.status === 201) {
      userId = createUserResponse.json().id;
    }

    sleep(THINK_TIME);
  });

  // Products API tests
  group('Products API', () => {
    // GET All Products
    let getAllProductsResponse = http.get(`${BASE_URL}/products`, { headers });
    
    check(getAllProductsResponse, {
      'GET All Products status is 200': (r) => r.status === 200,
      'GET All Products has valid JSON response': (r) => r.json().length > 0,
    }) || errorRate.add(1);

    if (getAllProductsResponse.status === 200 && getAllProductsResponse.json().length > 0) {
      productId = getAllProductsResponse.json()[0].id;
    }

    // GET Product by ID
    if (productId) {
      let getProductResponse = http.get(`${BASE_URL}/products/${productId}`, { headers });
      
      check(getProductResponse, {
        'GET Product status is 200': (r) => r.status === 200,
        'GET Product has correct ID': (r) => r.json().id === productId,
      }) || errorRate.add(1);
    }

    // GET Products by Category
    let getProductsByCategoryResponse = http.get(
      `${BASE_URL}/products?category=electronics`,
      { headers }
    );
    
    check(getProductsByCategoryResponse, {
      'GET Products by Category status is 200': (r) => r.status === 200,
      'GET Products by Category has valid category': (r) => 
        r.json().length > 0 && r.json()[0].category === 'electronics',
    }) || errorRate.add(1);

    // POST Create Product
    let productData = generateProductData();
    let createProductResponse = http.post(
      `${BASE_URL}/products`,
      JSON.stringify(productData),
      { headers }
    );
    
    check(createProductResponse, {
      'POST Create Product status is 201': (r) => r.status === 201,
      'POST Create Product has valid ID': (r) => r.json().id !== undefined,
    }) || errorRate.add(1);

    sleep(THINK_TIME);
  });

  // Orders API tests
  group('Orders API', () => {
    // GET All Orders
    let getAllOrdersResponse = http.get(`${BASE_URL}/orders`, { headers });
    
    check(getAllOrdersResponse, {
      'GET All Orders status is 200': (r) => r.status === 200,
      'GET All Orders has valid JSON response': (r) => r.json().length > 0,
    }) || errorRate.add(1);

    if (getAllOrdersResponse.status === 200 && getAllOrdersResponse.json().length > 0) {
      orderId = getAllOrdersResponse.json()[0].id;
    }

    // GET Order by ID
    if (orderId) {
      let getOrderResponse = http.get(`${BASE_URL}/orders/${orderId}`, { headers });
      
      check(getOrderResponse, {
        'GET Order status is 200': (r) => r.status === 200,
        'GET Order has correct ID': (r) => r.json().id === orderId,
      }) || errorRate.add(1);
    }

    // POST Create Order
    let orderData = generateOrderData();
    let createOrderResponse = http.post(
      `${BASE_URL}/orders`,
      JSON.stringify(orderData),
      { headers }
    );
    
    check(createOrderResponse, {
      'POST Create Order status is 201': (r) => r.status === 201,
      'POST Create Order has valid ID': (r) => r.json().id !== undefined,
    }) || errorRate.add(1);

    sleep(THINK_TIME);
  });
}
