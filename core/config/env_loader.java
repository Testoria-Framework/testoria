package core.config;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * A utility class for loading and parsing configuration settings.
 * Supports environment variable substitution and environment-specific configs.
 */
public class EnvLoader {
    private static final Logger logger = LoggerFactory.getLogger(EnvLoader.class);
    
    private final String configPath;
    private JSONObject config;
    private final Pattern envPattern = Pattern.compile("\\$\\{([^}]+)\\}");

    private static EnvLoader instance;

    /**
     * Get the singleton instance of the EnvLoader.
     *
     * @return The EnvLoader instance
     */
    public static synchronized EnvLoader getInstance() {
        if (instance == null) {
            instance = new EnvLoader();
        }
        return instance;
    }

    /**
     * Initialize the EnvLoader with the default config path.
     */
    private EnvLoader() {
        this("core/config/config.json");
    }

    /**
     * Initialize the EnvLoader with a specific config path.
     *
     * @param configPath Path to the JSON configuration file
     */
    private EnvLoader(String configPath) {
        this.configPath = configPath;
        this.config = null;
    }

    /**
     * Load the configuration from the JSON file and process environment variables.
     *
     * @return The processed configuration
     * @throws IOException   If the configuration file cannot be read
     * @throws JSONException If the configuration file is not valid JSON
     */
    public JSONObject loadConfig() throws IOException, JSONException {
        if (config != null) {
            return config;
        }

        Path path = Paths.get(configPath);
        String content = new String(Files.readAllBytes(path));
        JSONObject rawConfig = new JSONObject(content);

        // Process environment variables in the configuration
        config = processEnvVars(rawConfig);
        return config;
    }

    /**
     * Get the configuration for the specified environment.
     *
     * @param env Optional environment name (default: from ENVIRONMENT env var or "dev")
     * @return The environment-specific configuration
     * @throws IOException      If the configuration file cannot be read
     * @throws JSONException    If the configuration file is not valid JSON
     * @throws RuntimeException If the specified environment does not exist in the configuration
     */
    public JSONObject getEnvironmentConfig(String env) throws IOException, JSONException {
        if (env == null || env.isEmpty()) {
            env = System.getenv("ENVIRONMENT");
            if (env == null || env.isEmpty()) {
                env = "dev";
            }
        }

        JSONObject fullConfig = loadConfig();

        if (!fullConfig.has("environments") || !fullConfig.getJSONObject("environments").has(env)) {
            String errorMsg = "Environment '" + env + "' not found in configuration";
            logger.error(errorMsg);
            throw new RuntimeException(errorMsg);
        }

        return fullConfig.getJSONObject("environments").getJSONObject(env);
    }

    /**
     * Get the test settings for the specified test type.
     *
     * @param testType Test type (e.g., "functional", "integration", "performance", "security")
     * @return The test-type-specific settings
     * @throws IOException      If the configuration file cannot be read
     * @throws JSONException    If the configuration file is not valid JSON
     * @throws RuntimeException If the specified test type does not exist in the configuration
     */
    public JSONObject getTestSettings(String testType) throws IOException, JSONException {
        JSONObject fullConfig = loadConfig();

        if (!fullConfig.has("test_settings") || !fullConfig.getJSONObject("test_settings").has(testType)) {
            String errorMsg = "Test type '" + testType + "' not found in configuration";
            logger.error(errorMsg);
            throw new RuntimeException(errorMsg);
        }

        return fullConfig.getJSONObject("test_settings").getJSONObject(testType);
    }

    /**
     * Get the reporting configuration.
     *
     * @return The reporting configuration
     * @throws IOException      If the configuration file cannot be read
     * @throws JSONException    If the configuration file is not valid JSON
     * @throws RuntimeException If reporting configuration is not found
     */
    public JSONObject getReportingConfig() throws IOException, JSONException {
        JSONObject fullConfig = loadConfig();

        if (!fullConfig.has("reporting")) {
            String errorMsg = "Reporting configuration not found";
            logger.error(errorMsg);
            throw new RuntimeException(errorMsg);
        }

        return fullConfig.getJSONObject("reporting");
    }

    /**
     * Get the configuration for the specified mock type.
     *
     * @param mockType Mock type (e.g., "wiremock", "mockserver")
     * @return The mock-type-specific configuration
     * @throws IOException      If the configuration file cannot be read
     * @throws JSONException    If the configuration file is not valid JSON
     * @throws RuntimeException If the specified mock type does not exist in the configuration
     */
    public JSONObject getMockConfig(String mockType) throws IOException, JSONException {
        JSONObject fullConfig = loadConfig();

        if (!fullConfig.has("mocks") || !fullConfig.getJSONObject("mocks").has(mockType)) {
            String errorMsg = "Mock type '" + mockType + "' not found in configuration";
            logger.error(errorMsg);
            throw new RuntimeException(errorMsg);
        }

        return fullConfig.getJSONObject("mocks").getJSONObject(mockType);
    }

