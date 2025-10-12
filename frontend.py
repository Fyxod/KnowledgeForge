import subprocess
import os

# Get the directory where this script is run
project_path = os.getcwd()

# Move into the Frontend folder
frontend_path = os.path.join(project_path, "Frontend")
os.chdir(frontend_path)

# Step 1: Install dependencies
subprocess.run(["npm", "install"], check=True)

# Step 2: Start development server
subprocess.run(["npm", "run", "dev"], check=True)
