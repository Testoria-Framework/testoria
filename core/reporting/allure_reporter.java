package core.reporting;

import io.qameta.allure.Allure;
import io.qameta.allure.AllureLifecycle;
import io.qameta.allure.model.*;
import io.restassured.response.Response;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.ByteArrayInputStream;
import java.util.*;

/**
 * A utility class for reporting API test results to Allure.
 */
public class AllureReporter {
    private static final Logger logger = LoggerFactory.getLogger(AllureReporter.class);
    
    private final AllureLifecycle lifecycle;
    private final boolean enabled;

    private static AllureReporter instance;

    /**
     * Get the singleton instance of AllureReporter.
     *
     * @return The AllureReporter instance
     */
    public static synchronized AllureReporter getInstance() {
        if (instance == null) {
            instance = new AllureReporter();
        }
        return instance;
    }

    /**
     * Initialize the AllureReporter.
     */
    private AllureReporter() {
        this.lifecycle = Allure.getLifecycle();
        this.enabled = true; // Could be loaded from config
    }

    /**
     * Start a test case.
     *
     * @param testName    Name of the test
     * @param description Optional description of the test
     */
    public void startTest(String testName, String description) {
        if (!enabled) {
            return;
        }

        logger.debug("Starting test: {}", testName);
        
        // In JUnit 5 with Allure, tests are typically automatically started
        // This method can be used for additional setup
        
        if (description != null && !description.isEmpty()) {
            Allure.description(description);
        }
    }

    /**
     * End a test case.
     */
    public void endTest() {
        if (!enabled) {
            return;
        }

        logger.debug("Ending test");
        
        // In JUnit 5 with Allure, tests are typically automatically completed
        // This method can be used for additional teardown
    }

    /**
     * Add a step to the current test.
     *
     * @param name    Name of the step
     * @param status  Status of the step (passed, failed, broken, skipped)
     * @param details Optional details of the step
     */
    public void addStep(String name, Status status, String details) {
        if (!enabled) {
            return;
        }

        logger.debug("Adding step: {}", name);
        
        Allure.step(name, () -> {
            if (details != null && !details.isEmpty()) {
                Allure.attachment("Step Details", details);
            }
            
            if (status == Status.FAILED) {
                throw new AssertionError(details);
            }
        });
    }

    /**
     * Add an API request to the current test.
     *
     * @param method  HTTP method
     * @param url     Request URL
     * @param headers Request headers
     * @param body    Request body
     */
    public void addApiRequest(String method, String url, Map<String, String> headers, Object body) {
        if (!enabled) {
            return;
        }

        logger.debug("Adding API request: {} {}", method, url);
        
        Allure.step(method + " " + url, () -> {
            // Attach headers
            if (headers != null && !headers.isEmpty()) {
                Map<String, String> sanitizedHeaders = sanitizeHeaders(headers);
                Allure.attachment("Request Headers", new JSONObject(sanitizedHeaders).toString(2));
            }
            
            // Attach body
            if (body != null) {
                if (body instanceof JSONObject) {
                    Allure.attachment("Request Body", ((JSONObject) body).toString(2));
                } else {
                    Allure.attachment("Request Body", body.toString());
                }
            }
        });
    }

    /**
     * Add an API response to the current test.
     *
     * @param response    Response object
     * @param elapsedTime Optional elapsed time in milliseconds
     */
    public void addApiResponse(Response response, Long elapsedTime) {
        if (!enabled) {
            return;
        }

        logger.debug("Adding API response: {}", response.getStatusCode());
        
        Allure.step("Response: " + response.getStatusCode(), () -> {
            // Attach status and elapsed time
            StringBuilder statusInfo = new StringBuilder();
            statusInfo.append("Status: ").append(response.getStatusCode()).append("\n");
            
            if (elapsedTime != null) {
                statusInfo.append("Time: ").append(String.format("%.2f", elapsedTime)).append(" ms");
            } else {
                statusInfo.append("Time: ").append(String.format("%.2f", response.getTime())).append(" ms");
            }
            
            Allure.attachment("Response Status", statusInfo.toString());
            
            // Attach headers
            Map<String, String> headers = new HashMap<>();
            response.getHeaders().forEach(header -> headers.put(header.getName(), header.getValue()));
            Map<String, String> sanitizedHeaders = sanitizeHeaders(headers);
            Allure.attachment("Response Headers", new JSONObject(sanitizedHeaders).toString(2));
            
            // Attach body
            String responseBody = response.getBody().asString();
            if (responseBody != null && !responseBody.isEmpty()) {
                try {
                    // Try to parse as JSON
                    JSONObject jsonResponse = new JSONObject(responseBody);
                    Allure.attachment("Response Body", jsonResponse.toString(2));
                } catch (Exception e) {
                    // Not JSON, attach as text
                    Allure.attachment("Response Body", responseBody);
                }
            }
        });
    }

