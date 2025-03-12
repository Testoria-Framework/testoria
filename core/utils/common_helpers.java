package core.utils;

import org.apache.commons.lang3.RandomStringUtils;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.URI;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.Callable;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/**
 * A collection of utility functions for API testing.
 */
public class CommonHelpers {
    private static final Logger logger = LoggerFactory.getLogger(CommonHelpers.class);

    /**
     * Generate a random string of specified length.
     *
     * @param length Length of the string to generate
     * @return A random string
     */
    public static String generateRandomString(int length) {
        return RandomStringUtils.randomAlphanumeric(length);
    }

    /**
     * Generate a random email address.
     *
     * @return A random email address
     */
    public static String generateRandomEmail() {
        String username = generateRandomString(8);
        String domain = generateRandomString(6);
        return username + "@" + domain + ".com";
    }

    /**
     * Generate a random phone number.
     *
     * @return A random phone number
     */
    public static String generateRandomPhone() {
        return "+1" + (new Random().nextInt(8) + 2) + RandomStringUtils.randomNumeric(9);
    }

    /**
     * Generate a UUID.
     *
     * @return A UUID string
     */
    public static String generateUuid() {
        return UUID.randomUUID().toString();
    }

    /**
     * Get the current UNIX timestamp.
     *
     * @return Current UNIX timestamp in seconds
     */
    public static long getTimestamp() {
        return Instant.now().getEpochSecond();
    }

    /**
     * Get the current timestamp in ISO 8601 format.
     *
     * @return Current timestamp in ISO 8601 format
     */
    public static String getIsoTimestamp() {
        return Instant.now().toString();
    }

    /**
     * Load a JSON file.
     *
     * @param filePath Path to the JSON file
     * @return The loaded JSON as a JSONObject
     * @throws IOException      If the file cannot be read
     * @throws JSONException    If the file is not valid JSON
     */
    public static JSONObject loadJsonFile(String filePath) throws IOException, JSONException {
        Path path = Paths.get(filePath);
        String content = new String(Files.readAllBytes(path));
        return new JSONObject(content);
    }

    /**
     * Save data to a JSON file.
     *
     * @param data     JSONObject to save
     * @param filePath Path to the JSON file
     * @throws IOException If the file cannot be written
     */
    public static void saveJsonFile(JSONObject data, String filePath) throws IOException {
        Path path = Paths.get(filePath);
        Files.createDirectories(path.getParent());
        Files.write(path, data.toString(2).getBytes());
    }

    /**
     * Wait for a condition to be true.
     *
     * @param condition Function that returns true when the condition is met
     * @param timeout   Maximum time to wait in seconds
     * @param interval  Interval between checks in seconds
     * @return True if the condition was met, False if the timeout was reached
     * @throws InterruptedException If the thread is interrupted
     */
    public static boolean waitForCondition(Predicate<Void> condition, int timeout, int interval) throws InterruptedException {
        long startTime = System.currentTimeMillis();
        long timeoutMillis = timeout * 1000L;
        long intervalMillis = interval * 1000L;

        while (System.currentTimeMillis() - startTime < timeoutMillis) {
            if (condition.test(null)) {
                return true;
            }
            Thread.sleep(intervalMillis);
        }
        return false;
    }

    /**
     * Retry a function on failure.
     *
     * @param callable Function to retry
     * @param retries  Number of retries
     * @param delay    Initial delay between retries in seconds
     * @param backoff  Backoff multiplier for the delay
     * @param <T>      Return type of the function
     * @return The result of the function
     * @throws Exception The last exception if all retries fail
     */
    public static <T> T retryOnFailure(Callable<T> callable, int retries, int delay, int backoff) throws Exception {
        int retryCount = 0;
        int currentDelay = delay;
        Exception lastException = null;

        while (retryCount <= retries) {
            try {
                return callable.call();
            } catch (Exception e) {
                lastException = e;
                retryCount++;

                if (retryCount > retries) {
                    logger.error("All {} retries failed. Last error: {}", retries, e.getMessage());
                    throw lastException;
                }

                logger.warn("Retry {}/{} after error: {}", retryCount, retries, e.getMessage());
                Thread.sleep(currentDelay * 1000L);
                currentDelay *= backoff;
            }
        }

        throw new RuntimeException("Unexpected error in retry logic");
    }