    /**
     * Get the logging configuration.
     *
     * @return The logging configuration
     * @throws IOException      If the configuration file cannot be read
     * @throws JSONException    If the configuration file is not valid JSON
     * @throws RuntimeException If logging configuration is not found
     */
    public JSONObject getLoggingConfig() throws IOException, JSONException {
        JSONObject fullConfig = loadConfig();

        if (!fullConfig.has("logging")) {
            String errorMsg = "Logging configuration not found";
            logger.error(errorMsg);
            throw new RuntimeException(errorMsg);
        }

        return fullConfig.getJSONObject("logging");
    }

    /**
     * Get the base URL for the specified environment.
     *
     * @param env Optional environment name (default: from ENVIRONMENT env var or "dev")
     * @return The base URL for the environment
     * @throws IOException      If the configuration file cannot be read
     * @throws JSONException    If the configuration file is not valid JSON
     * @throws RuntimeException If the specified environment does not exist in the configuration
     */
    public String getBaseUrl(String env) throws IOException, JSONException {
        JSONObject envConfig = getEnvironmentConfig(env);
        return envConfig.optString("base_url", "");
    }

    /**
     * Recursively process the configuration object and substitute environment variables.
     *
     * @param obj Configuration object or value
     * @return The processed configuration with environment variables substituted
     * @throws JSONException If the JSON processing fails
     */
    private Object processEnvVars(Object obj) throws JSONException {
        if (obj instanceof JSONObject) {
            JSONObject jsonObj = (JSONObject) obj;
            JSONObject result = new JSONObject();

            Iterator<String> keys = jsonObj.keys();
            while (keys.hasNext()) {
                String key = keys.next();
                Object value = jsonObj.get(key);
                result.put(key, processEnvVars(value));
            }

            return result;
        } else if (obj instanceof JSONArray) {
            JSONArray jsonArray = (JSONArray) obj;
            JSONArray result = new JSONArray();

            for (int i = 0; i < jsonArray.length(); i++) {
                result.put(processEnvVars(jsonArray.get(i)));
            }

            return result;
        } else if (obj instanceof String) {
            return substituteEnvVars((String) obj);
        } else {
            return obj;
        }
    }

    /**
     * Substitute environment variables in a string.
     *
     * @param value String containing environment variable references (e.g., "${VAR_NAME}")
     * @return The string with environment variables substituted
     */
    private String substituteEnvVars(String value) {
        Matcher matcher = envPattern.matcher(value);
        StringBuffer sb = new StringBuffer();

        while (matcher.find()) {
            String envVarName = matcher.group(1);
            String envVarValue = System.getenv(envVarName);

            if (envVarValue == null) {
                logger.warn("Environment variable '{}' not found", envVarName);
                // Return the original reference if not found
                matcher.appendReplacement(sb, matcher.group(0));
            } else {
                matcher.appendReplacement(sb, envVarValue);
            }
        }

        matcher.appendTail(sb);
        return sb.toString();
    }

    /**
     * Convert a JSONObject to a Map.
     *
     * @param jsonObject The JSONObject to convert
     * @return A Map representation of the JSONObject
     * @throws JSONException If the conversion fails
     */
    public static Map<String, Object> jsonObjectToMap(JSONObject jsonObject) throws JSONException {
        Map<String, Object> map = new HashMap<>();

        Iterator<String> keys = jsonObject.keys();
        while (keys.hasNext()) {
            String key = keys.next();
            Object value = jsonObject.get(key);

            if (value instanceof JSONObject) {
                map.put(key, jsonObjectToMap((JSONObject) value));
            } else if (value instanceof JSONArray) {
                map.put(key, jsonArrayToList((JSONArray) value));
            } else {
                map.put(key, value);
            }
        }

        return map;
    }

    /**
     * Convert a JSONArray to a List.
     *
     * @param jsonArray The JSONArray to convert
     * @return A List representation of the JSONArray
     * @throws JSONException If the conversion fails
     */
    private static Object jsonArrayToList(JSONArray jsonArray) throws JSONException {
        Object[] list = new Object[jsonArray.length()];

        for (int i = 0; i < jsonArray.length(); i++) {
            Object value = jsonArray.get(i);

            if (value instanceof JSONObject) {
                list[i] = jsonObjectToMap((JSONObject) value);
            } else if (value instanceof JSONArray) {
                list[i] = jsonArrayToList((JSONArray) value);
            } else {
                list[i] = value;
            }
        }

        return list;
    }
}
