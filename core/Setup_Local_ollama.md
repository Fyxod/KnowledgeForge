## Open Terminal 
 ```bash
 OLLAMA_HOST=0.0.0.0:11435 OLLAMA_KEEP_ALIVE=-1 ollama serve
 ```
 ## Open new terminal 
 ```bash
 OLLAMA_HOST=0.0.0.0:11434 OLLAMA_KEEP_ALIVE=-1 ollama serve
 ```
 ## load and make custome models
    - if you are running this for the first time please run the following command to setup the models
    ```bash
    ./setmodel.sh
    ```