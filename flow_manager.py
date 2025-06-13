"""
Flow Manager for QA Bot - Allows defining and updating test flows
"""
import json
import yaml
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

class FlowManager:
    """Manages test flows for the QA Bot"""
    
    def __init__(self, flows_dir: str = "flows"):
        """Initialize the flow manager"""
        self.flows_dir = Path(flows_dir)
        self.flows_dir.mkdir(exist_ok=True)
        # Only create subdirectories for prod and uat
        for env in ["prod", "uat"]:
            (self.flows_dir / env).mkdir(exist_ok=True)
    
    def load_flow(self, flow_name: str, environment: str = "prod") -> Dict:
        """
        Load a flow definition from file
        
        Args:
            flow_name: Name of the flow to load
            environment: Environment to load flow for (prod, uat)
            
        Returns:
            Flow definition as a dictionary
        """
        # Try both YAML and JSON formats
        flow_path_yaml = self.flows_dir / environment / f"{flow_name}.yaml"
        flow_path_json = self.flows_dir / environment / f"{flow_name}.json"
        
        if flow_path_yaml.exists():
            with open(flow_path_yaml, 'r') as f:
                return yaml.safe_load(f)
        elif flow_path_json.exists():
            with open(flow_path_json, 'r') as f:
                return json.load(f)
        else:
            raise FileNotFoundError(f"Flow '{flow_name}' not found for environment '{environment}'")
    
    def save_flow(self, flow_name: str, flow_data: Dict, environment: str = "prod") -> str:
        """
        Save a flow definition to file
        
        Args:
            flow_name: Name of the flow to save
            flow_data: Flow definition data
            environment: Environment to save flow for (prod, uat)
            
        Returns:
            Path to the saved flow file
        """
        # Add metadata
        flow_data["metadata"] = {
            "last_updated": datetime.now().isoformat(),
            "environment": environment
        }
        
        # Save as YAML for better readability
        flow_path = self.flows_dir / environment / f"{flow_name}.yaml"
        with open(flow_path, 'w') as f:
            yaml.dump(flow_data, f, default_flow_style=False)
        
        return str(flow_path)
    
    def list_flows(self, environment: Optional[str] = None) -> Dict[str, List[str]]:
        """
        List all available flows
        
        Args:
            environment: Optional environment to filter by
            
        Returns:
            Dictionary of environments and their flows
        """
        result = {}
        
        if environment:
            environments = [environment]
        else:
            environments = ["prod", "uat"]
        
        for env in environments:
            env_dir = self.flows_dir / env
            if env_dir.exists():
                flows = []
                for file_path in env_dir.glob("*.*"):
                    if file_path.suffix.lower() in [".yaml", ".json"]:
                        flows.append(file_path.stem)
                result[env] = sorted(flows)
        
        return result
    
    def copy_flow(self, flow_name: str, source_env: str, target_env: str) -> str:
        """
        Copy a flow from one environment to another
        
        Args:
            flow_name: Name of the flow to copy
            source_env: Source environment (prod, uat)
            target_env: Target environment (prod, uat)
            
        Returns:
            Path to the new flow file
        """
        flow_data = self.load_flow(flow_name, source_env)
        return self.save_flow(flow_name, flow_data, target_env)
    
    def create_template_flow(self, flow_name: str, environment: str = "prod") -> str:
        """
        Create a template flow
        
        Args:
            flow_name: Name of the flow to create
            environment: Environment to create flow in (prod, uat)
            
        Returns:
            Path to the created flow file
        """
        template_flow = {
            "name": flow_name,
            "description": "Test flow for " + flow_name,
            "base_url": "https://example.com",
            "steps": [
                {
                    "name": "Navigate to home page",
                    "action": "navigate",
                    "url": "/"
                },
                {
                    "name": "Check UI elements",
                    "action": "check_ui"
                },
                {
                    "name": "Test responsive design",
                    "action": "test_responsive"
                }
            ],
            "selectors": {
                "login": {
                    "username": "input[type='email'], input[name='username']",
                    "password": "input[type='password']",
                    "submit": "button[type='submit']"
                }
            }
        }
        
        return self.save_flow(flow_name, template_flow, environment)


