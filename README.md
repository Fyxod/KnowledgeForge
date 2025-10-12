# Multi-Modal-Enterprise-Knowledge-Synthesis-Platform

>  - In `Frontend/url.js`  change url to local host for testing
> - assuming that Tesseract ocr is already installed  install from https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe
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


