
# 🧪 QA Testing Bot

An automated QA testing bot that logs in to a website, navigates through key pages, evaluates performance and responsiveness, detects errors, and generates detailed reports in HTML and Markdown.

---

## ✅ Features

- 🔐 **Login and Authentication**  
  Logs in with provided credentials before scanning the site.

- 🌍 **Multi-Page Navigation**  
  Automatically navigates through important URLs like dashboard, products, cart, etc.

- 🕒 **Performance Monitoring**  
  Tracks page load times, flags slow pages, and waits intelligently for content to load.

- 📱 **Responsive Testing**  
  Checks the website's responsiveness on desktop, tablet, and mobile screen sizes.

- 🧨 **Error Detection**  
  Detects JavaScript errors, missing pages (404s), and broken links.

- 📄 **Comprehensive Reports**  
  Generates well-structured HTML and Markdown reports with clear summaries, test results, and improvement suggestions.

- 🔁 **Optional Flow-Based Testing**  
  Support for YAML-defined custom flows (e.g., login-checkout, product-add-cart).

---

## 🧰 Requirements

- Python 3.9+
- pip
- Playwright
- Rich (console display)
- Pydantic (data validation)

---

## 🔧 Setup Instructions (Full Process)

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/qa-testing-bot.git
cd qa-testing-bot
```

### Step 2: Create a Virtual Environment

#### On Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

#### On macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Install Playwright Browsers

```bash
playwright install
```

---

## ▶️ How to Run the Bot

### Basic Full-Site QA Test

```bash
python run_qa_bot.py https://example.com --username your_email --password your_password
```

### With Visible Browser (Non-Headless Mode)

```bash
python run_qa_bot.py https://example.com --username your_email --password your_password --no-headless
```

### With a Custom Flow

```bash
python run_qa_bot.py https://example.com --username your_email --password your_password --flow login_checkout --env uat
```

---

## 🧪 Defining Custom Flows (Optional)

Create a YAML file in `flows/uat/` like this:

```yaml
name: login_checkout
description: Test login and checkout process
steps:
  - action: login
  - action: navigate
    url: /products
  - action: navigate
    url: /cart
  - action: click
    selector: .checkout-button
```

Then run:

```bash
python run_qa_bot.py https://example.com --username your_email --password your_password --flow login_checkout --env uat
```

---

## 📁 Project Structure

```
qa-testing-bot/
├── run_qa_bot.py            # CLI entry point
├── qa_bot.py                # Core bot logic
├── flow_manager.py          # Flow execution logic
├── report_generator.py      # HTML/Markdown report creation
├── flows/                   # Custom test flows (YAML)
├── reports/                 # Generated output files
├── requirements.txt         # Python dependencies
```

---

## 📄 Output Reports

Saved to `reports/` folder:
- ✅ `report_<timestamp>.html`
- ✅ `report_<timestamp>.md`

Each report includes:
- Navigation steps
- Page load times
- Responsive issues
- JS errors and broken links
- Pass/fail summary
- Suggestions for improvement

---

## 🛠 Troubleshooting

| Problem                  | Solution                                                   |
|--------------------------|------------------------------------------------------------|
| Browser not launching    | Use `--no-headless` or run `playwright install` again      |
| Elements not found       | Confirm selectors in flow or add wait-for-element logic    |
| Login failed             | Double-check username/password and login URL               |
| Blank report             | Check if login succeeded and target pages are reachable    |
| Slow test runs           | Avoid animations, disable headless for debugging           |

---

## 📜 License

MIT License — free for personal and commercial use.
