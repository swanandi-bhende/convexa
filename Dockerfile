FROM python:3.10-slim

# Install system dependencies, Node.js, and npm
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files first to leverage Docker cache
COPY requirements.txt ./
COPY agents/requirements.txt ./agents/
COPY package.json package-lock.json ./
COPY contracts/package.json contracts/package-lock.json ./contracts/
COPY frontend/package.json frontend/package-lock.json ./frontend/

# Install Node dependencies and Python dependencies
RUN npm install
RUN cd contracts && npm install
RUN cd frontend && npm install
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Compile contracts and build frontend
RUN cd contracts && npx hardhat compile
RUN cd frontend && npm run build

# Make the start script executable
RUN chmod +x start-backend.sh

# Command to start the background worker
CMD ["./start-backend.sh"]
