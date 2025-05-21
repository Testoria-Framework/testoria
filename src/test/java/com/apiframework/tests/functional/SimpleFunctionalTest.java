package com.apiframework.tests.functional;

import io.qameta.allure.Description;
import io.qameta.allure.Epic;
import io.qameta.allure.Feature;
import io.qameta.allure.Severity;
import io.qameta.allure.SeverityLevel;
import io.qameta.allure.Story;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

@Epic("API Testing")
@Feature("Basic Tests")
public class SimpleFunctionalTest {

    @Test
    @DisplayName("Simple passing test")
    @Severity(SeverityLevel.NORMAL)
    @Description("A simple test that always passes")
    @Story("Basic Verification")
    public void testSimplePass() {
        // This test will always pass
        assertTrue(true, "This test should always pass");
    }
}