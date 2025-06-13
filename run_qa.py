#!/usr/bin/env python3
"""
QA Bot Runner - Run QA bot tests on a specific website
"""
import asyncio
import sys
import typer
from qa_bot import QABot, LoginCredentials

app = typer.Typer()

@app.command()
def run(
    url: str = typer.Argument(None, help="Website URL to test"),
    username: str = typer.Option(None, help="Login username"),
    password: str = typer.Option(None, help="Login password"),
    headless: bool = typer.Option(False, help="Run in headless mode")
):
    """Run the QA bot on a website"""
    # Run the QA bot in asyncio context
    asyncio.run(run_qa_test(url, username, password, headless))

async def run_qa_test(url=None, username=None, password=None, headless=False):
    """Run the QA bot with the original functionality"""
    # Get website URL if not provided
    if not url:
        url = input("Enter website URL to test (including https://): ")
        if not url:
            url = "https://uat.parfumhaus.online"  # Default URL
    
    # Get credentials if not provided
    if not username:
        username = input("Enter username (leave empty to skip login): ")
    
    if username and not password:
        password = input("Enter password: ")
    
    print(f"Starting QA Bot test on {url}...")
    bot = QABot(headless=headless)
    await bot.setup()
    
    credentials = None
    if username and password:
        credentials = LoginCredentials(
            username=username,
            password=password
        )
    
    # Run the original test flow with all functionality
    await bot.run_test_flow(
        url=url,
        credentials=credentials,
        generate_report=True
    )
    
    await bot.close()
    print("QA Bot test completed successfully!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        app()
    else:
        asyncio.run(run_qa_test()) 