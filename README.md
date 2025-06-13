# QA Testing Bot

An automated QA testing bot for websites that logs in, navigates multiple key pages, verifies content loading, captures performance metrics, and generates comprehensive reports.

---

## 🔍 What It Does

1. **Login & Page Navigation**
   - Logs in using provided credentials
   - Navigates through defined site areas (e.g., home, dashboard, products, cart)
   - Waits for each page to load fully before continuing

2. **Performance Tracking**
   - Measures load times for each visited page
   - Flags slow pages (>3s) as warnings
   - Tracks network idle state for reliable metrics

3. **Responsive Design Testing**
   - Evaluates site behavior across mobile, tablet, and desktop viewports
   - Flags layout or visibility issues on smaller screens

4. **Error Detection**
   - Detects JavaScript errors, missing pages, and broken links
   - Tracks overall health of navigated routes

5. **Comprehensive Reporting**
   - Generates detailed HTML and Markdown reports
   - Includes page load summaries, viewport scores, and issues found

---

## 📦 Requirements

- Python 3.9+
- Playwright
- Rich (for console output)
- Pydantic (for models)

Install dependencies:

```bash
pip install -r requirements.txt
playwright install
