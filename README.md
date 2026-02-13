# Multi-Modal Enterprise Knowledge Synthesis Platform
For windows setup instructions please refer to [Windows_README.md](Windows_README.md)

# Linux systems

## Prerequisites
 Docker(install docker using the following command if not already installed):
   ```bash
      curl -fsSL https://get.docker.com -o get-docker.sh
      sh get-docker.sh
   ```
## Setup Instructions
1. Clone the repository:
   ```bash
    git clone https://github.com/bedrockSp/Multi-Modal-Enterprise-Knowledge-Synthesis-Platform.git
    cd Multi-Modal-Enterprise-Knowledge-Synthesis-Platform
    ```
2. Create a `.env` file in the root directory 
    ```bash
    cp  .env.docker .env
    ```
3. Update the `.env` file with your API keys and other configurations.

4. Change [Constants.py](core/constants.py) as per need (optional)

5. Build image( run this when you make changes to the codebase & first run will take time as it needs to download the base image and setup everything so be patient):
   ```bash
   make build
   ```

6. Run Ollama server: (must run after every restart of the system)
   ```bash
   make ollama
   ```

7. Run the application:
   ```bash
   make run 
    ```