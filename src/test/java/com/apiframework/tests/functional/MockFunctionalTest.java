package com.apiframework.tests.functional;

import io.qameta.allure.Description;
import io.qameta.allure.Epic;
import io.qameta.allure.Feature;
import io.qameta.allure.Severity;
import io.qameta.allure.SeverityLevel;
import io.qameta.allure.Story;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeAll;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertEquals;

@Epic("API Testing")
@Feature("Mock Tests")
public class MockFunctionalTest {

    @Test
    @DisplayName("Simple passing test")
    @Severity(SeverityLevel.NORMAL)
    @Description("A simple test that always passes")
    @Story("Basic Verification")
    public void testSimplePass() {
        assertTrue(true, "This test should always pass");
    }
    
    @Test
    @DisplayName("Test with assertions")
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test with multiple assertions")
    @Story("Basic Assertions")
    public void testWithAssertions() {
        // String assertions
        String expected = "test";
        String actual = "test";
        assertEquals(expected, actual, "Strings should be equal");
        
        // Numeric assertions
        int expectedNumber = 5;
        int actualNumber = 5;
        assertEquals(expectedNumber, actualNumber, "Numbers should be equal");
    }
}