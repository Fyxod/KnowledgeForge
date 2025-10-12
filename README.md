# Multi-Modal-Enterprise-Knowledge-Synthesis-Platform

![Callout](https://img.shields.io/badge/Warning-CPU%20Only%20Testing-red)

## For Local Testing on CPU

> Running models via Ollama on CPU introduces several **limitations** and potential **failure modes**:  
>
> - **Performance Degradation:** Inference speed will be significantly slower than on GPU.  
> - **Accuracy Issues:** Models may return incomplete, inconsistent, or incorrect results.  
> - **Instruction Non-Compliance:** Responses may ignore formatting or structural requirements, causing failures in downstream processing.  
> - **Resource Consumption:** CPU execution can be highly resource-intensive, leading to system slowdowns or instability during long runs.  
> - **Limited Model Compatibility:** Some larger models may fail to load or run due to excessive CPU and memory requirements. 
> - **Python version:** Please use python 3.11 for this project 
>
> As a result of these constraints, certain features may be **downgraded, restricted, or disabled** when running in CPU-only mode.

---
# Prerequisites

- **Node.js**
- **Tesseract**
- **MongoDB**
- **Python**
- **Ollama**

## Node.js

install from https://nodejs.org/dist/v22.20.0/node-v22.20.0-x64.msi

a msi file will be downloaded. Run the installer and follow the prompts to complete the installation.
- check this option when installing

![alt text](assistance/node.png)
#### Verify installation
```bash
node -v
npm -v
```
if `npm -v` error's out try restarting your terminal / pc / vscode

# Tesseract
- Download the Windows installer from https://github.com/UB-Mannheim/tesseract/releases/download/v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe 

- run the installer

# MongoDB

 install from https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-8.2.1-signed.msi
 - run the installer and follow the prompts to complete the installation.

- an application named "MongoDB Compass" will be installed in your system. open it and follow steps to connect to your local db


- do next next next when prompted between complete and custom select complete  then next next next install

![alt text](assistance/mongo3.png)

- add new connection 

![alt text](assistance/mongo1.png)


- save and connect 

![alt text](assistance/mongo2.png)



# Python
- Download the Windows installer from https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe

- run the installer and follow check the following option when prompted
- check both options, in image one is unchecked

![alt text](assistance/python.png)


# Ollama Setup

### 1. Ollama
- Download the Windows installer from [Ollama Downloads](https://ollama.com/download).  
- After installation, Ollama runs as a background service and exposes a local server at:  
  **http://localhost:11434**  

Verify the installation:
```powershell
ollama --version
```


### 2. Pull a Base Model
Example: pulling **Qwen 3 (8B parameters)**  
```powershell
ollama pull qwen3:8b
```

> - default model is set to qwen3:8b in `core/constant.py`
>If you hardware is not supporting it try a smaller model 
> - you might need to re run ollama application in windows after restarting system

## *Please read core/constant.py*

> In line no 4 Change the `OLLAMA_MODEL` name to the model you want to use.


# Setting Up the  Server's

### run this script if you are in samsung's virtual machine 
 - please use power shell to run this script (right side terminal in vscode)
 
![alt text](assistance/ter.png)
```powershell
prism_vm.ps1
```

### 1. clone the repository

```bash
git clone https://github.com/bugslayer01/Knowledge-Synthesis-Platform.git
```
navigate into the project directory:
```bash
cd Knowledge-Synthesis-Platform
```

Follow these steps to set up and run the backend server:


### 2. Create a Python Virtual Environment (Please use python 3.11 for this)

It's recommended to use a virtual environment to isolate dependencies:

```bash
python -m venv virtualEnv
```


#### Activate the virtual environment:

  - **Windows (PowerShell):**
```powershell
.\virtualEnv\Scripts\activate.ps1
```
- **Windows (Terminal):**
```powershell
.\virtualEnv\Scripts\activate
```
- **Linux / macOS:**(depend on your shell)
```bash
source virtualEnv/bin/activate
```


### 2. Install Dependencies

Make sure you have `pip` updated, then install the required packages:

```bash
pip install -r requirements.txt

```
### 3. Please rename .env.example to .env file in project root

### 4. Start the Server

run the FastAPI server: 
make sure that virtual environment is activated

```bash
python backend.py
```

The server will start at:

```
http://127.0.0.1:3000
```

# Frontend Setup

Follow these steps to set up and run the frontend server:

open a new terminal and run frontend.py
```bash
python frontend.py
```




