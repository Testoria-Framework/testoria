package core.assertions;

import io.restassured.response.Response;
import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.jupiter.api.Assertions;

/**
 * Utility class for common API test assertions.
 */
public class JavaAssertions {

    /**
     * Assert that the response has the expected status code.
     *
     * @param response The response to check
     * @param expectedStatusCode The expected status code
     */
    public static void assertStatusCode(Response response, int expectedStatusCode) {
        Assertions.assertEquals(expectedStatusCode, response.getStatusCode(),
                "Expected status code " + expectedStatusCode + " but got " + response.getStatusCode());
    }

    /**
     * Assert that the response has JSON content type.
     *
     * @param response The response to check
     */
    public static void assertJsonContentType(Response response) {
        String contentType = response.getContentType();
        Assertions.assertTrue(contentType != null && contentType.contains("application/json"),
                "Expected JSON content type but got " + contentType);
    }

    /**
     * Assert that the response time is less than the specified maximum.
     *
     * @param response The response to check
     * @param maxTimeMs The maximum acceptable response time in milliseconds
     */
    public static void assertResponseTime(Response response, long maxTimeMs) {
        Assertions.assertTrue(response.getTime() <= maxTimeMs,
                "Response time " + response.getTime() + "ms exceeded maximum " + maxTimeMs + "ms");
    }

    /**
     * Get the response body as a JSONObject.
     *
     * @param response The response to convert
     * @return The response body as a JSONObject
     */
    public static JSONObject getResponseAsJsonObject(Response response) {
        return new JSONObject(response.getBody().asString());
    }

    /**
     * Get the response body as a JSONArray.
     *
     * @param response The response to convert
     * @return The response body as a JSONArray
     */
    public static JSONArray getResponseAsJsonArray(Response response) {
        return new JSONArray(response.getBody().asString());
    }
}