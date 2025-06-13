#!/usr/bin/env python3
"""
AI-Powered End-to-End QA Testing Bot for Websites
"""
import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import typer
from loguru import logger
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Response
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
import yaml
import ssl
import socket
from urllib.parse import urlparse
import re
import builtins

# Import flow manager components
from flow_manager import FlowManager, FlowExecutor

# Configure logger
logger.remove()
logger.add("qa_bot.log", rotation="10 MB")

console = Console()
app = typer.Typer(help="AI-Powered End-to-End QA Testing Bot for Websites")


class LoginCredentials(BaseModel):
    """Login credentials model"""
    username: str
    password: str
    username_selector: str = "input[name='email'], input[type='email'], input[name='username'], input[id='username'], input[id='email']"
    password_selector: str = "input[name='password'], input[type='password'], input[id='password']"
    submit_selector: str = "button[type='submit'], .btn-outline-primary, input[type='submit'], button.login-button, .login-form button, form button"


class TestResults(BaseModel):
    """Test results model"""
    timestamp: str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    website: str
    passed: List[Dict[str, Union[str, int, float]]] = []
    failed: List[Dict[str, Union[str, int, float]]] = []
    broken_links: List[str] = []
    slow_pages: List[Dict[str, Union[str, float]]] = []
    js_errors: List[Dict[str, str]] = []
    ssl_status: Dict[str, str] = {}
    performance_issues: List[Dict[str, str]] = []
    ui_issue_summary: Optional[List[Dict]] = None
    responsive_issue_summary: Optional[List[Dict]] = None
    warnings: List[Dict[str, str]] = []
    responsiveness_scores: Dict[str, Dict[str, Union[int, float]]] = {}
    interactive_results: List[Dict[str, Union[str, bool, float]]] = []
    interactive_results_by_page: Dict[str, List[Dict[str, Union[str, bool, float]]]] = {}
    performance_details: List[Dict[str, Union[str, float]]] = []


