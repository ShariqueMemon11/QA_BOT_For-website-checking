import os
import sys
from pathlib import Path
from flow_manager import FlowManager
import subprocess

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_login_credentials():
    needs_login = input("Does this site require login? (y/N): ").strip().lower() == 'y'
    if needs_login:
        username = input("Enter username/email: ").strip()
        password = input("Enter password: ").strip()
        return username, password
    return '', ''

def run_full_test():
    clear_screen()
    url = input("Enter website URL: ").strip()
    flow_name = "temp_full_site_test"  # Always use your full-site flow
    environment = "prod"
    username, password = get_login_credentials()
    cmd = [sys.executable, "qa_bot.py", "run-flow", url, flow_name, "--environment", environment]
    if username:
        cmd += ["--username", username]
    if password:
        cmd += ["--password", password]
    print(f"[INFO] Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            print("[SUCCESS] Flow completed.")
        else:
            print(f"[ERROR] Flow failed with exit code {result.returncode}.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Flow failed: {e}")
    input("Press Enter to continue...")

def run_test_flow():
    clear_screen()
    url = input("Enter website URL: ").strip()
    flow_name = input("Enter flow name (YAML file without .yaml): ").strip()
    environment = input("Enter environment (prod/uat): ").strip() or "prod"
    username, password = get_login_credentials()
    cmd = [sys.executable, "qa_bot.py", "run-flow", url, flow_name, "--environment", environment]
    if username:
        cmd += ["--username", username]
    if password:
        cmd += ["--password", password]
    print(f"[INFO] Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            print("[SUCCESS] Flow completed.")
        else:
            print(f"[ERROR] Flow failed with exit code {result.returncode}.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Flow failed: {e}")
    input("Press Enter to continue...")

def create_new_flow():
    clear_screen()
    flow_name = input("Enter new flow name: ").strip()
    environment = input("Enter environment (prod/uat): ").strip() or "prod"
    description = input("Enter plain English description of the flow: ").strip()
    cmd = [sys.executable, "qa_bot.py", "generate-flow", flow_name, "--environment", environment, "--description", description]
    print(f"[INFO] Running: {' '.join(cmd)}")
    subprocess.run(cmd)
    input("Press Enter to continue...")

def list_flows():
    clear_screen()
    fm = FlowManager()
    flows = fm.list_flows("prod")
    print("\nAvailable flows in 'prod':")
    for f in flows.get("prod", []):
        print(f"- {f}")
    flows = fm.list_flows("uat")
    print("\nAvailable flows in 'uat':")
    for f in flows.get("uat", []):
        print(f"- {f}")
    input("Press Enter to continue...")

def edit_flow():
    clear_screen()
    flows_dir = Path("flows")
    all_flows = list(flows_dir.glob("**/*.yaml"))
    if not all_flows:
        print("No flows found.")
        input("Press Enter to continue...")
        return
    print("Available flows:")
    for idx, flow in enumerate(all_flows, 1):
        print(f"{idx}. {flow.relative_to(flows_dir)}")
    choice = input("Enter flow number to edit (or press Enter to cancel): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(all_flows):
        flow_path = all_flows[int(choice)-1]
        editor = os.environ.get("EDITOR", "notepad" if os.name == "nt" else "nano")
        os.system(f'{editor} "{flow_path}"')
    else:
        print("Cancelled.")
    input("Press Enter to continue...")

def main_menu():
    while True:
        clear_screen()
        print("\n===== QA TESTING BOT - PROFESSIONAL MENU =====")
        print("1. Run a test on a website")
        print("2. Run a test flow")
        print("3. Create a new test flow")
        print("4. List available flows")
        print("5. Edit a flow")
        print("0. Exit")
        choice = input("Select an option: ").strip()
        if choice == '1':
            run_full_test()
        elif choice == '2':
            run_test_flow()
        elif choice == '3':
            create_new_flow()
        elif choice == '4':
            list_flows()
        elif choice == '5':
            edit_flow()
        elif choice == '0':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main_menu() 