import os
import subprocess

CURR_DIR = os.path.dirname(os.path.abspath(__file__))

# Define your scraper script path
scraper_script_path = os.path.join(CURR_DIR, "DBPyppeteerScrap.py")

# List to store subprocesses
subprocesses = []

# Run 5 scrapers
for i in range(10):
    # Use the Python executable to run the scraper script in a new process
    process = subprocess.Popen([os.sys.executable, scraper_script_path, str(i)])
    subprocesses.append(process)

# Wait for all processes to finish
for process in subprocesses:
    process.wait()