class QABot:
    """AI-Powered QA Testing Bot for Websites"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.results = None
        self.browser = None
        self.context = None
        self.page = None
        self.base_url = None
        self.visited_urls = set()
        self.js_errors = []
        self.ui_checked_pages = set()
        self.responsive_checked_pages = set()
        self.credentials = None  # Store credentials for use in form submission

    async def setup(self):
        """Set up the browser"""
        playwright = await async_playwright().start()
        browser_type = playwright.chromium
        
        # Configure browser launch options
        launch_options = {
            "headless": self.headless,
            "args": [
                "--disable-dev-shm-usage",  # Overcome limited resource issues
                "--no-sandbox",  # Required in some environments
                "--disable-setuid-sandbox",
                "--disable-gpu",  # Helps avoid GPU issues
                "--disable-software-rasterizer",
            ]
        }
        
        if not self.headless:
            # Additional options for headed mode
            launch_options["args"].extend([
                "--start-maximized",
                "--window-size=1920,1080"
            ])
        
        self.browser = await browser_type.launch(**launch_options)
        
        # Configure browser context
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "ignore_https_errors": True,  # Handle SSL cert issues gracefully
            "java_script_enabled": True,
            "bypass_csp": True,  # Bypass Content Security Policy for testing
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        
        self.context = await self.browser.new_context(**context_options)
        
        # Create page and set up listeners
        self.page = await self.context.new_page()
        self.page.on("console", self._handle_console_message)
        self.page.on("pageerror", self._handle_page_error)
        
        # Set default timeouts
        self.page.set_default_timeout(30000)  # 30 seconds
        self.page.set_default_navigation_timeout(30000)
        
    async def _handle_console_message(self, msg):
        """Handle console messages"""
        if msg.type == "error":
            self.js_errors.append({
                "url": self.page.url,
                "message": msg.text
            })
            logger.error(f"Console error on {self.page.url}: {msg.text}")

    async def _handle_page_error(self, error):
        """Handle page errors"""
        self.js_errors.append({
            "url": self.page.url,
            "message": str(error)
        })
        logger.error(f"Page error on {self.page.url}: {error}")
        
    async def find_and_login_homepage(self, url: str, credentials: LoginCredentials, post_login_selector: str = '#main-menu-navigation') -> bool:
        """Robust login for CSRF/session-protected forms: waits for form, fills only username/password, submits by pressing Enter and clicking, with debug output."""
        try:
            await self.page.goto(url, timeout=60000)
            await self.page.wait_for_load_state("domcontentloaded")
            await self.page.wait_for_timeout(2000)  # Wait for dynamic content
            form = None
            username_selector = None
            password_selector = None
            username_selectors = [
                "input#email", "input[name='email']", "input[type='email']", "input[name='username']", "input[id='username']", "input[id='email']", "input[type='text']", "input[name*='user']", "input[name*='login']"
            ]
            password_selectors = [
                "input#password", "input[name='password']", "input[type='password']", "input[id='password']"
            ]
            for sel in username_selectors:
                try:
                    await self.page.wait_for_selector(sel, timeout=5000)
                    username_selector = sel
                    break
                except Exception:
                    continue
            for sel in password_selectors:
                try:
                    await self.page.wait_for_selector(sel, timeout=5000)
                    password_selector = sel
                    break
                except Exception:
                    continue
            if not username_selector or not password_selector:
                print(f'[DEBUG] Username or password field not found. Username selector: {username_selector}, Password selector: {password_selector}')
                return False
            username_el = await self.page.query_selector(username_selector)
            form = await username_el.evaluate_handle('el => el.closest("form")')
            if form:
                form_html = await form.evaluate('el => el.outerHTML')
                print(f'[DEBUG] Login form HTML before filling:\n{form_html}')
            await self.page.fill(username_selector, credentials.username)
            await self.page.wait_for_timeout(300)  # Mimic human typing delay
            await self.page.fill(password_selector, credentials.password)
            await self.page.wait_for_timeout(300)  # Mimic human typing delay
            if form:
                form_html_after = await form.evaluate('el => el.outerHTML')
                print(f'[DEBUG] Login form HTML after filling:\n{form_html_after}')
            # Try both pressing Enter and clicking the first visible/enabled submit button in parallel
            submit_selectors = [
                "button[type='submit']", "input[type='submit']", "button.btn-outline-primary", "button.login-button", ".login-form button", "form button", "button", ".btn", ".login-btn"
            ]
            found_buttons = []
            click_task = None
            for sel in submit_selectors:
                buttons = await self.page.query_selector_all(sel)
                for btn in buttons:
                    try:
                        is_in_form = await btn.evaluate('(el, form) => form && el.closest("form") === form', form)
                        if not is_in_form:
                            continue
                        visible = await btn.is_visible()
                        enabled = await btn.is_enabled()
                        text = await btn.inner_text() if hasattr(btn, 'inner_text') else ''
                        found_buttons.append((sel, text, visible, enabled))
                        if visible and enabled and not click_task:
                            print(f'[DEBUG] Clicking submit button with selector: {sel}, text: {text}')
                            click_task = btn.click()
                            break
                    except Exception as e:
                        print(f'[DEBUG] Error with button {sel}: {str(e)}')
                        continue
                if click_task:
                    break
            # Run both pressing Enter and clicking the button in parallel
            enter_task = self.page.focus(password_selector)
            await enter_task
            # Use asyncio.gather to run both tasks in parallel
            import asyncio
            results = await asyncio.gather(
                self.page.keyboard.press('Enter'),
                click_task if click_task else asyncio.sleep(0),
                return_exceptions=True
            )
            # Wait for either post-login selector or AJAX login (networkidle or DOM change)
            try:
                await self.page.wait_for_selector(post_login_selector, state='visible', timeout=8000)
                print(f'[DEBUG] Login successful: Found post-login selector {post_login_selector}')
                cookies = await self.context.cookies()
                print(f'[DEBUG] Cookies after login: {cookies}')
                local_storage = await self.page.evaluate('() => { let out = {}; for (let i=0; i<localStorage.length; ++i) { let k = localStorage.key(i); out[k] = localStorage.getItem(k); } return out; }')
                print(f'[DEBUG] localStorage after login: {local_storage}')
                return True
            except Exception:
                print(f'[DEBUG] Login failed: Post-login selector {post_login_selector} not found, checking for AJAX login...')
                try:
                    await self.page.wait_for_load_state('networkidle', timeout=5000)
                    await self.page.wait_for_selector(post_login_selector, state='visible', timeout=5000)
                    print(f'[DEBUG] Login successful (AJAX fallback): Found post-login selector {post_login_selector}')
                    cookies = await self.context.cookies()
                    print(f'[DEBUG] Cookies after login: {cookies}')
                    local_storage = await self.page.evaluate('() => { let out = {}; for (let i=0; i<localStorage.length; ++i) { let k = localStorage.key(i); out[k] = localStorage.getItem(k); } return out; }')
                    print(f'[DEBUG] localStorage after login: {local_storage}')
                    return True
                except Exception:
                    print(f'[DEBUG] Login failed: All robust login attempts exhausted')
                    cookies = await self.context.cookies()
                    print(f'[DEBUG] Cookies after failed login: {cookies}')
                    local_storage = await self.page.evaluate('() => { let out = {}; for (let i=0; i<localStorage.length; ++i) { let k = localStorage.key(i); out[k] = localStorage.getItem(k); } return out; }')
                    print(f'[DEBUG] localStorage after failed login: {local_storage}')
                    return False
        except Exception as e:
            logger.error(f"Homepage login attempt failed: {str(e)}")
            print(f'[DEBUG] Homepage login attempt failed: {str(e)}')
            return False

    async def try_login(self, url: str, credentials: LoginCredentials, post_login_selector: str = '#main-menu-navigation') -> bool:
        """Try to login using homepage first, then multiple strategies. Return True if login succeeds, False otherwise."""
        homepage_login = await self.find_and_login_homepage(url, credentials, post_login_selector=post_login_selector)
        if homepage_login:
            return True
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        login_paths = ["/login", "/signin", "/account/login", "/user/login", "/users/login", "/auth/login", "/sign-in", "/sign_in", "/log-in", "/log_in", "/admin/login", "/dashboard/login", "/session/new"]
        for path in login_paths:
            login_url = base + path
            try:
                console.print(f"[blue]Trying login at: {login_url}[/blue]")
                result = await self.find_and_login_homepage(login_url, credentials, post_login_selector=post_login_selector)
                if result:
                    return True
            except Exception as e:
                logger.warning(f"Login attempt failed at {login_url}: {str(e)}")
                continue
        return False

    async def check_ssl(self, url: str) -> Dict[str, str]:
        """Check SSL certificate status using direct socket/ssl (not Playwright)"""
        ssl_status = {"status": "unknown", "expiry": "unknown"}
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            port = parsed.port or 443
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    issuer = dict(x[0] for x in cert['issuer'])
                    not_after = cert['notAfter']
                    ssl_status = {
                        "status": "valid",
                        "issuer": issuer.get('organizationName', str(issuer)),
                        "expiry": not_after
                    }
        except Exception as e:
            ssl_status = {"status": "error", "message": str(e)}
        return ssl_status

    def _append_warning(self, step, reason):
        if not hasattr(self.results, 'warnings'):
            self.results.warnings = []
        self.results.warnings.append({"step": step, "reason": reason})

    async def navigate_to(self, url: str) -> bool:
        """Navigate to a specific URL and check for issues, with robust error/status logging and content verification."""
        if url in self.visited_urls:
            return True
        try:
            page_name = url.split('/')[-1]
            if not page_name:
                page_name = "Home"
            else:
                page_name = page_name.capitalize()
            test_name = f"Page Navigation: {page_name}"
            console.print(f"[blue]RUNNING TEST: {test_name}[/blue]")
            console.print(f"[blue]Navigating to {url}...[/blue]")
            if url.startswith('#') or (url.startswith(self.base_url) and '#' in url and url.split('#')[1]):
                self.results.passed.append({
                    "step": test_name,
                    "url": url,
                    "status": "Anchor navigation (no HTTP request)",
                    "load_time": "Not Applicable"
                })
                console.print(f"[green]✓ {test_name} - Anchor navigation (no HTTP request)[/green]")
                return True
            start_time = time.time()
            response = await self.page.goto(url, wait_until='networkidle', timeout=500000)
            await self.page.wait_for_timeout(5000)
            load_time = time.time() - start_time
            self.visited_urls.add(url)
            final_url = self.page.url
            status = response.status if response else 0
            # Check for redirect to login or error page
            redirected_to_login = 'login' in final_url.lower() and not url.lower().endswith('login')
            # Check for main content area
            main_content_found = False
            main_content_selectors = ['.main-content', '.content', '#main-menu-navigation', 'main', '.content-wrapper']
            for sel in main_content_selectors:
                try:
                    if await self.page.is_visible(sel):
                        main_content_found = True
                        break
                except Exception:
                    continue
            # --- ENHANCED: Stop if redirected to login page ---
            if redirected_to_login:
                self.results.failed.append({
                    "step": test_name,
                    "url": url,
                    "reason": "Redirected to login page (session lost)",
                    "final_url": final_url,
                    "load_time": round(load_time, 2),
                    "main_content_found": False,
                    "issues": [{"severity": "Critical", "message": "Redirected to login page (session lost)"}]
                })
                console.print(f"[red]✗ {test_name} - Failed: Redirected to login page (session lost) (Final URL: {final_url})[/red]")
                return False
            # --- ENHANCED: Stop if main content not found ---
            if not main_content_found:
                error_html = await self.page.content()
                self.results.failed.append({
                    "step": test_name,
                    "url": url,
                    "reason": "Main content area not found",
                    "final_url": final_url,
                    "load_time": round(load_time, 2),
                    "main_content_found": False,
                    "issues": [{"severity": "Critical", "message": "Main content area not found"}]
                })
                console.print(f"[red]✗ {test_name} - Failed: Main content area not found (Final URL: {final_url})[/red]")
                return False
            # If page is slow but accessible, mark as passed with warning
            result = {
                "step": test_name,
                "url": url,
                "status": status,
                "final_url": final_url,
                "main_content_found": main_content_found,
                "load_time": round(load_time, 2)
            }
            if load_time > 10:
                self.results.passed.append(result)
                self._append_warning(test_name, f"Page loaded slowly ({round(load_time, 2)}s)")
                console.print(f"[yellow]✓ {test_name} - Passed but slow ({round(load_time, 2)}s)[/yellow]")
            else:
                self.results.passed.append(result)
                console.print(f"[green]✓ {test_name} - Passed with status {status} ({round(load_time, 2)}s)[/green]")
            return True
        except Exception as e:
            logger.error(f"Navigation error to {url}: {str(e)}")
            try:
                safe_name = url.split('/')[-1].replace('/', '_').replace('?', '_')
                await self.page.screenshot(path=f"error_{safe_name}.png")
            except Exception:
                pass
            self._append_warning(test_name, f"Navigation error: {str(e)}")
            console.print(f"[yellow]⚠ {test_name} - Navigation warning: {str(e)}[/yellow]")
            return False

    async def inspect_login_page(self, url: str, use_ai: bool = True, ai_api_key: str = None) -> Dict[str, str]:
        """Inspect login page and suggest selectors (advanced heuristics + optional AI/ML for best accuracy)."""
        import re
        try:
            console.print(f"[bold blue]Inspecting login page at {url}...[/bold blue]")
            if self.page.url != url:
                await self.page.goto(url)
            forms = await self.page.query_selector_all('form')
            best_guess = {"username": None, "password": None, "submit": None}
            best_score = -1
            for form in forms:
                # Find all inputs in the form
                inputs = await form.query_selector_all('input')
                for inp in inputs:
                    inp_type = (await inp.get_attribute('type') or '').lower()
                    inp_name = (await inp.get_attribute('name') or '').lower()
                    inp_id = (await inp.get_attribute('id') or '').lower()
                    inp_placeholder = (await inp.get_attribute('placeholder') or '').lower()
                    inp_aria = (await inp.get_attribute('aria-label') or '').lower()
                    score = 0
                    if inp_type in ['email', 'text']:
                        score += 2
                    if re.search(r'user|email|login', inp_name):
                        score += 4
                    if re.search(r'user|email|login', inp_id):
                        score += 3
                    if re.search(r'user|email|login', inp_placeholder):
                        score += 2
                    if re.search(r'user|email|login', inp_aria):
                        score += 2
                    if score > best_score:
                        best_guess['username'] = inp
                        best_score = score
            return best_guess
        except Exception as e:
            console.print(f"[red]Error inspecting login page: {str(e)}[/red]")
            return {}

    async def discover_links(self, max_links: int = 10, nav_selector: str = None, sidebar_selector: str = None, main_content_selector: str = None, submenu_selector: str = None) -> List[str]:
        """Discover all visible <a>, clickable, sidebar, and submenu elements on homepage (one level deep, no recursion, generic for all sites). Uses precise selectors for your sidebar structure. After clicking, treat as a new page if URL or main content changes. Recursively click and test all visible submenu items. Logs all actions."""
        import time
        links = []  # Initialize the links list
        try:
            await self.page.wait_for_load_state("domcontentloaded")
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            await self.page.wait_for_timeout(2000)  # Wait 2 seconds for dynamic content
            # Scope sidebar discovery to #main-menu-navigation
            sidebar_container = await self.page.query_selector('#main-menu-navigation')
            if not sidebar_container:
                console.print("[yellow]Sidebar container #main-menu-navigation not found! Printing DOM for debugging:[/yellow]")
                dom = await self.page.content()
                logger.warning(f"Sidebar container missing DOM snapshot (truncated): {dom[:1000]}")
                return []
            # 1. Click all expanders to reveal submenus
            expanders = await sidebar_container.query_selector_all('li.nav-item.has-sub > a')
            for idx, expander in enumerate(expanders):
                try:
                    exp_text = await expander.inner_text() if hasattr(expander, 'inner_text') else ''
                    print(f"[DEBUG] Expanding sidebar expander {idx}: text='{exp_text}'")
                    logger.info(f"Expanding sidebar expander {idx}: text='{exp_text}'")
                    await expander.click()
                    await self.page.wait_for_timeout(1200)  # Wait for submenu to appear
                except Exception as e:
                    logger.warning(f"Sidebar expander click error: {str(e)}")
            # 2. Collect all submenu links
            submenu_links = await sidebar_container.query_selector_all('ul.menu-content li > a')
            for idx, subel in enumerate(submenu_links):
                try:
                    sub_text = await subel.inner_text() if hasattr(subel, 'inner_text') else ''
                    sub_href = await subel.get_attribute('href') or await subel.get_attribute('data-href') or ''
                    print(f"[DEBUG] Submenu element {idx}: text='{sub_text}', href='{sub_href}'")
                    logger.info(f"Submenu element {idx}: text='{sub_href}'")
                    if sub_href and sub_href not in links and (sub_href.startswith(self.base_url) or sub_href.startswith('/')):
                        # Convert relative to absolute if needed
                        if sub_href.startswith('/'):
                            sub_href = self.base_url.rstrip('/') + sub_href
                        links.append(sub_href)
                except Exception as e:
                    logger.warning(f"Sidebar submenu link error: {str(e)}")
            # 3. Collect all direct sidebar links (not expanders)
            direct_links = await sidebar_container.query_selector_all('li.nav-item:not(.has-sub) > a')
            for idx, el in enumerate(direct_links):
                try:
                    el_text = await el.inner_text() if hasattr(el, 'inner_text') else ''
                    el_href = await el.get_attribute('href') or await el.get_attribute('data-href') or ''
                    print(f"[DEBUG] Sidebar direct link {idx}: text='{el_text}', href='{el_href}'")
                    logger.info(f"Sidebar direct link {idx}: text='{el_href}'")
                    if el_href and el_href not in links and (el_href.startswith(self.base_url) or el_href.startswith('/')):
                        if el_href.startswith('/'):
                            el_href = self.base_url.rstrip('/') + el_href
                        links.append(el_href)
                except Exception as e:
                    logger.warning(f"Sidebar direct link error: {str(e)}")
            if not links:
                console.print("[yellow]No visible sidebar or submenu links found inside #main-menu-navigation. Printing sidebar HTML for debugging:[/yellow]")
                sidebar_html = await sidebar_container.inner_html()
                logger.warning(f"Sidebar discover DOM snapshot (truncated): {sidebar_html[:1000]}")
            else:
                console.print(f"[blue]Sidebar/submenu crawl list ({len(links)}):[blue]")
                for l in links:
                    console.print(f"  - {l}")
            return links
        except Exception as e:
            logger.error(f"Error discovering links: {str(e)}")
            dom = await self.page.content()
            logger.warning(f"Sidebar discover error DOM snapshot (truncated): {dom[:1000]}")
            return []

    async def check_for_broken_links(self):
        """Check all links on the current page for broken links, including anchor tag status"""
        console.print("[blue]Checking for broken links...[blue]")
        try:
            links = await self.page.evaluate('''
                () => {
                    const anchors = Array.from(document.querySelectorAll('a[href]'));
                    return anchors.map(a => a.getAttribute('href'));
                }
            ''')
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
            ) as progress:
                task = progress.add_task("Checking links...", total=len(links))
                for link in links:
                    if not link or link.startswith('javascript:'):
                        progress.update(task, advance=1)
                        continue
                    if link.startswith('#'):
                        # Anchor link: check if element with that id exists
                        anchor_id = link[1:]
                        if not anchor_id:
                            self.results.broken_links.append(f"Empty anchor link: {link}")
                        else:
                            exists = await self.page.evaluate(f"document.getElementById('{anchor_id}') !== null")
                            if not exists:
                                self.results.broken_links.append(f"Anchor link #{anchor_id} missing target element")
                        progress.update(task, advance=1)
                        continue
                    if not link.startswith('http'):
                        progress.update(task, advance=1)
                        continue
                    try:
                        response = await self.context.request.get(link, timeout=5000)
                        status = response.status
                        if status >= 400:
                            self.results.broken_links.append(f"{link} (Status: {status})")
                    except Exception:
                        self.results.broken_links.append(f"{link} (Failed to connect)")
                    progress.update(task, advance=1)
        except Exception as e:
            logger.error(f"Error checking broken links: {str(e)}")

    async def check_ui_elements(self, flow_yaml_path: str = None, config: dict = None):
        """Check UI elements on the current page, including interactive elements (tabs, dropdowns, radios, navs) with detailed logging and error highlighting. (DISABLED)"""
        console.print('[yellow]check_ui_elements is currently DISABLED.[/yellow]')
        return
    

    async def login(self, url: str, credentials: LoginCredentials) -> bool:
        """Login to a website using the provided credentials"""
        self.credentials = credentials  # Store credentials for later use
        logger.info(f"Attempting to login to {url}")
        
        try:
            if url.endswith('/login'):
                # If the URL already has /login, navigate directly
                await self.navigate_to(url)
            else:
                # Try a few common login paths
                login_found = False
                for login_path in ['/login', '/signin', '/account/login', '/auth/login', '/user/login']:
                    try:
                        login_url = f"{url.rstrip('/')}{login_path}"
                        await self.navigate_to(login_url)
                        login_found = True
                        break
                    except Exception:
                        continue
                
                if not login_found:
                    # If no login page found through direct paths, try the homepage
                    await self.navigate_to(url)
            
            # Attempt to find and login using the homepage form detection
            login_result = await self.find_and_login_homepage(url, credentials)
            if login_result:
                return True
            
            # If that fails, try a more general approach
            return await self.try_login(url, credentials)
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False

    async def test_form_submission(self, form_selector: str, fields: Dict[str, str]):
        """Test form submission by filling out form fields and submitting the form.
        
        Args:
            form_selector: CSS selector for the form
            fields: Dictionary mapping field selectors to values
        """
        console.print(f"[blue]Testing form submission for {form_selector}...[/blue]")
        
        try:
            # Fill in the form
            for selector, value in fields.items():
                # Replace template variables like {{username}} with actual values
                if isinstance(value, str) and "{{" in value and "}}" in value:
                    # Extract variable name
                    var_name = value.strip("{{").strip("}}")
                    # Check if it's a credential
                    if self.credentials and hasattr(self.credentials, var_name):
                        value = getattr(self.credentials, var_name)
                
                await self.page.fill(selector, value)
                
            # Submit the form and wait for navigation or network idle
            try:
                # First try to find a submit button within the form
                submit_selectors = [
                    "button[type='submit']", "input[type='submit']", 
                    "button.btn-outline-primary", "button.login-button", 
                    ".login-form button", "form button"
                ]
                
                submit_clicked = False
                
                for sel in submit_selectors:
                    try:
                        submit_el = await self.page.query_selector(f"{form_selector} {sel}")
                        if submit_el and await submit_el.is_visible():
                            console.print(f"[blue]Clicking submit button with selector: {sel}[/blue]")
                            async with self.page.expect_navigation(wait_until="networkidle", timeout=30000):
                                await submit_el.click()
                            submit_clicked = True
                            break
                    except Exception as submit_error:
                        logger.debug(f"Could not click {sel}: {str(submit_error)}")
                
                # If no submit button was found/clicked, try pressing Enter in the last field
                if not submit_clicked:
                    console.print("[blue]No submit button found, pressing Enter in the last field[/blue]")
                    last_selector = list(fields.keys())[-1]
                    async with self.page.expect_navigation(wait_until="networkidle", timeout=30000):
                        await self.page.press(last_selector, "Enter")
            
            except Exception as nav_error:
                logger.warning(f"Navigation after form submit didn't complete: {str(nav_error)}")
                console.print(f"[yellow]Navigation after form submit didn't complete: {str(nav_error)}[/yellow]")
            
            # Check for success indicators
            await self.page.wait_for_load_state("networkidle", timeout=5000)
            
            # If we have a results object, store the outcome
            if hasattr(self, "results"):
                if not hasattr(self.results, "passed"):
                    self.results.passed = []
                
                if isinstance(self.results.passed, list):
                    self.results.passed.append({
                        "url": self.page.url,
                        "action": f"Form submission {form_selector}",
                        "result": "Success"
                    })
                else:
                    print("DEBUG: self.results.passed is not a list!")
            
        except Exception as e:
            logger.error(f"Form submission error: {str(e)}")
            if hasattr(self, "results"):
                if not hasattr(self.results, "failed"):
                    self.results.failed = []
                    
                if isinstance(self.results.failed, list):
                    self.results.failed.append({
                        "url": self.page.url,
                        "action": f"Form submission {form_selector}",
                        "result": f"Exception: {str(e)}"
                    })
                else:
                    print("DEBUG: self.results.failed is not a list!")
            raise e

    async def test_responsive_design(self, url: str = None, config: dict = None):
        """Test responsive design: checks for viewport meta, horizontal scroll, images, fixed elements."""
        page_key = (url or self.page.url).split('#')[0]
        if page_key in self.responsive_checked_pages:
            console.print(f"[yellow]Responsive check already performed for {page_key}, skipping duplicate.[/yellow]")
            return []
        self.responsive_checked_pages.add(page_key)
        page_name = (url or self.page.url).split('/')[-1]
        if not page_name:
            page_name = "Home"
        else:
            page_name = page_name.capitalize()
        test_name = f"Responsive Design: {page_name}"
        console.print(f"[blue]RUNNING TEST: {test_name}[blue]")

        # Devices to test
        devices = [
            {"name": "Mobile", "width": 375, "height": 667},
            {"name": "Tablet", "width": 768, "height": 1024},
            {"name": "Desktop", "width": 1920, "height": 1080}
        ]
        original_viewport = self.page.viewport_size
        if not hasattr(self, 'results') or not hasattr(self.results, 'responsive_issue_summary') or self.results.responsive_issue_summary is None:
            self.results.responsive_issue_summary = []
        for device in devices:
            await self.page.set_viewport_size({"width": device["width"], "height": device["height"]})
            await self.page.wait_for_timeout(500)
            has_viewport = await self.page.evaluate("""
                () => !!document.querySelector('meta[name=viewport]')
            """)
            has_horizontal_scroll = await self.page.evaluate("""
                () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2
            """)
            images_without_maxwidth = await self.page.evaluate("""
                () => Array.from(document.querySelectorAll('img')).filter(img => {
                    const style = getComputedStyle(img);
                    return !(style.maxWidth === '100%' || style.width === '100%');
                }).map(img => img.src)
            """)
            fixed_elements = await self.page.evaluate("""
                () => Array.from(document.querySelectorAll('*')).filter(el => {
                    const style = getComputedStyle(el);
                    return style.position === 'fixed' && parseFloat(style.width) > 100 && parseFloat(style.height) > 40;
                }).map(el => el.tagName + (el.id ? '#' + el.id : ''))
            """)
            if not has_viewport:
                self.results.responsive_issue_summary.append({
                    "device": device["name"],
                    "issue_type": "Missing Viewport Meta Tag",
                    "count": 1,
                    "fix": "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> to <head>",
                    "example_selector": "meta[name=viewport]",
                    "severity": "Critical"
                })
            if has_horizontal_scroll:
                self.results.responsive_issue_summary.append({
                    "device": device["name"],
                    "issue_type": "Horizontal Scroll Present",
                    "count": 1,
                    "fix": "Fix layout to prevent horizontal scrolling on small screens.",
                    "example_selector": "html/body",
                    "severity": "Critical"
                })
            if images_without_maxwidth:
                self.results.responsive_issue_summary.append({
                    "device": device["name"],
                    "issue_type": "Images Without max-width:100%",
                    "count": len(images_without_maxwidth),
                    "fix": "Add CSS: img { max-width: 100%; height: auto; }",
                    "example_selector": images_without_maxwidth[0] if images_without_maxwidth else None,
                    "severity": "Moderate"
                })
            if fixed_elements:
                self.results.responsive_issue_summary.append({
                    "device": device["name"],
                    "issue_type": "Large Fixed Elements",
                    "count": len(fixed_elements),
                    "fix": "Avoid large fixed-position elements that block content on mobile.",
                    "example_selector": fixed_elements[0] if fixed_elements else None,
                    "severity": "Moderate"
                })
        await self.page.set_viewport_size(original_viewport)
        return {}

    # After navigation or major interaction, collect detailed performance metrics
    async def collect_performance_metrics(self):
        try:
            perf_metrics = await self.page.evaluate("""
                () => {
                    const nav = performance.getEntriesByType('navigation')[0] || {};
                    const paints = performance.getEntriesByType('paint');
                    const fcp = paints.find(e => e.name === 'first-contentful-paint');
                    const lcpEntry = (window.__lcp || null);
                    let lcp = null;
                    if (lcpEntry && lcpEntry.startTime) lcp = lcpEntry.startTime;
                    // Listen for LCP if not already captured
                    if (!window.__lcpListenerAdded) {
                        window.__lcpListenerAdded = true;
                        new PerformanceObserver((entryList) => {
                            const entries = entryList.getEntries();
                            window.__lcp = entries[entries.length - 1];
                        }).observe({type: 'largest-contentful-paint', buffered: true});
                    }
                    return {
                        navigationStart: nav.startTime || performance.timing.navigationStart,
                        domContentLoaded: nav.domContentLoadedEventEnd || performance.timing.domContentLoadedEventEnd,
                        loadEvent: nav.loadEventEnd || performance.timing.loadEventEnd,
                        responseStart: nav.responseStart || performance.timing.responseStart,
                        responseEnd: nav.responseEnd || performance.timing.responseEnd,
                        firstContentfulPaint: fcp ? fcp.startTime : null,
                        largestContentfulPaint: lcp,
                        now: performance.now()
                    };
                }
            """)
            if not hasattr(self.results, 'performance_details'):
                self.results.performance_details = []
            self.results.performance_details.append({
                'url': self.page.url,
                'metrics': perf_metrics
            })
        except Exception as e:
            logger.warning(f"Could not collect performance metrics: {str(e)}")

    def update_responsiveness_scores(self):
        """Update responsiveness scores based on unique responsive issue types (per device)."""
        if not hasattr(self.results, 'responsiveness_scores') or self.results.responsiveness_scores is None:
            self.results.responsiveness_scores = {}
        devices = ["Mobile", "Tablet", "Desktop"]
        device_unique_issues = {d: set() for d in devices}
        if hasattr(self.results, 'responsive_issue_summary') and self.results.responsive_issue_summary:
            for issue in self.results.responsive_issue_summary:
                device = issue.get("device", None)
                if device in device_unique_issues:
                    key = (issue.get("issue_type", None), issue.get("fix", None))
                    device_unique_issues[device].add(key)
        for device in devices:
            unique_issues = len(device_unique_issues[device])
            score = 100 - (unique_issues * 5)
            if score < 0:
                score = 0
            self.results.responsiveness_scores[device] = {
                'score': score,
                'issues': unique_issues
            }

    async def generate_report(self):
        # Always update responsiveness scores right before generating the report
        self.update_responsiveness_scores()
        from report_generator import MarkdownReportGenerator, HTMLReportGenerator
        md_generator = MarkdownReportGenerator(self.results)
        html_generator = HTMLReportGenerator(self.results)
        md_report = md_generator.generate()
        html_report = html_generator.generate()
        print(f"[green]Reports generated successfully![/green]")
        print(f"[green]- Markdown report: {md_report}[/green]")
        print(f"[green]- HTML report: {html_report}[/green]")
        print(f"[bold blue]To view the report, open the HTML file above in your browser.[/bold blue]")
        return {
            "markdown": md_report,
            "html": html_report
        }


@app.command()
def test(
    url: str = typer.Argument(..., help="Website URL to test"),
    username: str = typer.Option(..., help="Login username (required)"),
    password: str = typer.Option(..., help="Login password (required)", hide_input=True),
    urls_file: Optional[str] = typer.Option(None, help="File containing URLs to test (one per line)"),
    headless: bool = typer.Option(None, help="Run in headless mode (--no-headless for visible browser)"),
    report: bool = typer.Option(True, help="Generate detailed HTML/Markdown report")
):
    """Run a full, professional QA test on a website (curated generic tests, multi-page crawl)"""
    async def run_test():
        start_time = time.time()
        try:
            # Ask for headless mode if not specified
            use_headless = headless
            if use_headless is None:
                choice = input("Run in headless mode? [Y/n]: ").strip().lower()
                use_headless = choice != 'n'
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("[green]Setting up browser...", total=None)
                qa_bot = QABot(headless=use_headless)
                await qa_bot.setup()
                progress.update(task, description="[green]Preparing test environment...")
                credentials = LoginCredentials(
                    username=username,
                    password=password
                )
                # Load optional URLs list
                urls_to_test = None
                if urls_file:
                    with open(urls_file, 'r') as f:
                        urls_to_test = [line.strip() for line in f if line.strip()]
                # --- Curated generic QA tests with smart crawl ---
                # 1. Login
                login_success = await qa_bot.login(url, credentials)
                qa_bot.results = TestResults(website=url)
                if not login_success:
                    qa_bot.results.failed.append({
                        "step": "Login",
                        "url": url,
                        "reason": "Login failed. Check your credentials and try again."
                    })
                    console.print("[bold red]Login failed. Stopping tests.[/bold red]")
                    if report:
                        await qa_bot.generate_report()
                    return
                else:
                    qa_bot.results.passed.append({
                        "step": "Login",
                        "url": qa_bot.page.url,
                        "status": "Success",
                        "load_time": round(time.time() - start_time, 2)
                    })
                # 2. SSL Certificate
                qa_bot.results.ssl_status = await qa_bot.check_ssl(url)
                # 3. Discover links (always try to crawl public pages)
                discovered_urls = [url]
                links = await qa_bot.discover_links(max_links=20)
                for link in links:
                    if link not in discovered_urls:
                        discovered_urls.append(link)
                # 4. For each discovered page, run navigation, broken links, UI, and responsive checks
                ui_checks_run = 0
                responsive_checks_run = 0
                for page_url in discovered_urls:
                    nav_success = await qa_bot.navigate_to(page_url)
                    await qa_bot.check_for_broken_links()
                    result1 = await qa_bot.check_ui_elements()
                    ui_checks_run += 1
                    result2 = await qa_bot.test_responsive_design(url=None)
                    responsive_checks_run += 1
                # 5. Only report 'No UI/responsive issues' if checks were actually run
                if ui_checks_run == 0:
                    qa_bot.results.ui_issue_summary = None
                if responsive_checks_run == 0:
                    qa_bot.results.responsive_issue_summary = None
                # --- Ensure responsiveness scores are updated before report generation ---
                qa_bot.update_responsiveness_scores()
                # 6. Generate report if requested
                if report:
                    console.print("\n[bold blue]Step 4: Generating test report[/bold blue]")
                    reports = await qa_bot.generate_report()
                    if reports:
                        # Executive summary
                        total = len(discovered_urls)
                        passed = len([r for r in qa_bot.results.passed if r.get('step', '').startswith('Page Navigation')])
                        failed = len([r for r in qa_bot.results.failed if r.get('step', '').startswith('Page Navigation')])
                        console.print(f"\n[bold green]Executive Summary:[/bold green]")
                        console.print(f"[green]Total pages tested: {total}[/green]")
                        console.print(f"[green]Passed: {passed}[/green]")
                        console.print(f"[red]Failed: {failed}[/red]")
                        if failed > 0:
                            console.print(f"[red]See detailed report for failed pages and reasons.[/red]")
                        console.print(f"[green]Test complete! Reports saved:[/green]")
                        console.print(f"[green]- Markdown report: {reports['markdown']}[/green]")
                        console.print(f"[green]- HTML report: {reports['html']}[/green]")
                    else:
                        console.print("[yellow]Report generation failed.[/yellow]")
            console.print(f"\n[green]Test report saved in the 'reports' directory.[/green]")
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/bold red]")
            import traceback
            console.print(traceback.format_exc())
        finally:
            if 'qa_bot' in locals() and qa_bot.browser:
                await qa_bot.browser.close()
    asyncio.run(run_test())


@app.command()
def run_flow(
    url: str = typer.Argument(..., help="Website URL to test"),
    flow_name: str = typer.Argument(..., help="Name of the flow to run"),
    environment: str = typer.Option("prod", help="Environment to run the flow in (prod, uat)"),
    username: str = typer.Option(..., help="Login username (required)"),
    password: str = typer.Option(..., help="Login password (required)"),
    headless: bool = typer.Option(None, help="Run in headless mode (--no-headless for visible browser)"),
    skip_login: bool = typer.Option(False, help="Skip login step even if credentials are provided"),
    report: bool = typer.Option(True, help="Generate detailed HTML/Markdown report")
):
    """Run a test flow on a website"""
    # Remove any extra quotes that might have been added when calling from the interactive menu
    flow_name = flow_name.strip('"\'')
    if environment not in ["prod", "uat"]:
        console.print(f"[red]Invalid environment: {environment}. Only 'prod' and 'uat' are supported.[/red]")
        raise typer.Exit(code=1)
    
    async def run_flow_test():
        try:
            # Ask for headless mode if not specified
            use_headless = headless
            if use_headless is None:
                choice = input("Run in headless mode? [Y/n]: ").strip().lower()
                use_headless = choice != 'n'
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("[green]Setting up browser...", total=None)
                
                qa_bot = QABot(headless=use_headless)
                await qa_bot.setup()
                
                progress.update(task, description="[green]Preparing test environment...")
                
                # Initialize flow manager and executor
                flow_manager = FlowManager()
                flow_executor = FlowExecutor(qa_bot, flow_manager)
                
                # Create login credentials if not skipping login
                credentials = None
                if not skip_login:
                    credentials = LoginCredentials(
                        username=username,
                        password=password
                    )
                
                progress.update(task, description=f"[green]Running flow '{flow_name}' for {url}...")
                
                # Set base URL directly on the QA bot
                qa_bot.base_url = url
                
                # Initialize results object with the website URL
                qa_bot.results = TestResults(website=url)
                
                # Execute the flow
                flow_results = await flow_executor.execute_flow(
                    flow_name=flow_name,
                    environment=environment,
                    credentials=credentials
                )
                
                # Make sure passed/failed steps from flow execution are added to qa_bot.results
                for step in flow_results.get("passed", []):
                    if hasattr(qa_bot.results, 'passed') and isinstance(qa_bot.results.passed, list):
                        qa_bot.results.passed.append(step)
                
                for step in flow_results.get("failed", []):
                    if hasattr(qa_bot.results, 'failed') and isinstance(qa_bot.results.failed, list):
                        qa_bot.results.failed.append(step)
                
                # Generate reports
                if report and qa_bot.results:
                    from report_generator import MarkdownReportGenerator, HTMLReportGenerator
                    console.print("[blue]Generating test reports...[/blue]")
                    md_generator = MarkdownReportGenerator(qa_bot.results)
                    html_generator = HTMLReportGenerator(qa_bot.results)
                    md_report = md_generator.generate()
                    html_report = html_generator.generate()
                    
                    console.print(f"[green]Reports generated successfully![/green]")
                    console.print(f"[green]- Markdown report: {md_report}[/green]")
                    console.print(f"[green]- HTML report: {html_report}[/green]")
                    console.print(f"[bold blue]To view the report, open the HTML file above in your browser.[/bold blue]")
                    
                    # Automatically open the HTML report
                    import sys, os
                    if sys.platform.startswith('win'):
                        os.startfile(html_report)
                    elif sys.platform.startswith('darwin'):
                        os.system(f'open "{html_report}"')
                    elif sys.platform.startswith('linux'):
                        os.system(f'xdg-open "{html_report}"')
                
                # Print flow execution summary
                console.print("\n[bold green]Flow Execution Summary:[/bold green]")
                
                table = Table(title=f"Flow: {flow_name} ({environment})")
                table.add_column("Status", style="bold")
                table.add_column("Step", style="cyan")
                table.add_column("Details", style="yellow")
                
                for step in flow_results.get("passed", []):
                    table.add_row("✅ PASS", step.get("step", "Unknown"), "")
                
                for step in flow_results.get("failed", []):
                    table.add_row("❌ FAIL", step.get("step", "Unknown"), step.get("error", "Unknown error"))
                
                for step in flow_results.get("skipped", []):
                    table.add_row("⏭️ SKIP", step.get("step", "Unknown"), step.get("reason", ""))
                
                console.print(table)
                
                progress.update(task, description="[green]Flow execution completed!")
        
        except FileNotFoundError:
            console.print(f"[bold red]Error: Flow '{flow_name}' not found in environment '{environment}'.[/bold red]")
            flows = FlowManager().list_flows(environment)
            if flows.get(environment):
                console.print(f"\n[yellow]Available flows in '{environment}':[/yellow]")
                for flow in flows.get(environment, []):
                    console.print(f"- {flow}")
            else:
                console.print(f"[yellow]No flows found in environment '{environment}'.[/yellow]")
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/bold red]")
            import traceback
            console.print(traceback.format_exc())
        finally:
            if 'qa_bot' in locals() and qa_bot.browser:
                await qa_bot.browser.close()

    asyncio.run(run_flow_test())


@app.command()
def create_flow(
    flow_name: str = typer.Argument(..., help="Name of the flow to create"),
    environment: str = typer.Option("prod", help="Environment to create the flow in (prod, uat)")
):
    """Create a new flow template that can be customized"""
    if environment not in ["prod", "uat"]:
        console.print(f"[red]Invalid environment: {environment}. Only 'prod' and 'uat' are supported.[/red]")
        raise typer.Exit(code=1)
    flow_manager = FlowManager()
    try:
        flow_path = flow_manager.create_template_flow(flow_name, environment)
        console.print(f"[bold green]Created flow template:[/bold green] {flow_path}")
        console.print("[blue]Edit this file to customize your test flow.[/blue]")
    except Exception as e:
        console.print(f"[bold red]Error creating flow: {str(e)}[/bold red]")


@app.command()
def list_flows(
    environment: Optional[str] = typer.Option(None, help="Environment to list flows for (prod, uat)"),
    plain: bool = typer.Option(False, help="Print plain output for scripts")
):
    """List all available flows"""
    flow_manager = FlowManager()
    try:
        flows = flow_manager.list_flows(environment)
        if not flows:
            if plain:
                return
            console.print("[yellow]No flows found.[/yellow]")
            return
        if plain:
            for env, flow_list in flows.items():
                for flow in flow_list:
                    print(f"{env},{flow}")
            return
        table = Table(title="Available Test Flows")
        table.add_column("Environment", style="cyan")
        table.add_column("Flow Name", style="green")
        for env, flow_list in flows.items():
            for flow in flow_list:
                table.add_row(env, flow)
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error listing flows: {str(e)}[bold red]")


@app.command()
def copy_flow(
    flow_name: str = typer.Argument(..., help="Name of the flow to copy"),
    source_env: str = typer.Option("prod", help="Source environment (prod, uat)"),
    target_env: str = typer.Option("uat", help="Target environment (prod, uat)")
):
    """Copy a flow from one environment to another"""
    flow_name = flow_name.strip('"\'')
    if source_env not in ["prod", "uat"] or target_env not in ["prod", "uat"]:
        console.print(f"[red]Invalid environment(s). Only 'prod' and 'uat' are supported.[/red]")
        raise typer.Exit(code=1)
    
    flow_manager = FlowManager()
    try:
        new_path = flow_manager.copy_flow(flow_name, source_env, target_env)
        console.print(f"[bold green]Copied flow:[/bold green] {new_path}")
    except Exception as e:
        console.print(f"[bold red]Error copying flow: {str(e)}[/bold red]")


@app.command()
def generate_flow(
    flow_name: str = typer.Argument(..., help="Name of the flow to generate"),
    environment: str = typer.Option("prod", help="Environment for the flow (prod, uat)"),
    description: str = typer.Option(..., help="Plain English description of the flow")
):
    """Generate a new flow YAML from a plain English description."""
    flow_name = flow_name.strip('"\'')
    description = description.strip('"\'')
    if environment not in ["prod", "uat"]:
        console.print(f"[red]Invalid environment: {environment}. Only 'prod' and 'uat' are supported.[/red]")
        raise typer.Exit(code=1)
    
    # Simple template system: parse description into steps (for demo, just one step)
    # In production, you could use an LLM or more advanced parser
    steps = []
    for line in description.split(". "):
        line = line.strip()
        if not line:
            continue
        # Very basic mapping for demo
        if "login" in line.lower():
            steps.append({
                "name": "Login",
                "action": "fill_form",
                "form_selector": "form",
                "fields": {
                    "input[name='username']": "{{username}}",
                    "input[name='password']": "{{password}}"
                }
            })
        elif "navigate" in line.lower():
            steps.append({
                "name": "Navigate",
                "action": "navigate",
                "url": "/"
            })
        elif "check ui" in line.lower():
            steps.append({
                "name": "Check UI",
                "action": "check_ui"
            })
        elif "responsive" in line.lower():
            steps.append({
                "name": "Test Responsive Design",
                "action": "test_responsive"
            })
        # Add more mappings as needed
        else:
            steps.append({
                "name": line,
                "action": "custom",
                "description": line
            })
    flow_yaml = {
        "name": flow_name,
        "description": description,
        "base_url": "https://example.com",
        "steps": steps
    }
    flow_dir = Path(f"flows/{environment}")
    flow_dir.mkdir(parents=True, exist_ok=True)
    flow_path = flow_dir / f"{flow_name}.yaml"
    with open(flow_path, "w", encoding="utf-8") as f:
        yaml.dump(flow_yaml, f, sort_keys=False, allow_unicode=True)
    console.print(f"[green]Generated flow YAML:[/green] {flow_path}")


if __name__ == "__main__":
    app() 