    /**
     * Add an API response to the current test.
     *
     * @param response Response object
     */
    public void addApiResponse(Response response) {
        addApiResponse(response, null);
    }

    /**
     * Add an attachment to the current test.
     *
     * @param name    Name of the attachment
     * @param content Content of the attachment
     * @param type    Type of the attachment
     */
    public void addAttachment(String name, String content, String type) {
        if (!enabled) {
            return;
        }

        logger.debug("Adding attachment: {}", name);
        
        Allure.attachment(name, new ByteArrayInputStream(content.getBytes()), type);
    }

    /**
     * Add a link to the current test.
     *
     * @param url      URL
     * @param name     Optional name of the link
     * @param linkType Type of the link (link, issue, tms)
     */
    public void addLink(String url, String name, String linkType) {
        if (!enabled) {
            return;
        }

        logger.debug("Adding link: {}", url);
        
        if ("issue".equals(linkType)) {
            Allure.issue(name, url);
        } else if ("tms".equals(linkType)) {
            Allure.tms(name, url);
        } else {
            Allure.link(name, url);
        }
    }

    /**
     * Set the description of the current test.
     *
     * @param description Description of the test
     * @param isHtml      Whether the description is HTML
     */
    public void setDescription(String description, boolean isHtml) {
        if (!enabled) {
            return;
        }

        logger.debug("Setting description");
        
        if (isHtml) {
            Allure.descriptionHtml(description);
        } else {
            Allure.description(description);
        }
    }

    /**
     * Add a parameter to the current test.
     *
     * @param name  Name of the parameter
     * @param value Value of the parameter
     */
    public void addParameter(String name, String value) {
        if (!enabled) {
            return;
        }

        logger.debug("Adding parameter: {}", name);
        
        Allure.parameter(name, value);
    }

    /**
     * Add a tag to the current test.
     *
     * @param tag Tag to add
     */
    public void addTag(String tag) {
        if (!enabled) {
            return;
        }

        logger.debug("Adding tag: {}", tag);
        
        Allure.label("tag", tag);
    }

    /**
     * Add a severity level to the current test.
     *
     * @param severity Severity level (trivial, minor, normal, critical, blocker)
     */
    public void addSeverity(String severity) {
        if (!enabled) {
            return;
        }

        logger.debug("Adding severity: {}", severity);
        
        Allure.label("severity", severity);
    }

    /**
     * Add a suite name to the current test.
     *
     * @param suiteName Name of the suite
     */
    public void addSuite(String suiteName) {
        if (!enabled) {
            return;
        }

        logger.debug("Adding suite: {}", suiteName);
        
        Allure.label("suite", suiteName);
    }

    /**
     * Add an epic to the current test.
     *
     * @param epic Epic name
     */
    public void addEpic(String epic) {
        if (!enabled) {
            return;
        }

        logger.debug("Adding epic: {}", epic);
        
        Allure.epic(epic);
    }

    /**
     * Add a feature to the current test.
     *
     * @param feature Feature name
     */
    public void addFeature(String feature) {
        if (!enabled) {
            return;
        }

        logger.debug("Adding feature: {}", feature);
        
        Allure.feature(feature);
    }

    /**
     * Add a story to the current test.
     *
     * @param story Story name
     */
    public void addStory(String story) {
        if (!enabled) {
            return;
        }

        logger.debug("Adding story: {}", story);
        
        Allure.story(story);
    }

    /**
     * Sanitize headers by masking sensitive information.
     *
     * @param headers Headers to sanitize
     * @return Sanitized headers
     */
    private Map<String, String> sanitizeHeaders(Map<String, String> headers) {
        Map<String, String> sanitized = new HashMap<>(headers);
        List<String> sensitiveHeaders = Arrays.asList("Authorization", "X-API-Key", "Cookie");
        
        for (String header : sensitiveHeaders) {
            if (sanitized.containsKey(header)) {
                sanitized.put(header, "*****");
            }
        }
        
        return sanitized;
    }
}
