# QA Testing Bot

An automated QA testing bot for websites that detects and tests interactive elements, verifies content changes, and generates comprehensive reports.

## 🔧 Recent Improvements

### 1. Enhanced Interactive Element Detection
- Improved detection of clickable elements using better selectors
- Better classification of element types (buttons, links, tabs, dropdowns, etc.)
- More descriptive naming of elements for better reporting

### 2. Post-Click Content Change Detection
- Now verifies content changes after element interaction
- Uses TreeWalker to detect visible text changes
- Detects table/list content changes (rows, cards, products)
- Tracks URL changes and navigates back when needed

### 3. Load Time Measurement
- Properly measures load time between click and content change
- Reports accurate timing metrics for performance analysis
- Waits intelligently for network idle state

### 4. Element Type Classification
- Smarter rules based on HTML tags, classes, and text
- Better detection of tabs, nav links, dropdowns, and form elements
- Icon button detection with meaningful names

### 5. Table/List Content Detection
- Detects changes in table rows, product cards, and list items
- Reports the number of items before and after interaction
- Helps verify that filters and search functions work correctly

## 📋 Usage

```bash
# Basic usage
python run_qa_bot.py https://example.com --username user --password pass

# Test specific improvements
python qa_bot_test.py https://example.com --username user --password pass
```

## 📊 Reports

The QA bot generates comprehensive reports in both HTML and Markdown formats, including:

- Interactive element inventory with types and names
- Test results showing successful and failed interactions
- Performance metrics including load times
- Content change verification
- Responsive design issues

## 🚀 Requirements

- Python 3.7+
- Playwright
- Rich (for console output)
- Pydantic (for data models)

Install dependencies:
```bash
pip install -r requirements.txt
```

## 🔍 How It Works

1. The bot navigates to the specified website and logs in
2. It scans the page for all interactive elements
3. It tests each element by clicking/interacting with it
4. It verifies content changes after each interaction
5. It generates a comprehensive report of findings

## Features

- **Comprehensive Testing**: Tests UI elements, responsive design, performance, accessibility, and more
- **Accurate Element Detection**: Smart identification of UI elements using advanced detection techniques
- **Interactive Element Testing**: Tests buttons, links, dropdowns, and other interactive elements
- **Responsive Design Testing**: Tests websites across different viewport sizes (mobile, tablet, desktop)
- **Performance Monitoring**: Identifies slow loading pages and other performance issues
- **Detailed Reporting**: Generates HTML and Markdown reports with actionable recommendations
- **Flow-based Testing**: Create custom test flows for specific website features or user journeys

## Installation

### Prerequisites

- Python 3.9+
- pip
- Playwright (browsers will be installed automatically)

### Setup

1. Clone this repository:
   ```
   git clone <repository-url>
   cd qa_testing_bot
   ```

2. Create a virtual environment and activate it:
   ```
python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```
playwright install
```

## Usage

### Quick Start

The simplest way to use the QA bot is with the `run_qa_bot.py` script:

```bash
python run_qa_bot.py https://example.com --username your_username --password your_password
```

This will:
1. Log in to the website using the provided credentials
2. Test interactive elements (buttons, links, forms, etc.)
3. Check responsive design across different viewports
4. Identify performance issues
5. Generate a comprehensive HTML and Markdown report

### Command Line Options

```
usage: run_qa_bot.py [-h] --username USERNAME --password PASSWORD [--no-headless] [--flow FLOW] [--env {prod,uat}] url

Run QA tests with all fixes and improvements

positional arguments:
  url                  Website URL to test

options:
  -h, --help           show this help message and exit
  --username USERNAME  Login username
  --password PASSWORD  Login password
  --no-headless        Run with visible browser
  --flow FLOW          Name of specific flow to run
  --env {prod,uat}     Environment (prod, uat)
```

### Running Custom Flows

To run a specific test flow:

```bash
python run_qa_bot.py https://example.com --username your_username --password your_password --flow login_checkout --env uat
```

### Creating Custom Flows

Flows are defined in YAML files in the `flows/{environment}` directory. Create a new flow file with the following structure:

```yaml
name: login_checkout
description: Test login and checkout process
steps:
  - action: login
    description: Log in to the system
  - action: navigate
    description: Navigate to products page
    url: /products
  - action: click
    description: Click on first product
    selector: .product-card:first-child
  - action: click
    description: Add to cart
    selector: .add-to-cart-button
  - action: navigate
    description: Go to cart
    url: /cart
  - action: click
    description: Proceed to checkout
    selector: .checkout-button
```

## Reports

Reports are generated in the `reports` directory with both HTML and Markdown formats. The reports include:

- Overall test status and success rate
- Interactive element testing results
- Performance issues
- Responsive design scores
- UI/Accessibility issues
- Recommendations for improvement

## Troubleshooting

### Common Issues

1. **Element not found**: Try adjusting selectors in your flow or waiting for elements to load properly.

2. **Authentication failures**: Ensure credentials are correct and check if the login page has changed.

3. **Browser crashes**: Ensure you have enough system resources and update Playwright with:
   ```
   pip install --upgrade playwright
   playwright install
   ```

4. **Slow tests**: Try running in headless mode for better performance.

## Development

### Project Structure

- `qa_bot.py`: Main QA bot implementation
- `run_qa_bot.py`: Unified command line interface
- `report_generator.py`: HTML and Markdown report generation
- `flow_manager.py`: Custom test flow handling
- `flows/`: Directory containing flow definition files

### Extending the Bot

To add new testing capabilities:

1. Add new test methods to the `QABot` class in `qa_bot.py`
2. Update the report generation in `report_generator.py`
3. Add new actions to the flow system if needed

## License

[MIT License](LICENSE) 