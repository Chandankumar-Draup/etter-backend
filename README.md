# Etter

A tool to transform HR operations into an intelligent hub, making them smarter, faster,
and more connected through AI-driven automation and seamless integration.

## Project setup:
Python Version >= 3.11


### 1. Setup a redis server
MacOS + Homebrew
```bash
    brew install redis
    brew services start redis
```

Docker
```bash
    docker run -d --name redis -p 6379:6379 redis:latest
```

### 2. Clone the repository
```bash
    git clone https://github.com/Draup/etter-backend.git
```

### 3. Set up the virtual environment
```bash
    python -m venv <venv-name>
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
````

### 4. Install the required packages
```bash
    cd etter-backend
    pip install -r requirements.txt
```

### 5. Configure the environment variables
Create a `.env` file in the root directory and add the necessary environment variables. 
You can refer to the `env_example.txt` file for guidance.

Copy the example file:
```bash
    cp env_example.txt .env
```

Then edit the `.env` file with your actual configuration values:
- Database credentials (ETTER_DB_*)
- JWT secret key (SECRET_KEY)
- Admin secret (ADMIN_SECRET)
- Redis configuration (REDIS_*)
- Simulation provider type (SIMULATION_PROVIDER_TYPE)

### 6. Run the application
```bash
    uvicorn settings.server:etter_app --port 7071
```

### 6. Access the application
Open your web browser and navigate to `http://127.0.0.1:7071/docs/etter` to access the API documentation.