class FlowExecutor:
    """Executes test flows using the QA Bot"""
    
    def __init__(self, qa_bot, flow_manager=None):
        """
        Initialize the flow executor
        
        Args:
            qa_bot: Instance of QA Bot to use for execution
            flow_manager: Optional flow manager to use
        """
        self.qa_bot = qa_bot
        self.flow_manager = flow_manager or FlowManager()
    
    def safe_append(self, results: Dict, key: str, value: Dict) -> None:
        """Safely append a value to a list in the results dictionary.
        
        Args:
            results: Results dictionary
            key: Key of the list to append to
            value: Value to append
        """
        try:
            # Initialize if key doesn't exist
            if key not in results:
                results[key] = []
            
            # Ensure the value at key is a list
            if not isinstance(results[key], list):
                print(f"[WARNING] results['{key}'] is not a list. Resetting to empty list.")
                results[key] = []
            
            # Append the value
            results[key].append(value)
        except Exception as e:
            print(f"[WARNING] Failed to append to results['{key}']: {str(e)}")
            # Try to recover by initializing
            try:
                results[key] = [value]
            except Exception as e2:
                print(f"[ERROR] Could not recover from append failure: {str(e2)}")
    
    async def execute_flow(self, flow_name: str, environment: str = "prod", 
                          credentials: Dict = None) -> Dict:
        """
        Execute a flow by name
        
        Args:
            flow_name: Name of the flow to execute
            environment: Environment to execute in (prod, uat)
            credentials: Optional login credentials
            
        Returns:
            Flow execution results
        """
        # Load the flow
        flow_data = self.flow_manager.load_flow(flow_name, environment)
        
        # Initialize results with proper structure
        results = {
            "flow_name": flow_name,
            "environment": environment,
            "timestamp": datetime.now().isoformat(),
            "passed": [],
            "failed": [],
            "skipped": [],
            "accessibility_violations": []
        }
        
        # Set base URL
        if "base_url" in flow_data:
            self.qa_bot.base_url = flow_data["base_url"]
        
        # Make sure qa_bot.results is initialized if it doesn't exist
        if not hasattr(self.qa_bot, 'results') or self.qa_bot.results is None:
            from qa_bot import TestResults
            self.qa_bot.results = TestResults(website=self.qa_bot.base_url)
        
        # Execute login if credentials provided
        if credentials:
            login_url = flow_data.get("login_url", self.qa_bot.base_url)
            login_success = await self.qa_bot.login(login_url, credentials)
            if not login_success:
                self.safe_append(results, "failed", {
                    "step": "Login",
                    "error": "Login failed"
                })
                # Also add to qa_bot.results for report generation
                if hasattr(self.qa_bot.results, 'failed') and isinstance(self.qa_bot.results.failed, list):
                    self.qa_bot.results.failed.append({
                        "step": "Login",
                        "error": "Login failed"
                    })
                return results
        
        # Execute each step in the flow
        skip_remaining = False
        for step in flow_data.get("steps", []):
            importance = step.get("importance", "normal") if step else "normal"
            if skip_remaining and importance != "blocking":
                self.safe_append(results, "skipped", {
                    "step": step.get("name", "Unnamed step"),
                    "reason": "Skipped due to blocking failure",
                    "importance": importance
                })
                continue
            try:
                # Before executing a step, check if it's a 'navigate to login page' and user is already logged in
                if step.get('action') == 'navigate' and 'login' in step.get('name', '').lower():
                    if hasattr(self.qa_bot, 'is_logged_in') and await self.qa_bot.is_logged_in():
                        self.qa_bot.results.passed.append({
                            'step': step.get('name', 'Navigate to login page'),
                            'status': 'Skipped (already logged in)'
                        })
                        continue
                step_name = step.get("name", "Unknown step") if step else "Unknown step"
                action = step.get("action", "") if step else ""
                step_start = datetime.now()
                if action == "navigate":
                    url = step.get("url", "/") if step else "/"
                    if not url.startswith("http"):
                        url = f"{self.qa_bot.base_url.rstrip('/')}/{url.lstrip('/')}"
                    for attempt in range(2):
                        try:
                            success = await self.qa_bot.navigate_to(url)
                            break
                        except Exception as e:
                            if attempt == 1:
                                duration = (datetime.now() - step_start).total_seconds()
                                if "failed" not in results:
                                    results["failed"] = []
                                if isinstance(results["failed"], list):
                                    results["failed"].append({"step": step_name, "error": f"Navigation error (attempt {attempt+1}): {str(e)}", "duration": duration, "importance": importance})
                                else:
                                    print("DEBUG: results['failed'] is not a list!")
                                success = False
                    duration = (datetime.now() - step_start).total_seconds()
                    if success:
                        self.safe_append(results, "passed", {
                            "step": step_name,
                            "duration": duration,
                            "importance": importance
                        })
                    else:
                        self.safe_append(results, "failed", {
                            "step": step_name,
                            "error": "Navigation failed",
                            "duration": duration,
                            "importance": importance
                        })
                    # After each failure, if importance is 'blocking', set skip_remaining = True
                    if results["failed"] and results["failed"][-1]["step"] == step_name and importance == "blocking":
                        results["failed"][-1]["importance"] = importance
                        skip_remaining = True
                    elif results["failed"] and results["failed"][-1]["step"] == step_name:
                        results["failed"][-1]["importance"] = importance
                elif action == "check_ui":
                    for attempt in range(2):
                        try:
                            await self.qa_bot.check_ui_elements()
                            duration = (datetime.now() - step_start).total_seconds()
                            self.safe_append(results, "passed", {
                                "step": step_name,
                                "duration": duration,
                                "importance": importance
                            })
                            # Also add to qa_bot.results for report generation
                            if hasattr(self.qa_bot.results, 'passed') and isinstance(self.qa_bot.results.passed, list):
                                self.qa_bot.results.passed.append({
                                    "step": step_name,
                                    "duration": duration
                                })
                            break
                        except Exception as e:
                            if attempt == 1:
                                duration = (datetime.now() - step_start).total_seconds()
                                if "failed" not in results:
                                    results["failed"] = []
                                if isinstance(results["failed"], list):
                                    results["failed"].append({"step": step_name, "error": f"UI check error (attempt {attempt+1}): {str(e)}", "duration": duration, "importance": importance})
                                else:
                                    print("DEBUG: results['failed'] is not a list!")
                                # Also add to qa_bot.results for report generation
                                if hasattr(self.qa_bot.results, 'failed') and isinstance(self.qa_bot.results.failed, list):
                                    self.qa_bot.results.failed.append({
                                        "step": step_name,
                                        "error": f"UI check error: {str(e)}",
                                        "duration": duration
                                    })
                    # After each failure, if importance is 'blocking', set skip_remaining = True
                    if results["failed"] and results["failed"][-1]["step"] == step_name and importance == "blocking":
                        results["failed"][-1]["importance"] = importance
                        skip_remaining = True
                    elif results["failed"] and results["failed"][-1]["step"] == step_name:
                        results["failed"][-1]["importance"] = importance
                elif action == "test_responsive":
                    url = step.get("url") if step else None
                    for attempt in range(2):
                        try:
                            result = await self.qa_bot.test_responsive_design(url=url)
                            duration = (datetime.now() - step_start).total_seconds()
                            self.safe_append(results, "passed", {
                                "step": step_name,
                                "duration": duration,
                                "importance": importance
                            })
                            # Also add to qa_bot.results for report generation
                            if hasattr(self.qa_bot.results, 'passed') and isinstance(self.qa_bot.results.passed, list):
                                self.qa_bot.results.passed.append({
                                    "step": step_name,
                                    "duration": duration
                                })
                            break
                        except Exception as e:
                            if attempt == 1:
                                duration = (datetime.now() - step_start).total_seconds()
                                if "failed" not in results:
                                    results["failed"] = []
                                if isinstance(results["failed"], list):
                                    results["failed"].append({"step": step_name, "error": f"Responsive test error (attempt {attempt+1}): {str(e)}", "duration": duration, "importance": importance})
                                else:
                                    print("DEBUG: results['failed'] is not a list!")
                                # Also add to qa_bot.results for report generation
                                if hasattr(self.qa_bot.results, 'failed') and isinstance(self.qa_bot.results.failed, list):
                                    self.qa_bot.results.failed.append({
                                        "step": step_name,
                                        "error": f"Responsive test error: {str(e)}",
                                        "duration": duration
                                    })
                    # After each failure, if importance is 'blocking', set skip_remaining = True
                    if results["failed"] and results["failed"][-1]["step"] == step_name and importance == "blocking":
                        results["failed"][-1]["importance"] = importance
                        skip_remaining = True
                elif action == "check_links":
                    for attempt in range(2):
                        try:
                            await self.qa_bot.check_for_broken_links()
                            duration = (datetime.now() - step_start).total_seconds()
                            self.safe_append(results, "passed", {
                                "step": step_name,
                                "duration": duration,
                                "importance": importance
                            })
                            break
                        except Exception as e:
                            if attempt == 1:
                                duration = (datetime.now() - step_start).total_seconds()
                                if "failed" not in results:
                                    results["failed"] = []
                                if isinstance(results["failed"], list):
                                    results["failed"].append({"step": step_name, "error": f"Link check error (attempt {attempt+1}): {str(e)}", "duration": duration, "importance": importance})
                                else:
                                    print("DEBUG: results['failed'] is not a list!")
                    # After each failure, if importance is 'blocking', set skip_remaining = True
                    if results["failed"] and results["failed"][-1]["step"] == step_name and importance == "blocking":
                        results["failed"][-1]["importance"] = importance
                        skip_remaining = True
                elif action == "fill_form":
                    form_selector = step.get("form_selector", "form") if step else "form"
                    fields = step.get("fields", {}) if step else {}
                    for attempt in range(2):
                        try:
                            await self.qa_bot.test_form_submission(form_selector, fields)
                            duration = (datetime.now() - step_start).total_seconds()
                            self.safe_append(results, "passed", {
                                "step": step_name,
                                "duration": duration,
                                "importance": importance
                            })
                            break
                        except Exception as e:
                            if attempt == 1:
                                duration = (datetime.now() - step_start).total_seconds()
                                if "failed" not in results:
                                    results["failed"] = []
                                if isinstance(results["failed"], list):
                                    results["failed"].append({"step": step_name, "error": f"Form fill error (attempt {attempt+1}): {str(e)}", "duration": duration, "importance": importance})
                                else:
                                    print("DEBUG: results['failed'] is not a list!")
                    # After each failure, if importance is 'blocking', set skip_remaining = True
                    if results["failed"] and results["failed"][-1]["step"] == step_name and importance == "blocking":
                        results["failed"][-1]["importance"] = importance
                        skip_remaining = True
                elif action == "click":
                    selector = step.get("selector") if step else None
                    if selector and self.qa_bot.page:
                        for attempt in range(2):
                            try:
                                await self.qa_bot.page.click(selector, timeout=10000)
                                if step.get("wait_for_navigation", False):
                                    await self.qa_bot.page.wait_for_load_state("networkidle", timeout=15000)
                                duration = (datetime.now() - step_start).total_seconds()
                                self.safe_append(results, "passed", {
                                    "step": step_name,
                                    "duration": duration,
                                    "importance": importance
                                })
                                break
                            except Exception as e:
                                if attempt == 1:
                                    duration = (datetime.now() - step_start).total_seconds()
                                    html_snippet = await self.qa_bot.page.content()
                                    screenshot_path = f"screenshots/{step_name.replace(' ', '_')}_{int(datetime.now().timestamp())}.png"
                                    os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                                    await self.qa_bot.page.screenshot(path=screenshot_path, full_page=True)
                                    xpath_suggestion = f"//*[contains(@class, '{selector.strip('.')}' )]"
                                    if "failed" not in results:
                                        results["failed"] = []
                                    if isinstance(results["failed"], list):
                                        results["failed"].append({
                                            "step": step_name,
                                            "error": f"Click error (attempt {attempt+1}): {str(e)}. XPath suggestion: {xpath_suggestion}",
                                            "screenshot": screenshot_path,
                                            "html_snippet": html_snippet[:1000],
                                            "duration": duration,
                                            "importance": importance
                                        })
                                    else:
                                        print("DEBUG: results['failed'] is not a list!")
                                    # After each failure, if importance is 'blocking', set skip_remaining = True
                                    if results["failed"] and results["failed"][-1]["step"] == step_name and importance == "blocking":
                                        results["failed"][-1]["importance"] = importance
                                        skip_remaining = True
                                    elif results["failed"] and results["failed"][-1]["step"] == step_name:
                                        results["failed"][-1]["importance"] = importance
                    else:
                        duration = (datetime.now() - step_start).total_seconds()
                        if "failed" not in results:
                            results["failed"] = []
                        if isinstance(results["failed"], list):
                            results["failed"].append({"step": step_name, "error": "Missing selector or page not available", "duration": duration, "importance": importance})
                        else:
                            print("DEBUG: results['failed'] is not a list!")
                        # After each failure, if importance is 'blocking', set skip_remaining = True
                        if results["failed"] and results["failed"][-1]["step"] == step_name and importance == "blocking":
                            results["failed"][-1]["importance"] = importance
                            skip_remaining = True
                elif action == "wait":
                    duration_ms = step.get("duration", 1000) if step else 1000
                    try:
                        await self.qa_bot.page.wait_for_timeout(duration_ms)
                        duration = (datetime.now() - step_start).total_seconds()
                        self.safe_append(results, "passed", {
                            "step": step_name,
                            "duration": duration,
                            "importance": importance
                        })
                    except Exception as e:
                        duration = (datetime.now() - step_start).total_seconds()
                        if "failed" not in results:
                            results["failed"] = []
                        if isinstance(results["failed"], list):
                            results["failed"].append({"step": step_name, "error": f"Wait error: {str(e)}", "duration": duration, "importance": importance})
                        else:
                            print("DEBUG: results['failed'] is not a list!")
                        # After each failure, if importance is 'blocking', set skip_remaining = True
                        if results["failed"] and results["failed"][-1]["step"] == step_name and importance == "blocking":
                            results["failed"][-1]["importance"] = importance
                            skip_remaining = True
                elif action == "check_element":
                    selector = step.get("selector") if step else None
                    expected_visible = step.get("visible", True) if step else True
                    if selector and self.qa_bot.page:
                        for attempt in range(2):
                            try:
                                is_visible = await self.qa_bot.page.is_visible(selector, timeout=10000)
                                if is_visible == expected_visible:
                                    duration = (datetime.now() - step_start).total_seconds()
                                    self.safe_append(results, "passed", {
                                        "step": step_name,
                                        "duration": duration,
                                        "importance": importance
                                    })
                                else:
                                    state = "visible" if expected_visible else "invisible"
                                    duration = (datetime.now() - step_start).total_seconds()
                                    if "failed" not in results:
                                        results["failed"] = []
                                    if isinstance(results["failed"], list):
                                        results["failed"].append({"step": step_name, "error": f"Element should be {state}", "duration": duration, "importance": importance})
                                    else:
                                        print("DEBUG: results['failed'] is not a list!")
                                break
                            except Exception as e:
                                if attempt == 1:
                                    duration = (datetime.now() - step_start).total_seconds()
                                    html_snippet = await self.qa_bot.page.content()
                                    screenshot_path = f"screenshots/{step_name.replace(' ', '_')}_{int(datetime.now().timestamp())}.png"
                                    os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                                    await self.qa_bot.page.screenshot(path=screenshot_path, full_page=True)
                                    xpath_suggestion = f"//*[contains(@class, '{selector.strip('.')}' )]"
                                    if "failed" not in results:
                                        results["failed"] = []
                                    if isinstance(results["failed"], list):
                                        results["failed"].append({
                                            "step": step_name,
                                            "error": f"Element check error (attempt {attempt+1}): {str(e)}. XPath suggestion: {xpath_suggestion}",
                                            "screenshot": screenshot_path,
                                            "html_snippet": html_snippet[:1000],
                                            "duration": duration,
                                            "importance": importance
                                        })
                                    else:
                                        print("DEBUG: results['failed'] is not a list!")
                                    # After each failure, if importance is 'blocking', set skip_remaining = True
                                    if results["failed"] and results["failed"][-1]["step"] == step_name and importance == "blocking":
                                        results["failed"][-1]["importance"] = importance
                                        skip_remaining = True
                                    elif results["failed"] and results["failed"][-1]["step"] == step_name:
                                        results["failed"][-1]["importance"] = importance
                    else:
                        duration = (datetime.now() - step_start).total_seconds()
                        if "failed" not in results:
                            results["failed"] = []
                        if isinstance(results["failed"], list):
                            results["failed"].append({"step": step_name, "error": "Missing selector or page not available", "duration": duration, "importance": importance})
                        else:
                            print("DEBUG: results['failed'] is not a list!")
                        # After each failure, if importance is 'blocking', set skip_remaining = True
                        if results["failed"] and results["failed"][-1]["step"] == step_name and importance == "blocking":
                            results["failed"][-1]["importance"] = importance
                            skip_remaining = True
                elif action == "check_accessibility":
                    step_start = datetime.now()
                    try:
                        violations = await self.qa_bot.check_accessibility()
                        duration = (datetime.now() - step_start).total_seconds()
                        if violations:
                            # Count critical/serious
                            criticals = [v for v in violations if v.get('impact') in ('critical', 'serious')]
                            if criticals:
                                if "failed" not in results:
                                    results["failed"] = []
                                if isinstance(results["failed"], list):
                                    results["failed"].append({
                                        "step": step_name,
                                        "error": f"Accessibility violations: {len(criticals)} critical/serious issues",
                                        "violations": criticals,
                                        "duration": duration,
                                        "importance": importance
                                    })
                                else:
                                    print("DEBUG: results['failed'] is not a list!")
                            else:
                                self.safe_append(results, "passed", {
                                    "step": step_name,
                                    "duration": duration,
                                    "violations": violations,
                                    "importance": importance
                                })
                        else:
                            self.safe_append(results, "passed", {
                                "step": step_name,
                                "duration": duration,
                                "importance": importance
                            })
                    except Exception as e:
                        duration = (datetime.now() - step_start).total_seconds()
                        if "failed" not in results:
                            results["failed"] = []
                        if isinstance(results["failed"], list):
                            results["failed"].append({"step": step_name, "error": f"Accessibility check error: {str(e)}", "duration": duration, "importance": importance})
                        else:
                            print("DEBUG: results['failed'] is not a list!")
                        # After each failure, if importance is 'blocking', set skip_remaining = True
                        if results["failed"] and results["failed"][-1]["step"] == step_name and importance == "blocking":
                            results["failed"][-1]["importance"] = importance
                            skip_remaining = True
                elif action == "assert_text":
                    selector = step.get("selector") if step else None
                    expected_text = step.get("text") if step else None
                    should_exist = step.get("should_exist", True) if step else True
                    step_start = datetime.now()
                    try:
                        if selector and expected_text and self.qa_bot.page:
                            try:
                                content = await self.qa_bot.page.inner_text(selector)
                                found = expected_text in content
                            except Exception as e:
                                # Auto-heal: suggest XPath, screenshot, HTML snippet
                                duration = (datetime.now() - step_start).total_seconds()
                                html_snippet = await self.qa_bot.page.content()
                                screenshot_path = f"screenshots/{step_name.replace(' ', '_')}_{int(datetime.now().timestamp())}.png"
                                os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                                await self.qa_bot.page.screenshot(path=screenshot_path, full_page=True)
                                xpath_suggestion = f"//*[contains(text(), '{expected_text}') or contains(@class, '{selector.strip('.')}' )]"
                                if "failed" not in results:
                                    results["failed"] = []
                                if isinstance(results["failed"], list):
                                    results["failed"].append({
                                        "step": step_name,
                                        "error": f"Selector '{selector}' not found. XPath suggestion: {xpath_suggestion}",
                                        "screenshot": screenshot_path,
                                        "html_snippet": html_snippet[:1000],
                                        "duration": duration,
                                        "importance": importance
                                    })
                                else:
                                    print("DEBUG: results['failed'] is not a list!")
                                # After each failure, if importance is 'blocking', set skip_remaining = True
                                if results["failed"] and results["failed"][-1]["step"] == step_name and importance == "blocking":
                                    results["failed"][-1]["importance"] = importance
                                    skip_remaining = True
                                continue
                            duration = (datetime.now() - step_start).total_seconds()
                            if (found and should_exist) or (not found and not should_exist):
                                self.safe_append(results, "passed", {
                                    "step": step_name,
                                    "duration": duration,
                                    "importance": importance
                                })
                            else:
                                if "failed" not in results:
                                    results["failed"] = []
                                if isinstance(results["failed"], list):
                                    results["failed"].append({"step": step_name, "error": f"Text '{expected_text}' not found in {selector}", "duration": duration, "importance": importance})
                                else:
                                    print("DEBUG: results['failed'] is not a list!")
                        else:
                            duration = (datetime.now() - step_start).total_seconds()
                            if "failed" not in results:
                                results["failed"] = []
                            if isinstance(results["failed"], list):
                                results["failed"].append({"step": step_name, "error": "Missing selector or text for assert_text", "duration": duration, "importance": importance})
                                print("DEBUG: results['failed'] is not a list!")
                    except Exception as e:
                        duration = (datetime.now() - step_start).total_seconds()
                        if "failed" not in results:
                            results["failed"] = []
                        if isinstance(results["failed"], list):
                            results["failed"].append({"step": step_name, "error": f"Assert text error: {str(e)}", "duration": duration, "importance": importance})
                            print("DEBUG: results['failed'] is not a list!")
                        # After each failure, if importance is 'blocking', set skip_remaining = True
                        if results["failed"] and results["failed"][-1]["step"] == step_name and importance == "blocking":
                            results["failed"][-1]["importance"] = importance
                            skip_remaining = True
                elif action == "screenshot":
                    step_start = datetime.now()
                    try:
                        if self.qa_bot.page:
                            screenshot_path = f"screenshots/{step_name.replace(' ', '_')}_{int(datetime.now().timestamp())}.png"
                            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                            await self.qa_bot.page.screenshot(path=screenshot_path, full_page=True)
                            duration = (datetime.now() - step_start).total_seconds()
                            self.safe_append(results, "passed", {
                                "step": step_name,
                                "screenshot": screenshot_path,
                                "duration": duration,
                                "importance": importance
                            })
                        else:
                            duration = (datetime.now() - step_start).total_seconds()
                            if "failed" not in results:
                                results["failed"] = []
                            if isinstance(results["failed"], list):
                                results["failed"].append({"step": step_name, "error": "No page available for screenshot", "duration": duration, "importance": importance})
                                print("DEBUG: results['failed'] is not a list!")
                    except Exception as e:
                        duration = (datetime.now() - step_start).total_seconds()
                        if "failed" not in results:
                            results["failed"] = []
                        if isinstance(results["failed"], list):
                            results["failed"].append({"step": step_name, "error": f"Screenshot error: {str(e)}", "duration": duration, "importance": importance})
                            print("DEBUG: results['failed'] is not a list!")
                        # After each failure, if importance is 'blocking', set skip_remaining = True
                        if results["failed"] and results["failed"][-1]["step"] == step_name and importance == "blocking":
                            results["failed"][-1]["importance"] = importance
                            skip_remaining = True
                elif action == "check_performance":
                    step_start = datetime.now()
                    try:
                        if self.qa_bot.page:
                            perf = await self.qa_bot.page.evaluate("""
                                () => {
                                    const perf = window.performance.timing;
                                    return {
                                        navigationStart: perf.navigationStart,
                                        domContentLoaded: perf.domContentLoadedEventEnd - perf.navigationStart,
                                        loadEvent: perf.loadEventEnd - perf.navigationStart,
                                        responseStart: perf.responseStart - perf.navigationStart,
                                        responseEnd: perf.responseEnd - perf.navigationStart
                                    };
                                }
                            """)
                            duration = (datetime.now() - step_start).total_seconds()
                            self.safe_append(results, "passed", {
                                "step": step_name,
                                "performance": perf,
                                "duration": duration,
                                "importance": importance
                            })
                        else:
                            duration = (datetime.now() - step_start).total_seconds()
                            if "failed" not in results:
                                results["failed"] = []
                            if isinstance(results["failed"], list):
                                results["failed"].append({"step": step_name, "error": "No page available for performance check", "duration": duration, "importance": importance})
                                print("DEBUG: results['failed'] is not a list!")
                    except Exception as e:
                        duration = (datetime.now() - step_start).total_seconds()
                        if "failed" not in results:
                            results["failed"] = []
                        if isinstance(results["failed"], list):
                            results["failed"].append({"step": step_name, "error": f"Performance check error: {str(e)}", "duration": duration, "importance": importance})
                            print("DEBUG: results['failed'] is not a list!")
                        # After each failure, if importance is 'blocking', set skip_remaining = True
                        if results["failed"] and results["failed"][-1]["step"] == step_name and importance == "blocking":
                            results["failed"][-1]["importance"] = importance
                            skip_remaining = True
                elif action == "auto_crawl":
                    # Auto-crawl logic
                    max_pages = step.get("max_pages", 10)
                    # Support custom nav_selector from flow YAML
                    nav_selector = flow_data.get("nav_selector")
                    # Discover links from the current page
                    links = await self.qa_bot.discover_links(max_pages, nav_selector)
                    if not links:
                        self.safe_append(results, "failed", {
                            "step": step_name,
                            "error": "No internal links found to crawl",
                            "duration": 0,
                            "importance": "critical"
                        })
                    else:
                        for i, link in enumerate(links):
                            crawl_step_name = f"Crawl Page {i+1}: {link}"
                            crawl_start = datetime.now()
                            try:
                                nav_success = await self.qa_bot.navigate_to(link)
                                nav_duration = (datetime.now() - crawl_start).total_seconds()
                                if nav_success:
                                    # UI check
                                    try:
                                        await self.qa_bot.check_ui_elements()
                                    except Exception as e:
                                        self.safe_append(results, "failed", {
                                            "step": crawl_step_name + " (UI check)",
                                            "error": str(e),
                                            "duration": nav_duration,
                                            "importance": "normal"
                                        })
                                    # Responsive check
                                    try:
                                        await self.qa_bot.test_responsive_design(url=link)
                                    except Exception as e:
                                        self.safe_append(results, "failed", {
                                            "step": crawl_step_name + " (Responsive check)",
                                            "error": str(e),
                                            "duration": nav_duration,
                                            "importance": "normal"
                                        })
                                    self.safe_append(results, "passed", {
                                        "step": crawl_step_name,
                                        "url": link,
                                        "duration": nav_duration,
                                        "importance": "normal"
                                    })
                                else:
                                    self.safe_append(results, "failed", {
                                        "step": crawl_step_name,
                                        "url": link,
                                        "error": "Navigation failed",
                                        "duration": nav_duration,
                                        "importance": "normal"
                                    })
                            except Exception as e:
                                nav_duration = (datetime.now() - crawl_start).total_seconds()
                                self.safe_append(results, "failed", {
                                    "step": crawl_step_name,
                                    "url": link,
                                    "error": str(e),
                                    "duration": nav_duration,
                                    "importance": "normal"
                                })
                else:
                    duration = (datetime.now() - step_start).total_seconds()
                    self.safe_append(results, "skipped", {
                        "step": step_name,
                        "reason": f"Unknown action: {action}",
                        "duration": duration,
                        "importance": importance
                    })
            except Exception as e:
                duration = (datetime.now() - step_start).total_seconds()
                if "failed" not in results:
                    results["failed"] = []
                if isinstance(results["failed"], list):
                    # Always include step name and error
                    fail_entry = {
                        "step": step_name if step_name else "[Step name missing]",
                        "error": str(e) if str(e) else "[No error message provided]",
                        "duration": duration,
                        "importance": importance
                    }
                    results["failed"].append(fail_entry)
                else:
                    print("DEBUG: results['failed'] is not a list!")
        
        # After all steps, add coverage summary
        total_steps = len(flow_data.get("steps", []))
        passed_steps = len(results["passed"])
        failed_steps = len(results["failed"])
        skipped_steps = len(results["skipped"])
        results["coverage_summary"] = {
            "total": total_steps,
            "passed": passed_steps,
            "failed": failed_steps,
            "skipped": skipped_steps,
            "failed_steps": [step["step"] for step in results["failed"]],
            "skipped_steps": [step["step"] for step in results["skipped"]]
        }
        
        # Transfer any UI or responsive test results to qa_bot.results if they're not already there
        # This ensures the HTML report will include all the data
        if hasattr(self.qa_bot, 'ui_issue_summary') and self.qa_bot.ui_issue_summary and hasattr(self.qa_bot.results, 'ui_issue_summary'):
            self.qa_bot.results.ui_issue_summary = self.qa_bot.ui_issue_summary
            
        if hasattr(self.qa_bot, 'responsive_issue_summary') and self.qa_bot.responsive_issue_summary and hasattr(self.qa_bot.results, 'responsive_issue_summary'):
            self.qa_bot.results.responsive_issue_summary = self.qa_bot.responsive_issue_summary
            
        if hasattr(self.qa_bot, 'responsiveness_scores') and self.qa_bot.responsiveness_scores and hasattr(self.qa_bot.results, 'responsiveness_scores'):
            self.qa_bot.results.responsiveness_scores = self.qa_bot.responsiveness_scores
            
        if hasattr(self.qa_bot, 'broken_links') and self.qa_bot.broken_links and hasattr(self.qa_bot.results, 'broken_links'):
            self.qa_bot.results.broken_links = self.qa_bot.broken_links
            
        if hasattr(self.qa_bot, 'js_errors') and self.qa_bot.js_errors and hasattr(self.qa_bot.results, 'js_errors'):
            self.qa_bot.results.js_errors = self.qa_bot.js_errors
            
        return results 