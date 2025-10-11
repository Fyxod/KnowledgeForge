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

# Steps to Set Up the Environment (Windows)
# Ollama Setup

### 1. Install Ollama
- Download the Windows installer from [Ollama Downloads](https://ollama.com/download).  
- After installation, Ollama runs as a background service and exposes a local server at:  
  **http://localhost:11434**  
- reffer to backend section to change port

Verify the installation:
```powershell
ollama --version
```


### 2. Pull a Base Model
Example: pulling **Qwen 3 (8B parameters)**  
```powershell
ollama pull qwen3:8b
```

> - default model is set to qwen3:8b in core/constant.py
>If you hardware is not supporting it try a smaller model 
> - you might need to re run ollama application in windows after restarting system

## *Please read core/constant.py*

> In line no 4 Change the `OLLAMA_MODEL` name to the model you want to use.


# Setting Up the Backend Server

Follow these steps to set up and run the backend server:


### 1. Create a Python Virtual Environment (Please use python 3.11 for this)

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
### 3. Please paste .env file in project root 

### 4. Start the Server

run the FastAPI server:

```bash
python run.py
```

The server will start at:

```
http://127.0.0.1:3000
```

# Frontend Setup

Follow these steps to set up and run the frontend server:


## 1. Prerequisites

- **Node.js** must be installed on your system.  
- Verify installation:

```bash
node -v
npm -v
```


## 2. Navigate to the Frontend Directory

```bash
cd Frontend
```

## 3. Install Dependencies

```bash
npm i
```


## 4. Start the Development Server

```bash
npm run dev
```


