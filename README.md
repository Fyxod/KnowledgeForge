# Multi-Modal-Enterprise-Knowledge-Synthesis-Platform

# Build And run loacly 
- docker  (only to be followed on linux operating system )
  <!-- - build image yourself -->
  <!-- - pull from docker hub (--preferred) -->

- Build manually (preferred tor local testing) 


## Docker 

``` bash
git clone https://github.ecodesamsung.com/SRIB-PRISM/TU_25TS14TU_Multi-Modal_Enterprise_Knowledge_Synthesis_Platform.git
```

```bash
cd Multi-Modal-Enterprise-Knowledge-Synthesis-Platform
```


- **make .env file and populate it**

- set backend url to Local
  - ***Navigate*** to Frontend/url.js  and ***uncomment***   export const API_BASE_URL = 'http://localhost:8000';   for local testing 

```bash
docker build -t samsung .
```

```bash
docker run -it \
           --env-file .env \
           --dns=8.8.8.8 \
           -p 3000:8080 \
         -p 8000:8000\
       -v $(pwd)d/data:/data \
           samsung
```


## Build from code
``` bash
git clone https://github.ecodesamsung.com/SRIB-PRISM/TU_25TS14TU_Multi-Modal_Enterprise_Knowledge_Synthesis_Platform.git
```

```bash
cd Multi-Modal-Enterprise-Knowledge-Synthesis-Platform
```

- install tesseract ocr 

  - Linux
    ```bash 
    sudo pacman -S tesseract tesseract-data-eng      # for arch only  please find alternative command for your system
    ```
  - Windows

    from `https://github.com/UB-Mannheim/tesseract/wiki`  install via `tesseract-ocr-w64-setup-5.5.0.20241111.exe` file 

- **make .env file and populate it**

- set backend url to Local
  - ***Navigate*** to `Frontend/url.js`  and ***uncomment***   `export const API_BASE_URL = 'http://localhost:8000';`   for local testing 

- Make a python venv
```python
python -m venv venv
```
- activate venv

```bash
source venv/bin/activate    (linux)

.\env\Scripts\activate      (windows)
```
- install requirement.txt
```bash
pip install -r req.txt     (linux)

pip install -r 311.txt     (windows)
```

- Start Backend 
```bash
uvicorn app.main:app
```

- Start Frontend 
```bash
cd Frontend && npm install && npm run dev
```