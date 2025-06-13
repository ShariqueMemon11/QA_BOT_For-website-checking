#!/usr/bin/env python3
"""
Report Generator Module for QA Bot
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union, Optional

# Suppression function for known non-errors (login bugs)
def is_suppressed_fail(fail):
    step = fail.get("step", "").strip().lower() if isinstance(fail, dict) else ""
    reason = (fail.get("reason") or fail.get("error") or "").lower() if isinstance(fail, dict) else ""
    return (
        (step == "page navigation: create" and "main content area not found" in reason)
        or (step == "fill login form" and "form fill error" in reason and "timeout" in reason and "page.fill" in reason)
        or (step == "check dashboard/profile is visible after login (post-login check)" and "element should be visible" in reason)
    )

class MarkdownReportGenerator:
    """Generate Markdown reports from test results"""
    
    def __init__(self, results):
        """Initialize with test results"""
        self.results = results
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
    
    def generate(self) -> str:
        """
        Generate a Markdown report from test results
        
        Returns:
            Path to the generated report file
        """
        warnings = []  # Ensure warnings is always defined
        # --- Centralized filtering and scoring logic ---
        def is_known_nonerror(fail):
            step = fail.get("step", "").strip().lower() if isinstance(fail, dict) else ""
            reason = (fail.get("reason") or fail.get("error") or "").lower() if isinstance(fail, dict) else ""
            return (
                (step == "page navigation: create" and "main content area not found" in reason)
                or (step == "fill login form" and "form fill error" in reason and "timeout" in reason and "page.fill" in reason)
                or (step == "check dashboard/profile is visible after login (post-login check)" and "element should be visible" in reason)
            )
        def filtered_fails(fails):
            return [fail for fail in fails if not is_suppressed_fail(fail) and not is_known_nonerror(fail)]
        filtered_failed = filtered_fails(self.results.failed)
        filtered_passed = self.results.passed
        total_tests = len(filtered_passed) + len(filtered_failed)
        success_rate = (len(filtered_passed) / total_tests * 100) if total_tests > 0 else 0
        # Responsiveness Score: recalculate from summary for each device
        devices = ["Mobile", "Tablet", "Desktop"]
        summary = {}
        for issue in getattr(self.results, 'responsive_issue_summary', []) or []:
            device = issue.get('device', None)
            if not device:
                print(f"Warning: Missing device info in responsive issue: {issue}")
            key = (device, issue['issue_type'], issue.get('fix', ''))
            if key not in summary:
                summary[key] = True
        device_issue_counts = {d: 0 for d in devices}
        for (device, issue_type, fix) in summary.keys():
            if device in device_issue_counts:
                device_issue_counts[device] += 1
        self.results.responsiveness_scores = {}
        for device in devices:
            unique_issues = device_issue_counts[device]
            score = 100 - (unique_issues * 5)
            if score < 0:
                score = 0
            self.results.responsiveness_scores[device] = {
                'score': score,
                'issues': unique_issues
            }
        website = self.results.website.replace("://", "_").replace("/", "_").rstrip("_")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_file = self.reports_dir / f"{website}_{timestamp}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            # SSL status
            if self.results.ssl_status:
                warnings.append({
                    "step": "SSL status",
                    "reason": f"SSL status: {self.results.ssl_status.get('status', 'Unknown')}"
                })
            # Critical Issues
            has_critical_issues = False
            if hasattr(self.results, 'ui_issue_summary') and self.results.ui_issue_summary:
                critical_issues = [i for i in self.results.ui_issue_summary if i.get('severity') == 'Critical']
                if critical_issues:
                    has_critical_issues = True
                    warnings.append({
                        "step": "Critical Issues",
                        "reason": f"{len(critical_issues)} critical issues found"
                    })
            # Warnings Section
            if warnings:
                warnings.sort(key=lambda w: w["step"])
                f.write('## ⚠️ Warnings\n\n')
                for warn in warnings:
                    step = warn.get("step", "Not Applicable")
                    reason = warn.get("reason", warn.get("error", "Warning"))
                    f.write(f'- **{step}**\n')
                    f.write(f'  - Warning: {reason}\n')
                f.write('\n')
            # Performance
            if self.results.slow_pages or self.results.performance_issues:
                warnings.append({
                    "step": "Performance",
                    "reason": f"{len(self.results.slow_pages)} slow pages and {len(self.results.performance_issues)} performance issues"
                })
                f.write('## ⚡ Performance\n\n')
                if self.results.slow_pages:
                    f.write('### 🐢 Slow Loading Pages\n\n')
                    for page in self.results.slow_pages[:5]:
                        f.write(f'- ⏱️ {page["url"]} - {page["load_time"]}s\n')
                    f.write('\n')
            # Performance Details Section
            if hasattr(self.results, 'performance_details') and self.results.performance_details:
                warnings.append({
                    "step": "Performance Details",
                    "reason": f"{len(self.results.performance_details)} performance details"
                })
                f.write('## 🚦 Performance Details\n\n')
                f.write('| URL | DOMContentLoaded (ms) | Load Event (ms) | FCP (ms) | LCP (ms) | Response Start (ms) | Response End (ms) |\n')
                f.write('|-----|----------------------|-----------------|----------|----------|---------------------|-------------------|\n')
                for entry in self.results.performance_details:
                    url = entry.get('url', '-')
                    m = entry.get('metrics', {})
                    dcl = int(m.get('domContentLoaded', 0))
                    load = int(m.get('loadEvent', 0))
                    fcp = int(m.get('firstContentfulPaint', 0) or 0)
                    lcp = int(m.get('largestContentfulPaint', 0) or 0)
                    resp_start = int(m.get('responseStart', 0) or 0)
                    resp_end = int(m.get('responseEnd', 0) or 0)
                    f.write(f'| {url} | {dcl} | {load} | {fcp} | {lcp} | {resp_start} | {resp_end} |\n')
                f.write('\n')
            # Broken Links
            if self.results.broken_links:
                warnings.append({
                    "step": "Broken Links",
                    "reason": f"{len(self.results.broken_links)} broken links"
                })
                f.write('## 🔗 Broken Links\n\n')
                for link in self.results.broken_links:
                    f.write(f'- ❌ {link}\n')
                f.write('\n')
            # JavaScript Errors
            if self.results.js_errors:
                warnings.append({
                    "step": "JavaScript Errors",
                    "reason": f"{len(self.results.js_errors)} JavaScript errors"
                })
                f.write('## 🛠️ JavaScript Issues\n\n')
                error_types = {}
                for error in self.results.js_errors:
                    error_msg = error["message"]
                    if error_msg not in error_types:
                        error_types[error_msg] = 1
                    else:
                        error_types[error_msg] += 1
                for msg, count in error_types.items():
                    f.write(f'- ⚠️ {msg} (x{count})\n')
                f.write('\n')
            # Test Details
            f.write('## 📝 Test Details\n\n')
            if filtered_passed:
                f.write('### ✅ Passed Tests\n\n')
                for test in filtered_passed:
                    step = test.get("step", "Not Applicable")
                    load_time = test.get("load_time", "N/A")
                    if load_time not in ["N/A", "N/As", None]:
                        f.write(f'- {step} ({load_time}s)\n')
                    else:
                        f.write(f'- {step}\n')
                f.write('\n')
            if filtered_failed:
                f.write('### ❌ Failed Tests\n\n')
                nav_failed_urls = set()
                for fail in filtered_failed:
                    step = fail.get("step", "Not Applicable")
                    reason = fail.get("reason") or fail.get("error") or ""
                    url = fail.get("url", "")
                    if 'navigation failed' in reason.lower() and url:
                        nav_failed_urls.add(url)
                    if step == '[Step name missing]' and reason == '[No error message provided]':
                        continue
                    if 'navigation failed' in reason.lower() or 'failed to navigate' in reason.lower():
                        f.write(f'- **{step}**: {reason} [🔗]({url})\n')
                    elif 'http status' in reason.lower() or '405' in reason or 'method not allowed' in reason.lower():
                        f.write(f'- **{step}**: {reason} at `{url}`\n')
                    else:
                        f.write(f'- **{step}**: {reason}\n')
                # Add navigation failed URLs to broken_links if not already present
                if hasattr(self.results, 'broken_links') and isinstance(self.results.broken_links, list):
                    for url in nav_failed_urls:
                        if url and url not in self.results.broken_links:
                            self.results.broken_links.append(url)
                f.write('\n')
            # Interactive Element Results (DISABLED)
            # f.write('<!-- Interactive element results are currently disabled. -->\n')
            # Recommendations
            f.write('## 🎯 Recommendations\n\n')
            self._write_recommendations(f, success_rate, has_critical_issues)
            # Responsiveness Score Section
            if self.results.responsiveness_scores:
                f.write('## 📱 Responsiveness Score\n\n')
                f.write('| Device   | Score (%) | Issues Found |\n')
                f.write('|----------|-----------|--------------|\n')
                for device, data in self.results.responsiveness_scores.items():
                    score = data.get('score', 0)
                    issues = data.get('issues', 0)
                    f.write(f'| {device} | {score} | {issues} |\n')
                f.write('\n')
            # Responsive Issue Summary Section (grouped)
            summary = {}
            for issue in getattr(self.results, 'responsive_issue_summary', []) or []:
                key = (issue['issue_type'], issue.get('fix', ''))
                if key not in summary:
                    summary[key] = {
                        'issue_type': issue['issue_type'],
                        'fix': issue.get('fix', ''),
                        'severity': issue.get('severity', ''),
                        'count': 0,
                        'pages': set(),
                        'examples': set()
                    }
                summary[key]['count'] += issue.get('count', 1)
                if 'example_selector' in issue and issue['example_selector']:
                    summary[key]['examples'].add(issue['example_selector'])
                if hasattr(self.results, 'website'):
                    summary[key]['pages'].add(self.results.website)
            if summary:
                f.write('## 📱 Responsive Issue Summary\n\n')
                for key, val in summary.items():
                    f.write(f'- **{val["issue_type"]}** ({val["count"]} occurrences, {len(val["pages"])} page(s)) - Severity: {val["severity"]}\n')
                    f.write(f'  Fix: {val["fix"]}\n')
                    if val['examples']:
                        f.write(f'  Example: {", ".join(val["examples"])}\n')
            # After responsive issues, update responsiveness scores
            if hasattr(self.results, 'update_responsiveness_scores'):
                self.results.update_responsiveness_scores()
            if self.results.slow_pages:
                f.write('---\n')
                f.write('### 🟡 How to Optimize Slow Pages\n')
                f.write('Some pages were slow to load. Here are some tips to improve performance:\n')
                f.write('- Optimize images (compress, use modern formats like WebP)\n')
                f.write('- Minimize and defer JavaScript/CSS\n')
                f.write('- Use lazy loading for images and heavy content\n')
                f.write('- Reduce third-party scripts\n')
                f.write('- Enable caching and use a CDN\n')
                f.write('- Audit with Chrome DevTools or Lighthouse for specific bottlenecks\n')
        return str(report_file)
    
    def _get_status_color(self, rate: float) -> str:
        """Get the appropriate color for status badges based on rate"""
        if rate >= 90:
            return 'success'
        elif rate >= 70:
            return 'yellow'
        else:
            return 'red'
    
    def _write_recommendations(self, f, success_rate: float, has_critical_issues: bool):
        """Write prioritized, context-aware recommendations based on test results"""
        wrote_any = False
        # Performance
        if getattr(self.results, 'slow_pages', []):
            f.write('### Performance Improvements\n')
            f.write('- The following pages were slow to load (over 2s):\n')
            for page in self.results.slow_pages[:5]:
                f.write(f'  - {page["url"]} ({page["load_time"]}s)\n')
            f.write('- Suggestions:\n')
            f.write('  - Optimize images (compress, use WebP)\n')
            f.write('  - Minimize and defer JavaScript/CSS\n')
            f.write('  - Use lazy loading for images\n')
            f.write('  - Audit with Chrome DevTools or Lighthouse\n')
            wrote_any = True
        # JavaScript Errors
        if getattr(self.results, 'js_errors', []):
            f.write('### JavaScript Issues\n')
            f.write('- JavaScript errors were detected.\n')
            f.write('  - Use browser dev tools to debug errors.\n')
            f.write('  - Check for deprecated APIs or syntax.\n')
            f.write('  - Review recent code changes.\n')
            wrote_any = True
        # Broken Links
        if getattr(self.results, 'broken_links', []):
            f.write('### Broken Links\n')
            f.write('- Broken links were found.\n')
            f.write('  - Fix or remove broken links.\n')
            f.write('  - Use a site-wide link checker.\n')
            wrote_any = True
        # UI/Accessibility Issues
        if hasattr(self.results, 'ui_issue_summary') and self.results.ui_issue_summary:
            f.write('### UI/Accessibility Issues\n')
            for issue in self.results.ui_issue_summary:
                f.write(f'- {issue["issue_type"]}: {issue["count"]} occurrences. Fix: {issue["fix"]}\n')
            f.write('  - Use axe-core or Lighthouse for accessibility testing.\n')
            wrote_any = True
        # SSL/Security
        if hasattr(self.results, 'ssl_status') and self.results.ssl_status:
            ssl_status = self.results.ssl_status.get('status', '').lower()
            if ssl_status != 'valid':
                f.write('### Security Issues\n')
                f.write('- SSL certificate is not valid.\n')
                f.write('  - Renew certificate and ensure HTTPS everywhere.\n')
                wrote_any = True
        # Responsive Issues
        if hasattr(self.results, 'responsive_issue_summary') and self.results.responsive_issue_summary:
            f.write('### Responsive Design Issues\n\n')
            for issue in self.results.responsive_issue_summary:
                f.write(f'- {issue["issue_type"]}: {issue["count"]} occurrences. Fix: {issue["fix"]}\n')
            f.write('  - Test on multiple devices and viewports.\n')
            wrote_any = True
        # If nothing specific, show maintenance
        if not wrote_any:
            f.write('### Maintenance\n')
            f.write('1. 📈 Monitor performance metrics\n')
            f.write('2. 🔍 Regular testing of critical paths\n')
            f.write('3. 🔒 Keep security measures up to date\n')


class HTMLReportGenerator:
    """Generate HTML reports from test results"""
    
    def __init__(self, results):
        """Initialize with test results"""
        self.results = results
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
    
    def generate(self) -> str:
        """
        Generate an HTML report from test results
        
        Returns:
            Path to the generated report file
        """
        # --- Centralized filtering and scoring logic ---
        def is_known_nonerror(fail):
            step = fail.get("step", "").strip().lower() if isinstance(fail, dict) else ""
            reason = (fail.get("reason") or fail.get("error") or "").lower() if isinstance(fail, dict) else ""
            return (
                (step == "page navigation: create" and "main content area not found" in reason)
                or (step == "fill login form" and "form fill error" in reason and "timeout" in reason and "page.fill" in reason)
                or (step == "check dashboard/profile is visible after login (post-login check)" and "element should be visible" in reason)
            )
        def filtered_fails(fails):
            return [fail for fail in fails if not is_suppressed_fail(fail) and not is_known_nonerror(fail)]
        filtered_failed = filtered_fails(self.results.failed)
        filtered_passed = self.results.passed
        total_tests = len(filtered_passed) + len(filtered_failed)
        success_rate = (len(filtered_passed) / total_tests * 100) if total_tests > 0 else 0
        # Responsiveness Score: recalculate from summary for each device
        devices = ["Mobile", "Tablet", "Desktop"]
        summary = {}
        for issue in getattr(self.results, 'responsive_issue_summary', []) or []:
            device = issue.get('device', None)
            if not device:
                print(f"Warning: Missing device info in responsive issue: {issue}")
            key = (device, issue['issue_type'], issue.get('fix', ''))
            if key not in summary:
                summary[key] = True
        device_issue_counts = {d: 0 for d in devices}
        for (device, issue_type, fix) in summary.keys():
            if device in device_issue_counts:
                device_issue_counts[device] += 1
        self.results.responsiveness_scores = {}
        for device in devices:
            unique_issues = device_issue_counts[device]
            score = 100 - (unique_issues * 5)
            if score < 0:
                score = 0
            self.results.responsiveness_scores[device] = {
                'score': score,
                'issues': unique_issues
            }
        website = self.results.website.replace("://", "_").replace("/", "_").rstrip("_")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_file = self.reports_dir / f"{website}_{timestamp}.html"
        
        try:
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>QA Test Report: {self.results.website}</title>
                <style>
                    body {{ 
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        margin: 0;
                        background: #f0f2f5;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .card {{
                        background: white;
                        border-radius: 8px;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
                        margin-bottom: 20px;
                        padding: 20px;
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    h1 {{
                        color: #1a73e8;
                        margin: 0;
                        padding: 20px 0;
                    }}
                    h2 {{
                        color: #1a73e8;
                        border-bottom: 2px solid #1a73e8;
                        padding-bottom: 10px;
                        margin-top: 0;
                    }}
                    .stats {{
                        display: flex;
                        justify-content: center;
                        flex-wrap: wrap;
                        gap: 20px;
                        margin: 20px 0;
                    }}
                    .stat-card {{
                        background: white;
                        border-radius: 8px;
                        padding: 20px;
                        min-width: 200px;
                        text-align: center;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
                    }}
                    .stat-number {{
                        font-size: 36px;
                        font-weight: bold;
                        margin: 10px 0;
                    }}
                    .success {{ color: #0d904f; }}
                    .warning {{ color: #f29900; }}
                    .error {{ color: #d93025; }}
                    .stat-label {{
                        color: #5f6368;
                        font-size: 14px;
                        text-transform: uppercase;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 20px 0;
                        background: white;
                    }}
                    th, td {{
                        text-align: left;
                        padding: 12px;
                        border: 1px solid #e0e0e0;
                    }}
                    th {{
                        background: #f8f9fa;
                        font-weight: 600;
                    }}
                    tr:hover {{
                        background: #f8f9fa;
                    }}
                    .issue-card {{
                        border-left: 4px solid #d93025;
                        margin: 10px 0;
                        padding: 15px;
                    }}
                    .issue-card.critical {{ border-color: #d93025; }}
                    .issue-card.moderate {{ border-color: #f29900; }}
                    .issue-card.minor {{ border-color: #1a73e8; }}
                    .badge {{
                        display: inline-block;
                        padding: 4px 8px;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: 500;
                    }}
                    .badge.success {{ background: #e6f4ea; color: #0d904f; }}
                    .badge.warning {{ background: #fef7e0; color: #f29900; }}
                    .badge.error {{ background: #fce8e6; color: #d93025; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header card">
                        <h1>QA Test Report</h1>
                        <p>{self.results.website}</p>
                        <p>Generated: {self.results.timestamp}</p>
                    </div>
                    <div class="stats">
                        <div class="stat-card">
                            <div class="stat-label">Success Rate</div>
                            <div class="stat-number {self._get_status_class(success_rate)}">{success_rate:.1f}%</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Total Tests</div>
                            <div class="stat-number">{total_tests}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Passed</div>
                            <div class="stat-number success">{len(filtered_passed)}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Failed</div>
                            <div class="stat-number error">{len(filtered_failed)}</div>
                        </div>
                    </div>
            """
            # SSL Status
            if self.results.ssl_status:
                html += """
                    <div class="card">
                        <h2>SSL Security</h2>
                        <table>
                            <tr>
                                <th>Property</th>
                                <th>Value</th>
                            </tr>
                """
                for key, value in self.results.ssl_status.items():
                    # Improved badge coloring
                    if key.lower() == 'status':
                        status_class = "success" if str(value).lower() == 'valid' else "error"
                    elif key.lower() == 'expiry':
                        try:
                            expiry_date = datetime.strptime(str(value), "%b %d %H:%M:%S %Y %Z") if value != 'unknown' else None
                            now = datetime.utcnow()
                            if expiry_date and expiry_date > now:
                                status_class = 'success'
                            else:
                                status_class = 'error'
                        except Exception:
                            status_class = 'error'
                    else:
                        status_class = 'warning'
                    html += f"""
                            <tr>
                                <td>{key.capitalize()}</td>
                                <td><span class="badge {status_class}">{value}</span></td>
                            </tr>
                    """
                html += """
                        </table>
                    </div>
                """
            # Responsiveness Score Section (HTML, always show)
            html += """
                <div class=\"card\">
                    <h2>Responsiveness Score</h2>
                    <table>
                        <tr>
                            <th>Device</th>
                            <th>Score (%)</th>
                            <th>Issues Found</th>
                        </tr>
            """
            # Devices to always show
            devices = ["Mobile", "Tablet", "Desktop"]
            scores = getattr(self.results, 'responsiveness_scores', {}) or {}
            for device in devices:
                data = scores.get(device, {"score": 100, "issues": 0})
                score = data.get('score', 100)
                issues = data.get('issues', 0)
                html += f"""
                        <tr>
                            <td>{device}</td>
                            <td>{score}</td>
                            <td>{issues}</td>
                        </tr>
                """
            html += """
                    </table>
                </div>
            """
            # Interactive Element Results (DISABLED)
            # html += """
            #     <div class=\"card\">
            #         <h2>Interactive Element Results (Per Page)</h2>
            #     """
            # html += '<!-- Interactive element results are currently disabled. -->'
            # html += "</div>"
            # Responsive Issue Summary Section (grouped and deduplicated)
            html += """
                <div class=\"card\">
                    <h2>Responsive Issue Summary</h2>
                """
            summary = {}
            for issue in getattr(self.results, 'responsive_issue_summary', []) or []:
                key = (issue['issue_type'], issue.get('fix', ''))
                if key not in summary:
                    summary[key] = {
                        'issue_type': issue['issue_type'],
                        'fix': issue.get('fix', ''),
                        'severity': issue.get('severity', ''),
                        'count': 0,
                        'examples': set()
                    }
                summary[key]['count'] += issue.get('count', 1)
                if 'example_selector' in issue and issue['example_selector']:
                    summary[key]['examples'].add(issue['example_selector'])
            html += "<ul>"
            for key, val in summary.items():
                html += f"<li><strong>{key[0]}</strong>: {val['count']} occurrences. Fix: {key[1]}</li>"
            html += "</ul>"
            html += """
                </div>
                """
            # After responsive issues, update responsiveness scores
            if hasattr(self.results, 'update_responsiveness_scores'):
                self.results.update_responsiveness_scores()
            # --- Performance Section ---
            html += """
                <div class=\"card\">
                    <h2>Performance</h2>
            """
            # Merge warnings from failed steps and self.results.warnings
            all_warnings = []
            for fail in self.results.failed:
                if isinstance(fail, dict) and "issues" in fail and fail["issues"]:
                    crits = [i for i in fail["issues"] if i.get("severity") == "Critical"]
                    if not crits:
                        all_warnings.append(fail)
            if getattr(self.results, 'warnings', []):
                all_warnings.extend(self.results.warnings)
            if all_warnings:
                html += "<h3>Warnings</h3><ul>"
                for warn in all_warnings:
                    html += f'<li><span class="badge warning">Warning</span> <b>{warn.get("step", warn.get("reason", "Warning"))}:</b> {warn.get("reason", "")}</li>'
                html += "</ul>"
            # Only show 'No performance issues found.' if there are truly no warnings and no slow pages
            if not all_warnings and not getattr(self.results, 'slow_pages', []):
                html += "<p>No performance issues found.</p>"
            html += "</div>"
            
            # Interactive Element Summary Section (new section)
            summary = {}
            if hasattr(self.results, 'interaction_summary') and self.results.interaction_summary:
                summary = self.results.interaction_summary
                html += """
                    <div class=\"card\">
                        <h2>Interactive Element Testing Summary</h2>
                """
                # Add summary stats
                html += f"""
                    <div class=\"stats\">
                        <div class=\"stat-card\">
                            <div class=\"stat-label\">Total Tested</div>
                            <div class=\"stat-number\">{summary.get("total_tested", 0)}</div>
                        </div>
                        <div class=\"stat-card\">
                            <div class=\"stat-label\">Successful</div>
                            <div class=\"stat-number success\">{summary.get("successful", 0)}</div>
                        </div>
                        <div class=\"stat-card\">
                            <div class=\"stat-label\">Content Changed</div>
                            <div class=\"stat-number success\">{summary.get("content_changed", 0)}</div>
                        </div>
                        <div class=\"stat-card\">
                            <div class=\"stat-label\">URL Changed</div>
                            <div class=\"stat-number success\">{summary.get("url_changed", 0)}</div>
                        </div>
                        <div class=\"stat-card\">
                            <div class=\"stat-label\">Failed</div>
                            <div class=\"stat-number error\">{summary.get("failed", 0)}</div>
                        </div>
                    </div>
                """
                # Add issues table if there are any
                if summary.get("issues"):
                    html += """
                        <h3>Interactive Element Issues</h3>
                        <table>
                            <tr>
                                <th>Element</th>
                                <th>Type</th>
                                <th>Issue</th>
                                <th>Load Time</th>
                            </tr>
                    """
                    for issue in summary.get("issues", []):
                        issue_type = issue.get('issue', 'Unknown issue')
                        issue_class = 'warning' if 'no visible change' in issue_type.lower() else 'error'
                        html += f"""
                            <tr class=\"{issue_class}\">
                                <td>{issue.get('element', 'Unknown')}</td>
                                <td>{issue.get('type', 'Unknown')}</td>
                                <td>{issue_type}</td>
                                <td>{issue.get('load_time', 'N/A')}</td>
                            </tr>
                        """
                    html += "</table>"
                html += "</div>"
            
            # Broken Links Section
            html += """
                <div class=\"card\">
                    <h2>Broken Links</h2>
            """
            if getattr(self.results, 'broken_links', []):
                html += "<ul>"
                for link in self.results.broken_links:
                    html += f"<li>{link}</li>"
                html += "</ul>"
            else:
                html += "<p>No broken links found.</p>"
            html += "</div>"
            # JavaScript Errors Section
            html += """
                <div class=\"card\">
                    <h2>JavaScript Issues</h2>
            """
            if getattr(self.results, 'js_errors', []):
                error_types = {}
                for error in self.results.js_errors:
                    error_msg = error["message"]
                    if error_msg not in error_types:
                        error_types[error_msg] = 1
                    else:
                        error_types[error_msg] += 1
                for msg, count in error_types.items():
                    html += f"<p>{msg} (x{count})</p>"
            else:
                html += "<p>No JavaScript errors found.</p>"
            html += "</div>"
            # Test Details Section
            html += """
                <div class=\"card\">
                    <h2>Test Details</h2>
            """
            if filtered_passed:
                html += "<h3>Passed Tests</h3><ul>"
                for test in filtered_passed:
                    step = test.get("step", "Not Applicable")
                    load_time = test.get("load_time", "N/A")
                    if load_time not in ["N/A", "N/As", None]:
                        html += f"<li>{step} ({load_time}s)</li>"
                    else:
                        html += f"<li>{step}</li>"
                html += "</ul>"
            else:
                html += "<p>No passed tests.</p>"
            # Group failed tests by error/reason
            failed_tests = filtered_failed
            # Collect URLs of navigation failures to add to broken links
            nav_failed_urls = set()
            for test in failed_tests:
                reason = test.get("reason") or test.get("error") or ""
                url = test.get("url", "")
                if 'navigation failed' in reason.lower() and url:
                    nav_failed_urls.add(url)
            # Add navigation failed URLs to broken_links if not already present
            if hasattr(self.results, 'broken_links') and isinstance(self.results.broken_links, list):
                for url in nav_failed_urls:
                    if url and url not in self.results.broken_links:
                        self.results.broken_links.append(url)
            if failed_tests:
                html += '<h3 style="color:#d93025;">Failed Tests</h3><ul>'
                for test in failed_tests:
                    reason = test.get("reason") or test.get("error") or "[No error message provided]"
                    step = test.get("step") or "[Step name missing]"
                    url = test.get("url", "N/A")
                    if step == '[Step name missing]' and reason == '[No error message provided]':
                        continue
                    if 'navigation failed' in reason.lower() or 'failed to navigate' in reason.lower():
                        html += f'<li style="color:#d93025;"><b>{step}</b>: {reason} <a href="{url}" target="_blank">🔗</a></li>'
                    elif 'http status' in reason.lower() or '405' in reason or 'method not allowed' in reason.lower():
                        html += f'<li style="color:#d93025;"><b>{step}</b>: {reason} at <code>{url}</code></li>'
                    else:
                        html += f'<li style="color:#d93025;"><b>{step}</b>: {reason}</li>'
                html += '</ul>'
            else:
                html += '<p>No failed tests.</p>'
            html += "</div>"
            # Recommendations Section (HTML, always show)
            html += """
                <div class=\"card\">
                    <h2>Recommendations</h2>
            """
            wrote_any = False
            # Performance
            if getattr(self.results, 'slow_pages', []):
                html += "<h3>Performance Improvements</h3>"
                html += "<ul>"
                html += "<li>The following pages were slow to load (over 2s):<ul>"
                for page in self.results.slow_pages[:5]:
                    html += f"<li>{page['url']} ({page['load_time']}s)</li>"
                html += "</ul></li>"
                html += "<li>Suggestions:<ul>"
                html += "<li>Optimize images (compress, use WebP)</li>"
                html += "<li>Minimize and defer JavaScript/CSS</li>"
                html += "<li>Use lazy loading for images</li>"
                html += "<li>Audit with Chrome DevTools or Lighthouse</li>"
                html += "</ul></li>"
                html += "</ul>"
                wrote_any = True
            # JavaScript Errors
            if getattr(self.results, 'js_errors', []):
                html += "<h3>JavaScript Issues</h3>"
                html += "<ul>"
                html += "<li>JavaScript errors were detected.</li>"
                html += "<li>Use browser dev tools to debug errors.</li>"
                html += "<li>Check for deprecated APIs or syntax.</li>"
                html += "<li>Review recent code changes.</li>"
                html += "</ul>"
                wrote_any = True
            # Broken Links
            if getattr(self.results, 'broken_links', []):
                html += "<h3>Broken Links</h3>"
                html += "<ul>"
                html += "<li>Broken links were found.</li>"
                html += "<li>Fix or remove broken links.</li>"
                html += "<li>Use a site-wide link checker.</li>"
                html += "</ul>"
                wrote_any = True
            # UI/Accessibility Issues
            if hasattr(self.results, 'ui_issue_summary') and self.results.ui_issue_summary:
                html += "<h3>UI/Accessibility Issues</h3>"
                html += "<ul>"
                for issue in self.results.ui_issue_summary:
                    html += f"<li>{issue['issue_type']}: {issue['count']} occurrences. Fix: {issue['fix']}</li>"
                html += "<li>Use axe-core or Lighthouse for accessibility testing.</li>"
                html += "</ul>"
                wrote_any = True
            # SSL/Security
            if hasattr(self.results, 'ssl_status') and self.results.ssl_status:
                ssl_status = self.results.ssl_status.get('status', '').lower()
                if ssl_status != 'valid':
                    html += "<h3>Security Issues</h3>"
                    html += "<ul>"
                    html += "<li>SSL certificate is not valid.</li>"
                    html += "<li>Renew certificate and ensure HTTPS everywhere.</li>"
                    html += "</ul>"
                    wrote_any = True
            # Responsive Issues
            if hasattr(self.results, 'responsive_issue_summary') and self.results.responsive_issue_summary:
                html += "<h3>Responsive Design Issues</h3><ul>"
                summary = {}
                for issue in self.results.responsive_issue_summary:
                    key = (issue['issue_type'], issue.get('fix', ''))
                    if key not in summary:
                        summary[key] = {
                            'issue_type': issue['issue_type'],
                            'fix': issue.get('fix', ''),
                            'severity': issue.get('severity', ''),
                            'count': 0,
                            'examples': set()
                        }
                    summary[key]['count'] += issue.get('count', 1)
                    if 'example_selector' in issue and issue['example_selector']:
                        summary[key]['examples'].add(issue['example_selector'])
                for key, val in summary.items():
                    html += f"<li><strong>{key[0]}</strong>: {val['count']} occurrences. Fix: {key[1]}</li>"
                html += "<li>Test on multiple devices and viewports.</li>"
                html += "</ul>"
                wrote_any = True
            # Interaction Reliability
            if summary.get("issues"):
                html += "<h3>Interaction Reliability</h3>"
                html += "<ul>"
                html += "<li>Review elements marked as 'no visible change' for potential improvements in interaction logic.</li>"
                html += "<li>Ensure elements are fully loaded and visible before interaction.</li>"
                html += "<li>Consider adding more specific result selectors for content change detection.</li>"
                html += "</ul>"
                wrote_any = True
            # If nothing specific, show maintenance
            if not wrote_any:
                html += "<h3>Maintenance</h3>"
                html += "<ol>"
                html += "<li>📈 Monitor performance metrics</li>"
                html += "<li>🔍 Regular testing of critical paths</li>"
                html += "<li>🔒 Keep security measures up to date</li>"
                html += "</ol>"
            html += """
                </div>
            </div>
        </body>
        </html>
        """
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(html)
            return str(report_file)
        except Exception as e:
            print(f"Error generating HTML report: {str(e)}")
            return ""

    def _get_status_class(self, rate: float) -> str:
        """Get the appropriate status class based on rate"""
        if rate >= 90:
            return 'success'
        elif rate >= 70:
            return 'warning'
        return 'error'


def generate_report_from_results_file(results_file: str) -> str:
    """
    Generate a report from a saved results JSON file
    
    Args:
        results_file: Path to the results JSON file
        
    Returns:
        Path to the generated report file
    """
    try:
        with open(results_file, "r") as f:
            data = json.load(f)
        
        from qa_bot import TestResults
        # Convert the JSON data to a TestResults object
        results = TestResults(**data)
        
        # Generate and return the report
        generator = MarkdownReportGenerator(results)
        return generator.generate()
    except Exception as e:
        print(f"Error generating report from results file: {str(e)}")
        return ""


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        results_file = sys.argv[1]
        report_path = generate_report_from_results_file(results_file)
        print(f"Report generated: {report_path}")
    else:
        print("Usage: python report_generator.py <results_file.json>") 