package core.assertions;

import io.restassured.response.Response;
import org.hamcrest.Matchers;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Assert;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * Utility class for API testing assertions in Java.
 * Provides methods to validate API responses, headers, status codes, and more.
 */
public class JavaAssertions {
    private static final Logger logger = LoggerFactory.getLogger(JavaAssertions.class);

    /**
     * Assert that the response has the expected status code.
     *
     * @param response     The Response object
     * @param expectedCode Expected HTTP status code
     */
    public static void assertStatusCode(Response response, int expectedCode) {
        response.then().statusCode(expectedCode);
    }

    /**
     * Assert that the response has a successful status code (2xx).
     *
     * @param response The Response object
     */
    public static void assertSuccess(Response response) {
        int statusCode = response.getStatusCode();
        Assert.assertTrue("Status code should be in the 2xx range", statusCode >= 200 && statusCode <= 299);
    }

    /**
     * Assert that the response has a client error status code (4xx).
     *
     * @param response The Response object
     */
    public static void assertClientError(Response response) {
        int statusCode = response.getStatusCode();
        Assert.assertTrue("Status code should be in the 4xx range", statusCode >= 400 && statusCode <= 499);
    }

    /**
     * Assert that the response has a server error status code (5xx).
     *
     * @param response The Response object
     */
    public static void assertServerError(Response response) {
        int statusCode = response.getStatusCode();
        Assert.assertTrue("Status code should be in the 5xx range", statusCode >= 500 && statusCode <= 599);
    }

    /**
     * Assert that the response contains the specified header.
     *
     * @param response   The Response object
     * @param headerName Header name to check
     */
    public static void assertHeaderExists(Response response, String headerName) {
        response.then().header(headerName, Matchers.notNullValue());
    }

    /**
     * Assert that the response header has the expected value.
     *
     * @param response      The Response object
     * @param headerName    Header name to check
     * @param expectedValue Expected header value
     */
    public static void assertHeaderValue(Response response, String headerName, String expectedValue) {
        response.then().header(headerName, expectedValue);
    }

    /**
     * Assert that the response has the expected Content-Type header.
     *
     * @param response            The Response object
     * @param expectedContentType Expected Content-Type
     */
    public static void assertContentType(Response response, String expectedContentType) {
        response.then().contentType(expectedContentType);
    }

    /**
     * Assert that the response has a JSON Content-Type header.
     *
     * @param response The Response object
     */
    public static void assertJsonContentType(Response response) {
        assertContentType(response, "application/json");
    }

    /**
     * Assert that the response body contains the expected content.
     *
     * @param response        The Response object
     * @param expectedContent Expected content
     */
    public static void assertBodyContains(Response response, String expectedContent) {
        response.then().body(Matchers.containsString(expectedContent));
    }

    /**
     * Assert that the JSON response has the specified key.
     *
     * @param response The Response object
     * @param key      Key to check
     */
    public static void assertJsonHasKey(Response response, String key) {
        response.then().body(key, Matchers.notNullValue());
    }

    /**
     * Assert that the JSON response has all the specified keys.
     *
     * @param response The Response object
     * @param keys     List of keys to check
     */
    public static void assertJsonHasKeys(Response response, List<String> keys) {
        for (String key : keys) {
            assertJsonHasKey(response, key);
        }
    }

    /**
     * Assert that the JSON response has the specified key with the expected value.
     *
     * @param response      The Response object
     * @param key           Key to check
     * @param expectedValue Expected value
     */
    public static void assertJsonValue(Response response, String key, Object expectedValue) {
        response.then().body(key, Matchers.equalTo(expectedValue));
    }

    /**
     * Assert that the JSON response has the specified keys with the expected values.
     *
     * @param response  The Response object
     * @param keyValues Dictionary of key-value pairs to check
     */
    public static void assertJsonValues(Response response, Map<String, Object> keyValues) {
        for (Map.Entry<String, Object> entry : keyValues.entrySet()) {
            assertJsonValue(response, entry.getKey(), entry.getValue());
        }
    }

    /**
     * Assert that the JSON response matches the specified schema.
     *
     * @param response The Response object
     * @param schema   JSON schema to validate against
     */
    public static void assertJsonMatchesSchema(Response response, String schema) {
        response.then().body(Matchers.matchesJsonSchema(schema));
    }

    /**
     * Assert that a list in the JSON response has the expected length.
     *
     * @param response       The Response object
     * @param path           Path to the list (e.g., 'data.items')
     * @param expectedLength Expected length of the list
     */
    public static void assertJsonListLength(Response response, String path, int expectedLength) {
        response.then().body(path + ".size()", Matchers.equalTo(expectedLength));
    }

    /**
     * Assert that the response time is below the maximum allowed time.
     *
     * @param response   The Response object
     * @param maxTimeMs Maximum allowed response time in milliseconds
     */
    public static void assertResponseTime(Response response, long maxTimeMs) {
        response.then().time(Matchers.lessThanOrEqualTo(maxTimeMs));
    }

    /**
     * Assert that the text matches the specified regex pattern.
     *
     * @param text          Text to check
     * @param regexPattern  Regex pattern to match
     */
    public static void assertRegexMatch(String text, String regexPattern) {
        Assert.assertTrue("Text does not match pattern: " + regexPattern,
                Pattern.compile(regexPattern).matcher(text).matches());
    }

    /**
     * Convert the response body to a JSONObject.
     *
     * @param response The Response object
     * @return The response body as a JSONObject
     */
    public static JSONObject getResponseAsJsonObject(Response response) {
        try {
            return new JSONObject(response.getBody().asString());
        } catch (JSONException e) {
            logger.error("Failed to parse response body as JSON", e);
            throw new AssertionError("Response body is not valid JSON", e);
        }
    }

    /**
     * Convert the response body to a JSONArray.
     *
     * @param response The Response object
     * @return The response body as a JSONArray
     */
    public static JSONArray getResponseAsJsonArray(Response response) {
        try {
            return new JSONArray(response.getBody().asString());
        } catch (JSONException e) {
            logger.error("Failed to parse response body as JSON array", e);
            throw new AssertionError("Response body is not a valid JSON array", e);
        }
    }

    /**
     * Assert that the JSON response contains a specific value in a list at the given path.
     *
     * @param response The Response object
     * @param path     Path to the list
     * @param value    Value to check for
     */
    public static void assertJsonListContains(Response response, String path, Object value) {
        response.then().body(path, Matchers.hasItem(value));
    }

    /**
     * Assert that two JSONObjects are equivalent (same structure and values, regardless of order).
     *
     * @param actual   The actual JSONObject
     * @param expected The expected JSONObject
     */
    public static void assertJsonEquivalent(JSONObject actual, JSONObject expected) {
        Assert.assertEquals("JSON objects are not equivalent", expected.toString(), actual.toString());
    }

    /**
     * Assert that the response body is not empty.
     *
     * @param response The Response object
     */
    public static void assertNonEmptyResponse(Response response) {
        String responseBody = response.getBody().asString();
        Assert.assertTrue("Response body should not be empty", responseBody != null && !responseBody.trim().isEmpty());
    }
}
