package core.clients;

import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import io.restassured.response.Response;
import io.restassured.specification.RequestSpecification;
import org.json.JSONObject;

import java.util.HashMap;
import java.util.Map;

/**
 * Base API client for making HTTP requests.
 */
public class BaseApiClient {
    private final String baseUrl;
    private final Map<String, String> headers;

    /**
     * Constructor with base URL.
     *
     * @param baseUrl The base URL for API requests
     */
    public BaseApiClient(String baseUrl) {
        this.baseUrl = baseUrl;
        this.headers = new HashMap<>();
        // Set default headers
        headers.put("Content-Type", "application/json");
        headers.put("Accept", "application/json");
    }

    /**
     * Set headers for requests.
     *
     * @param headers Map of headers
     */
    public void setHeaders(Map<String, String> headers) {
        this.headers.clear();
        this.headers.putAll(headers);
    }

    /**
     * Add a single header.
     *
     * @param name Header name
     * @param value Header value
     */
    public void addHeader(String name, String value) {
        this.headers.put(name, value);
    }

    /**
     * Make a GET request.
     *
     * @param path The API endpoint path
     * @return The response
     */
    public Response get(String path) {
        return get(path, null);
    }

    /**
     * Make a GET request with query parameters.
     *
     * @param path The API endpoint path
     * @param queryParams Map of query parameters
     * @return The response
     */
    public Response get(String path, Map<String, String> queryParams) {
        RequestSpecification request = createRequest();
        
        if (queryParams != null) {
            request.queryParams(queryParams);
        }
        
        return request.get(baseUrl + path);
    }

    /**
     * Make a POST request.
     *
     * @param path The API endpoint path
     * @param body The request body
     * @return The response
     */
    public Response post(String path, JSONObject body) {
        return createRequest()
                .body(body.toString())
                .post(baseUrl + path);
    }

    /**
     * Make a PUT request.
     *
     * @param path The API endpoint path
     * @param body The request body
     * @return The response
     */
    public Response put(String path, JSONObject body) {
        return createRequest()
                .body(body.toString())
                .put(baseUrl + path);
    }

    /**
     * Make a PATCH request.
     *
     * @param path The API endpoint path
     * @param body The request body
     * @return The response
     */
    public Response patch(String path, JSONObject body) {
        return createRequest()
                .body(body.toString())
                .patch(baseUrl + path);
    }

    /**
     * Make a DELETE request.
     *
     * @param path The API endpoint path
     * @return The response
     */
    public Response delete(String path) {
        return createRequest()
                .delete(baseUrl + path);
    }

    /**
     * Create a request specification with headers.
     *
     * @return The request specification
     */
    private RequestSpecification createRequest() {
        RequestSpecification request = RestAssured.given();
        
        for (Map.Entry<String, String> header : headers.entrySet()) {
            request.header(header.getKey(), header.getValue());
        }
        
        return request;
    }
}