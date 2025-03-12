import os
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

import allure
import requests
from allure_commons.types import AttachmentType

from core.config.env_loader import get_reporting_config

logger = logging.getLogger(__name__)

class AllureReporter:
    """
    A utility class for reporting API test results to Allure.
    """
    
    def __init__(self):
        """
        Initialize the AllureReporter with the reporting configuration.
        """
        self.report_config = get_reporting_config().get('allure', {})
        self.enabled = self.report_config.get('enabled', True)
        
        if not self.enabled:
            logger.info("Allure reporting is disabled")
    
    def start_test(self, test_name: str, description: Optional[str] = None) -> None:
        """
        Start a test case.
        
        Args:
            test_name: Name of the test
            description: Optional description of the test
        """
        if not self.enabled:
            return
            
        allure.dynamic.title(test_name)
        
        if description:
            allure.dynamic.description(description)
    
    def end_test(self) -> None:
        """
        End a test case.
        """
        # Allure automatically handles test completion
        pass
    
    def add_step(self, name: str, status: str = "passed", details: Optional[str] = None) -> None:
        """
        Add a step to the current test.
        
        Args:
            name: Name of the step
            status: Status of the step (passed, failed, broken, skipped)
            details: Optional details of the step
        """
        if not self.enabled:
            return
            
        with allure.step(name):
            if details:
                allure.attach(
                    body=details,
                    name="Step Details",
                    attachment_type=AttachmentType.TEXT
                )
            
            if status == "failed":
                assert False, details
    
    def add_api_request(self, method: str, url: str, headers: Optional[Dict[str, str]] = None,
                       body: Optional[Union[Dict[str, Any], str]] = None) -> None:
        """
        Add an API request to the current test.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
        """
        if not self.enabled:
            return
            
        with allure.step(f"{method} {url}"):
            # Attach headers
            if headers:
                sanitized_headers = self._sanitize_headers(headers)
                allure.attach(
                    body=json.dumps(sanitized_headers, indent=2),
                    name="Request Headers",
                    attachment_type=AttachmentType.JSON
                )
            
            # Attach body
            if body:
                if isinstance(body, dict):
                    allure.attach(
                        body=json.dumps(body, indent=2),
                        name="Request Body",
                        attachment_type=AttachmentType.JSON
                    )
                else:
                    allure.attach(
                        body=str(body),
                        name="Request Body",
                        attachment_type=AttachmentType.TEXT
                    )
    
    def add_api_response(self, response: requests.Response, elapsed_time: Optional[float] = None) -> None:
        """
        Add an API response to the current test.
        
        Args:
            response: Response object
            elapsed_time: Optional elapsed time in milliseconds
        """
        if not self.enabled:
            return
            
        with allure.step(f"Response: {response.status_code}"):
            # Attach status and elapsed time
            status_info = f"Status: {response.status_code}\n"
            if elapsed_time is not None:
                status_info += f"Time: {elapsed_time:.2f} ms"
            else:
                status_info += f"Time: {response.elapsed.total_seconds() * 1000:.2f} ms"
                
            allure.attach(
                body=status_info,
                name="Response Status",
                attachment_type=AttachmentType.TEXT
            )
            
            # Attach headers
            sanitized_headers = self._sanitize_headers(dict(response.headers))
            allure.attach(
                body=json.dumps(sanitized_headers, indent=2),
                name="Response Headers",
                attachment_type=AttachmentType.JSON
            )
            
            # Attach body
            try:
                json_response = response.json()
                allure.attach(
                    body=json.dumps(json_response, indent=2),
                    name="Response Body",
                    attachment_type=AttachmentType.JSON
                )
            except ValueError:
                # Not a JSON response
                allure.attach(
                    body=response.text,
                    name="Response Body",
                    attachment_type=AttachmentType.TEXT
                )
    
    def add_attachment(self, name: str, content: Union[str, bytes], 
                      attachment_type: AttachmentType = AttachmentType.TEXT) -> None:
        """
        Add an attachment to the current test.
        
        Args:
            name: Name of the attachment
            content: Content of the attachment
            attachment_type: Type of the attachment
        """
        if not self.enabled:
            return
            
        allure.attach(
            body=content,
            name=name,
            attachment_type=attachment_type
        )
    
    def add_link(self, url: str, name: Optional[str] = None, link_type: str = "link") -> None:
        """
        Add a link to the current test.
        
        Args:
            url: URL
            name: Optional name of the link
            link_type: Type of the link (link, issue, tms)
        """
        if not self.enabled:
            return
            
        if link_type == "issue":
            allure.dynamic.issue(url, name)
        elif link_type == "tms":
            allure.dynamic.testcase(url, name)
        else:
            allure.dynamic.link(url, name)
    
    def set_description(self, description: str, is_html: bool = False) -> None:
        """
        Set the description of the current test.
        
        Args:
            description: Description of the test
            is_html: Whether the description is HTML
        """
        if not self.enabled:
            return
            
        if is_html:
            allure.dynamic.description_html(description)
        else:
            allure.dynamic.description(description)
    
    def add_parameter(self, name: str, value: Any) -> None:
        """
        Add a parameter to the current test.
        
        Args:
            name: Name of the parameter
            value: Value of the parameter
        """
        if not self.enabled:
            return
            
        allure.dynamic.parameter(name, value)
    
    def add_tag(self, tag: str) -> None:
        """
        Add a tag to the current test.
        
        Args:
            tag: Tag to add
        """
        if not self.enabled:
            return
            
        allure.dynamic.tag(tag)
    
    def add_suite(self, suite_name: str) -> None:
        """
        Add a suite name to the current test.
        
        Args:
            suite_name: Name of the suite
        """
        if not self.enabled:
            return
            
        allure.dynamic.suite(suite_name)
    
    def add_severity(self, severity: str) -> None:
        """
        Add a severity level to the current test.
        
        Args:
            severity: Severity level (trivial, minor, normal, critical, blocker)
        """
        if not self.enabled:
            return
            
        allure.dynamic.severity(severity)
    
    def add_epic(self, epic: str) -> None:
        """
        Add an epic to the current test.
        
        Args:
            epic: Epic name
        """
        if not self.enabled:
            return
            
        allure.dynamic.epic(epic)
    
    def add_feature(self, feature: str) -> None:
        """
        Add a feature to the current test.
        
        Args:
            feature: Feature name
        """
        if not self.enabled:
            return
            
        allure.dynamic.feature(feature)
    
    def add_story(self, story: str) -> None:
        """
        Add a story to the current test.
        
        Args:
            story: Story name
        """
        if not self.enabled:
            return
            
        allure.dynamic.story(story)
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Sanitize headers by masking sensitive information.
        
        Args:
            headers: Headers to sanitize
            
        Returns:
            Sanitized headers
        """
        sanitized = headers.copy()
        sensitive_headers = ['Authorization', 'X-API-Key', 'Cookie']
        
        for header in sensitive_headers:
            if header in sanitized:
                sanitized[header] = '*****'
                
        return sanitized


# Singleton instance for global use
allure_reporter = AllureReporter()
