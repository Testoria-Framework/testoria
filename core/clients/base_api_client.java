package core.clients;

import io.restassured.RestAssured;
import io.restassured.response.Response;
import io.restassured.specification.RequestSpecification;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;

/**
 * Base API client for making HTTP requests to REST APIs.
 * Provides common functionality for all API interactions using RestAssured.
 */
public class BaseApiClient {
    private static final Logger logger = LoggerFactory.getLogger(BaseApiClient.class);
    
    private final String baseUrl;
    private final RequestSpecification requestSpec;
    private Response lastResponse;
    
    /**
     * Initialize the BaseApiClient with base URL and optional default headers.
     *
     * @param baseUrl The base URL for the API (e.g., https://api.example.com)
     */
    public BaseApiClient(String baseUrl) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.requestSpec = RestAssured.given();
        this.requestSpec.baseUri(this.baseUrl);
    }
    
    /**
     * Initialize the BaseApiClient with base URL and default headers.
     *
     * @param baseUrl The base URL for the API (e.g., https://api.example.com)
     * @param headers Default headers to include in all requests
     */
    public BaseApiClient(String baseUrl, Map<String, String> headers) {
        this(baseUrl);
        if (headers != null) {
            this.requestSpec.headers(headers);
        }
    }
    
    /**
     * Build the full endpoint URL, handling slashes correctly.
     *
     * @param endpoint The API endpoint
     * @return The complete endpoint path
     */
    private String buildEndpointPath(String endpoint) {
        return endpoint.startsWith("/") ? endpoint : "/" + endpoint;
    }
    
    /**
     * Log request information.
     *
     * @param method   HTTP method
     * @param endpoint Request endpoint
     */
    private void logRequest(String method, String endpoint) {
        logger.info("Making {} request to {}{}", method, baseUrl, buildEndpointPath(endpoint));
    }
    
    /**
     * Send a GET request to the specified API endpoint.
     *
     * @param endpoint The API endpoint to call (will be appended to baseUrl)
     * @return The Response object
     */
    public Response get(String endpoint) {
        logRequest("GET", endpoint);
        lastResponse = requestSpec.get(buildEndpointPath(endpoint));
        logger.debug("Response status code: {}", lastResponse.getStatusCode());
        return lastResponse;
    }
    
    /**
     * Send a GET request to the specified API endpoint with query parameters.
     *
     * @param endpoint The API endpoint to call (will be appended to baseUrl)
     * @param params   Query parameters
     * @return The Response object
     */
    public Response get(String endpoint, Map<String, ?> params) {
        logRequest("GET", endpoint);
        lastResponse = requestSpec.params(params).get(buildEndpointPath(endpoint));
        logger.debug("Response status code: {}", lastResponse.getStatusCode());
        return lastResponse;
    }
    
    /**
     * Send a GET request to the specified API endpoint with query parameters and headers.
     *
     * @param endpoint The API endpoint to call (will be appended to baseUrl)
     * @param params   Query parameters
     * @param headers  Request headers
     * @return The Response object
     */
    public Response get(String endpoint, Map<String, ?> params, Map<String, String> headers) {
        logRequest("GET", endpoint);
        lastResponse = requestSpec.params(params).headers(headers).get(buildEndpointPath(endpoint));
        logger.debug("Response status code: {}", lastResponse.getStatusCode());
        return lastResponse;
    }
    
    /**
     * Send a POST request to the specified API endpoint.
     *
     * @param endpoint The API endpoint to call (will be appended to baseUrl)
     * @return The Response object
     */
    public Response post(String endpoint) {
        logRequest("POST", endpoint);
        lastResponse = requestSpec.post(buildEndpointPath(endpoint));
        logger.debug("Response status code: {}", lastResponse.getStatusCode());
        return lastResponse;
    }
    
    /**
     * Send a POST request to the specified API endpoint with a JSON body.
     *
     * @param endpoint The API endpoint to call (will be appended to baseUrl)
     * @param body     The JSON body as a JSONObject
     * @return The Response object
     */
    public Response post(String endpoint, JSONObject body) {
        logRequest("POST", endpoint);
        lastResponse = requestSpec.body(body.toString()).post(buildEndpointPath(endpoint));
        logger.debug("Response status code: {}", lastResponse.getStatusCode());
        return lastResponse;
    }
    
    /**
     * Send a POST request to the specified API endpoint with a JSON body and headers.
     *
     * @param endpoint The API endpoint to call (will be appended to baseUrl)
     * @param body     The JSON body as a JSONObject
     * @param headers  Request headers
     * @return The Response object
     */
    public Response post(String endpoint, JSONObject body, Map<String, String> headers) {
        logRequest("POST", endpoint);
        lastResponse = requestSpec.body(body.toString()).headers(headers).post(buildEndpointPath(endpoint));
        logger.debug("Response status code: {}", lastResponse.getStatusCode());
        return lastResponse;
    }
    
    /**
     * Send a PUT request to the specified API endpoint.
     *
     * @param endpoint The API endpoint to call (will be appended to baseUrl)
     * @return The Response object
     */
    public Response put(String endpoint) {
        logRequest("PUT", endpoint);
        lastResponse = requestSpec.put(buildEndpointPath(endpoint));
        logger.debug("Response status code: {}", lastResponse.getStatusCode());
        return lastResponse;
    }
    
    /**
     * Send a PUT request to the specified API endpoint with a JSON body.
     *
     * @param endpoint The API endpoint to call (will be appended to baseUrl)
     * @param body     The JSON body as a JSONObject
     * @return The Response object
     */
    public Response put(String endpoint, JSONObject body) {
        logRequest("PUT", endpoint);
        lastResponse = requestSpec.body(body.toString()).put(buildEndpointPath(endpoint));
        logger.debug("Response status code: {}", lastResponse.getStatusCode());
        return lastResponse;
    }
    
    /**
     * Send a PUT request to the specified API endpoint with a JSON body and headers.
     *
     * @param endpoint The API endpoint to call (will be appended to baseUrl)
     * @param body     The JSON body as a JSONObject
     * @param headers  Request headers
     * @return The Response object
     */
    public Response put(String endpoint, JSONObject body, Map<String, String> headers) {
        logRequest("PUT", endpoint);
        lastResponse = requestSpec.body(body.toString()).headers(headers).put(buildEndpointPath(endpoint));
        logger.debug("Response status code: {}", lastResponse.getStatusCode());
        return lastResponse;
    }
    
    /**
     * Send a DELETE request to the specified API endpoint.
     *
     * @param endpoint The API endpoint to call (will be appended to baseUrl)
     * @return The Response object
     */
    public Response delete(String endpoint) {
        logRequest("DELETE", endpoint);
        lastResponse = requestSpec.delete(buildEndpointPath(endpoint));
        logger.debug("Response status code: {}", lastResponse.getStatusCode());
        return lastResponse;
    }
    
    /**
     * Send a DELETE request to the specified API endpoint with query parameters.
     *
     * @param endpoint The API endpoint to call (will be appended to baseUrl)
     * @param params   Query parameters
     * @return The Response object
     */
    public Response delete(String endpoint, Map<String, ?> params) {
        logRequest("DELETE", endpoint);
        lastResponse = requestSpec.params(params).delete(buildEndpointPath(endpoint));
        logger.debug("Response status code: {}", lastResponse.getStatusCode());
        return lastResponse;
    }
    
    /**
     * Send a DELETE request to the specified API endpoint with query parameters and headers.
     *
     * @param endpoint The API endpoint to call (will be appended to baseUrl)
     * @param params   Query parameters
     * @param headers  Request headers
     * @return The Response object
     */
    public Response delete(String endpoint, Map<String, ?> params, Map<String, String> headers) {
        logRequest("DELETE", endpoint);
        lastResponse = requestSpec.params(params).headers(headers).delete(buildEndpointPath(endpoint));
        logger.debug("Response status code: {}", lastResponse.getStatusCode());
        return lastResponse;
    }
    
    /**
     * Send a PATCH request to the specified API endpoint.
     *
     * @param endpoint The API endpoint to call (will be appended to baseUrl)
     * @return The Response object
     */
    public Response patch(String endpoint) {
        logRequest("PATCH", endpoint);
        lastResponse = requestSpec.patch(buildEndpointPath(endpoint));
        logger.debug("Response status code: {}", lastResponse.getStatusCode());
        return lastResponse;
    }
    
    /**
     * Send a PATCH request to the specified API endpoint with a JSON body.
     *
     * @param endpoint The API endpoint to call (will be appended to baseUrl)
     * @param body     The JSON body as a JSONObject
     * @return The Response object
     */
    public Response patch(String endpoint, JSONObject body) {
        logRequest("PATCH", endpoint);
        lastResponse = requestSpec.body(body.toString()).patch(buildEndpointPath(endpoint));
        logger.debug("Response status code: {}", lastResponse.getStatusCode());
        return lastResponse;
    }
    
    /**
     * Send a PATCH request to the specified API endpoint with a JSON body and headers.
     *
     * @param endpoint The API endpoint to call (will be appended to baseUrl)
     * @param body     The JSON body as a JSONObject
     * @param headers  Request headers
     * @return The Response object
     */
    public Response patch(String endpoint, JSONObject body, Map<String, String> headers) {
        logRequest("PATCH", endpoint);
        lastResponse = requestSpec.body(body.toString()).headers(headers).patch(buildEndpointPath(endpoint));
        logger.debug("Response status code: {}", lastResponse.getStatusCode());
        return lastResponse;
    }
    
    /**
     * Get the Response object from the last request.
     *
     * @return The last Response object
     * @throws IllegalStateException if no request has been made yet
     */
    public Response getLastResponse() {
        if (lastResponse == null) {
            throw new IllegalStateException("No response available. Make a request first.");
        }
        return lastResponse;
    }
    
    /**
     * Get the status code from the last request.
     *
     * @return The HTTP status code
     * @throws IllegalStateException if no request has been made yet
     */
    public int getResponseStatusCode() {
        return getLastResponse().getStatusCode();
    }
    
    /**
     * Get the response body as a string from the last request.
     *
     * @return The response body as a string
     * @throws IllegalStateException if no request has been made yet
     */
    public String getResponseBody() {
        return getLastResponse().getBody().asString();
    }
    
    /**
     * Get the response body as a JSONObject from the last request.
     *
     * @return The response body as a JSONObject
     * @throws IllegalStateException if no request has been made yet
     */
    public JSONObject getResponseBodyAsJson() {
        return new JSONObject(getResponseBody());
    }
    
    /**
     * Set the Authorization header.
     *
     * @param authType The authorization type (e.g., "Bearer", "Basic")
     * @param token    The authorization token
     */
    public void setAuthorization(String authType, String token) {
        requestSpec.header("Authorization", authType + " " + token);
    }
    
    /**
     * Clear the Authorization header.
     */
    public void clearAuthorization() {
        requestSpec.header("Authorization", "");
    }
    
    /**
     * Set request headers.
     *
     * @param headers Map of header names and values
     */
    public void setHeaders(Map<String, String> headers) {
        requestSpec.headers(headers);
    }
    
    /**
     * Add a single header to the request.
     *
     * @param name  Header name
     * @param value Header value
     */
    public void addHeader(String name, String value) {
        requestSpec.header(name, value);
    }
    
    /**
     * Set a request timeout.
     *
     * @param timeoutInMillis Timeout in milliseconds
     */
    public void setTimeout(int timeoutInMillis) {
        RestAssured.config().httpConfig().requestConfig().setConfig(
                org.apache.http.client.config.RequestConfig.custom()
                        .setConnectTimeout(timeoutInMillis)
                        .setSocketTimeout(timeoutInMillis)
                        .build());
    }
}