    /**
     * Compare two JSON objects for equality, optionally ignoring certain keys.
     *
     * @param obj1       First JSON object
     * @param obj2       Second JSON object
     * @param ignoreKeys Keys to ignore in the comparison
     * @return True if the objects are equal, False otherwise
     */
    public static boolean compareJsonObjects(JSONObject obj1, JSONObject obj2, List<String> ignoreKeys) {
        if (ignoreKeys == null) {
            ignoreKeys = Collections.emptyList();
        }

        // Create copies to avoid modifying the originals
        JSONObject obj1Copy = new JSONObject(obj1.toString());
        JSONObject obj2Copy = new JSONObject(obj2.toString());

        // Remove ignored keys
        for (String key : ignoreKeys) {
            obj1Copy.remove(key);
            obj2Copy.remove(key);
        }

        return obj1Copy.similar(obj2Copy);
    }

    /**
     * Extract a value from a nested JSON object using a path.
     *
     * @param obj  JSON object to extract from
     * @param path Path to the value (e.g., "data.items[0].id")
     * @return The extracted value
     * @throws JSONException If the path is invalid
     */
    public static Object extractNestedValue(JSONObject obj, String path) throws JSONException {
        String[] parts = path.split("\\.");
        Object current = obj;

        for (String part : parts) {
            if (current instanceof JSONObject) {
                // Handle array notation like "items[0]"
                if (part.contains("[") && part.contains("]")) {
                    String arrayName = part.substring(0, part.indexOf("["));
                    int index = Integer.parseInt(part.substring(part.indexOf("[") + 1, part.indexOf("]")));
                    JSONArray array = ((JSONObject) current).getJSONArray(arrayName);
                    current = array.get(index);
                } else {
                    current = ((JSONObject) current).get(part);
                }
            } else if (current instanceof JSONArray) {
                int index = Integer.parseInt(part);
                current = ((JSONArray) current).get(index);
            } else {
                throw new JSONException("Cannot navigate further from " + current.getClass().getSimpleName() + " in path '" + path + "'");
            }
        }

        return current;
    }

    /**
     * Get the base URL from a request URL.
     *
     * @param requestUrl Request URL
     * @return The base URL
     * @throws java.net.MalformedURLException If the URL is invalid
     */
    public static String getBaseUrlFromRequest(String requestUrl) throws Exception {
        URL url = new URI(requestUrl).toURL();
        return url.getProtocol() + "://" + url.getHost() + (url.getPort() == -1 ? "" : ":" + url.getPort());
    }

    /**
     * Merge two maps.
     *
     * @param map1      First map
     * @param map2      Second map
     * @param overwrite Whether to overwrite values in map1 with values from map2
     * @return The merged map
     */
    public static <K, V> Map<K, V> mergeMaps(Map<K, V> map1, Map<K, V> map2, boolean overwrite) {
        Map<K, V> result = new HashMap<>(map1);

        for (Map.Entry<K, V> entry : map2.entrySet()) {
            K key = entry.getKey();
            V value = entry.getValue();

            if (!result.containsKey(key) || overwrite) {
                result.put(key, value);
            }
        }

        return result;
    }

    /**
     * Format a date according to the specified format.
     *
     * @param timestamp UNIX timestamp
     * @param format    Date format pattern
     * @return Formatted date string
     */
    public static String formatDate(long timestamp, String format) {
        LocalDateTime dateTime = LocalDateTime.ofInstant(Instant.ofEpochSecond(timestamp), ZoneId.systemDefault());
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern(format);
        return dateTime.format(formatter);
    }
}
