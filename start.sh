#!/bin/bash

# Color codes for better readability
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Default values
DEFAULT_MONGODB_URI="mongodb://localhost:27017"
DEFAULT_PORT=8002
DEFAULT_FRONTEND_PORT=3000

# Load environment variables from .env file
if [ -f .env ]; then
  echo -e "${GREEN}Loading environment variables from .env file...${NC}"
  export $(grep -v '^#' .env | xargs)
else
  echo -e "${YELLOW}Warning: .env file not found. Using default configuration:${NC}"
  echo -e "  - MongoDB URI: ${YELLOW}$DEFAULT_MONGODB_URI${NC}"
  echo -e "  - Backend port: ${YELLOW}$DEFAULT_PORT${NC}"
  echo -e "  - Frontend port: ${YELLOW}$DEFAULT_FRONTEND_PORT${NC}"
  echo -e "${YELLOW}To use custom settings, create a .env file (see README.md)${NC}"
  
  # Set default values when .env is missing
  MONGODB_URI=$DEFAULT_MONGODB_URI
fi

# Define ports
BACKEND_PORT=${PORT:-$DEFAULT_PORT}
FRONTEND_PORT=${FRONTEND_PORT:-$DEFAULT_FRONTEND_PORT}

echo -e "===================================="
echo -e "  Predicate Device Analyzer Startup "
echo -e "===================================="

# Function to check if a port is in use
is_port_in_use() {
  lsof -i:"$1" >/dev/null 2>&1
  return $?
}

# Function to kill processes on a specific port
kill_port_process() {
  echo "Checking for processes using port $1..."
  local PID=$(lsof -t -i:$1 -sTCP:LISTEN 2>/dev/null)
  if [ -n "$PID" ]; then
    echo "Killing process on port $1..."
    kill -9 $PID 2>/dev/null
  else
    echo "No process found using port $1"
  fi
}

# Function to check if local MongoDB is running
check_mongodb() {
  if [[ "$MONGODB_URI" == "mongodb://localhost"* ]]; then
    echo -e "${YELLOW}Checking if local MongoDB is running...${NC}"
    nc -z localhost 27017 > /dev/null 2>&1
    if [ $? -ne 0 ]; then
      echo -e "${RED}Error: Local MongoDB is not running!${NC}"
      echo -e "${YELLOW}Please start MongoDB service before running this application.${NC}"
      echo -e "Run one of the following commands based on your system:"
      echo -e "  - ${GREEN}sudo systemctl start mongod${NC} (Linux with systemd)"
      echo -e "  - ${GREEN}brew services start mongodb-community${NC} (macOS with Homebrew)"
      echo -e "  - ${GREEN}net start MongoDB${NC} (Windows)"
      exit 1
    fi
    echo -e "${GREEN}Local MongoDB is running.${NC}"
  fi
}

# Cleanup function
cleanup() {
  echo "Shutting down servers..."
  echo "Stopping backend server (PID: $BACKEND_PID)..."
  echo "Stopping frontend server (PID: $FRONTEND_PID)..."
  kill -SIGINT $BACKEND_PID $FRONTEND_PID 2>/dev/null
  
  # Double-check and force kill if needed
  kill_port_process $BACKEND_PORT
  kill_port_process $FRONTEND_PORT
  
  echo "Cleanup complete."
  exit 0
}

# Set up trap to run cleanup on exit
trap cleanup SIGINT SIGTERM

# Check MongoDB if we're using local instance
check_mongodb

# Kill any existing processes using our ports
echo "Killing any existing processes..."
kill_port_process $BACKEND_PORT
kill_port_process $FRONTEND_PORT

# Start the FastAPI backend server
echo "Starting FastAPI backend on port $BACKEND_PORT..."
MONGODB_URI="$MONGODB_URI" PORT=$BACKEND_PORT python3 src/main.py 2>&1 | sed "s/^/${BLUE}[BACKEND]${NC} /" &
BACKEND_PID=$!

# Wait longer to ensure backend is starting properly
echo "Waiting for backend to start..."
for i in {1..10}; do
  if is_port_in_use $BACKEND_PORT; then
    echo -e "${GREEN}Backend started successfully! (PID: $BACKEND_PID)${NC}"
    break
  fi
  echo "Waiting... ($i/10)"
  sleep 2
  # If this is the last attempt and the port is still not in use
  if [ $i -eq 10 ] && ! is_port_in_use $BACKEND_PORT; then
    echo -e "${RED}Failed to start backend server!${NC}"
    cleanup
    exit 1
  fi
done

# Start the React frontend
echo "Starting React frontend on port $FRONTEND_PORT..."
cd client && PORT=$FRONTEND_PORT npm start 2>&1 | sed "s/^/${BLUE}[FRONTEND]${NC} /" &
FRONTEND_PID=$!

# Wait for frontend to start with improved checking
echo "Waiting for frontend to start..."
for i in {1..15}; do
  if is_port_in_use $FRONTEND_PORT; then
    echo -e "${GREEN}Frontend started successfully! (PID: $FRONTEND_PID)${NC}"
    break
  fi
  echo "Waiting... ($i/15)"
  sleep 2
  # If this is the last attempt and the port is still not in use
  if [ $i -eq 15 ] && ! is_port_in_use $FRONTEND_PORT; then
    echo -e "${RED}Failed to start frontend server!${NC}"
    cleanup
    exit 1
  fi
done

# Print out access info
echo -e "=== ${GREEN}Application is now running${NC} ==="
echo -e "Backend API: ${GREEN}http://localhost:$BACKEND_PORT${NC}"
echo -e "Frontend UI: ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
echo -e "Press ${YELLOW}Ctrl+C${NC} to stop both servers."

# Wait for frontend process
wait $FRONTEND_PID
cleanup 