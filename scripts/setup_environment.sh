#!/bin/bash
# Weather AI Profile - Environment Setup Script
# Automated setup and configuration for development and production environments

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root for security reasons"
        exit 1
    fi
}

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [[ -f /etc/debian_version ]]; then
            OS="ubuntu"
        elif [[ -f /etc/redhat-release ]]; then
            OS="centos"
        else
            OS="linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        OS="unknown"
        log_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    log_info "Detected OS: $OS"
}

# Install system dependencies
install_system_dependencies() {
    log_info "Installing system dependencies..."
    
    case "$OS" in
        ubuntu)
            sudo apt-get update
            sudo apt-get install -y \
                curl \
                wget \
                git \
                build-essential \
                python3 \
                python3-pip \
                python3-venv \
                nodejs \
                npm \
                docker.io \
                docker-compose \
                mongodb-tools \
                redis-tools \
                jq \
                unzip \
                htop \
                net-tools \
                ca-certificates \
                gnupg \
                lsb-release
            ;;
        centos)
            sudo yum update -y
            sudo yum groupinstall -y "Development Tools"
            sudo yum install -y \
                curl \
                wget \
                git \
                python3 \
                python3-pip \
                nodejs \
                npm \
                docker \
                docker-compose \
                jq \
                unzip \
                htop \
                net-tools
            ;;
        macos)
            # Check if Homebrew is installed
            if ! command -v brew &> /dev/null; then
                log_info "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            
            brew update
            brew install \
                curl \
                wget \
                git \
                python@3.11 \
                node \
                docker \
                docker-compose \
                mongodb/brew/mongodb-community \
                redis \
                jq \
                htop
            ;;
        *)
            log_error "Unsupported OS for automatic dependency installation: $OS"
            exit 1
            ;;
    esac
    
    log_success "System dependencies installed"
}

# Setup Python environment
setup_python_environment() {
    log_info "Setting up Python environment..."
    
    # Create virtual environment
    cd "$PROJECT_ROOT"
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    # Install Python dependencies
    if [[ -f "50_implementation/deployment/requirements.txt" ]]; then
        pip install -r 50_implementation/deployment/requirements.txt
    else
        log_warning "requirements.txt not found, installing basic dependencies"
        pip install \
            fastapi \
            uvicorn \
            pymongo \
            redis \
            pandas \
            numpy \
            scikit-learn \
            aiohttp \
            python-dotenv \
            structlog
    fi
    
    log_success "Python environment setup complete"
}

# Setup databases
setup_databases() {
    log_info "Setting up databases..."
    
    # Create data directories
    mkdir -p "$PROJECT_ROOT/data/mongodb"
    mkdir -p "$PROJECT_ROOT/data/redis"
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Start MongoDB in Docker
    docker run -d \
        --name weather-ai-mongo-dev \
        -p 27017:27017 \
        -v "$PROJECT_ROOT/data/mongodb:/data/db" \
        -e MONGO_INITDB_ROOT_USERNAME=admin \
        -e MONGO_INITDB_ROOT_PASSWORD=password123 \
        mongo:7.0 || log_warning "MongoDB container may already be running"
    
    # Start Redis in Docker
    docker run -d \
        --name weather-ai-redis-dev \
        -p 6379:6379 \
        -v "$PROJECT_ROOT/data/redis:/data" \
        redis:7.2-alpine || log_warning "Redis container may already be running"
    
    # Wait for databases to be ready
    log_info "Waiting for databases to be ready..."
    sleep 10
    
    # Test MongoDB connection
    if docker exec weather-ai-mongo-dev mongosh --eval "db.runCommand('ping')" &> /dev/null; then
        log_success "MongoDB is running and accessible"
    else
        log_warning "MongoDB may not be fully ready yet"
    fi
    
    # Test Redis connection
    if docker exec weather-ai-redis-dev redis-cli ping &> /dev/null; then
        log_success "Redis is running and accessible"
    else
        log_warning "Redis may not be fully ready yet"
    fi
}

# Create configuration files
create_configuration_files() {
    log_info "Creating configuration files..."
    
    # Create config directory
    mkdir -p "$PROJECT_ROOT/config"
    
    # Development environment configuration
    cat > "$PROJECT_ROOT/config/development.json" << 'EOF'
{
  "environment": "development",
  "mongodb": {
    "uri": "mongodb://admin:password123@localhost:27017/weather_ai_profile?authSource=admin",
    "database": "weather_ai_profile"
  },
  "redis": {
    "host": "localhost",
    "port": 6379,
    "db": 0
  },
  "weather_apis": {
    "openweathermap": {
      "api_key": "your_api_key_here",
      "base_url": "http://api.openweathermap.org/data/2.5"
    }
  },
  "locations": {
    "seguin_tx": {
      "name": "Seguin, TX",
      "latitude": 29.5688,
      "longitude": -97.9647,
      "timezone": "America/Chicago"
    },
    "conroe_tx": {
      "name": "Conroe, TX",
      "latitude": 30.3118,
      "longitude": -95.4560,
      "timezone": "America/Chicago"
    },
    "gunter_tx": {
      "name": "Gunter, TX",
      "latitude": 33.4476,
      "longitude": -96.7474,
      "timezone": "America/Chicago"
    }
  },
  "logging": {
    "level": "INFO",
    "file": "logs/weather-ai.log"
  }
}
EOF

    # Create environment file
    cat > "$PROJECT_ROOT/.env.development" << 'EOF'
# Development Environment Variables
NODE_ENV=development
PYTHON_ENV=development

# Database Configuration
MONGODB_URI=mongodb://admin:password123@localhost:27017/weather_ai_profile?authSource=admin
REDIS_HOST=localhost
REDIS_PORT=6379

# Weather API Keys (replace with actual keys)
OPENWEATHERMAP_API_KEY=your_openweathermap_key_here
NOAA_API_KEY=your_noaa_key_here

# Security
JWT_SECRET=development_jwt_secret_change_in_production
SESSION_SECRET=development_session_secret

# Logging
LOG_LEVEL=DEBUG
EOF

    log_success "Configuration files created"
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."
    
    local errors=0
    
    # Check Python environment
    if source "$PROJECT_ROOT/venv/bin/activate" && python --version &> /dev/null; then
        log_success "Python environment is working"
    else
        log_error "Python environment is not working"
        ((errors++))
    fi
    
    # Check database connections
    if docker exec weather-ai-mongo-dev mongosh --eval "db.runCommand('ping')" &> /dev/null; then
        log_success "MongoDB connection is working"
    else
        log_error "MongoDB connection failed"
        ((errors++))
    fi
    
    if docker exec weather-ai-redis-dev redis-cli ping &> /dev/null; then
        log_success "Redis connection is working"
    else
        log_error "Redis connection failed"
        ((errors++))
    fi
    
    if [[ $errors -eq 0 ]]; then
        log_success "All verification checks passed!"
        return 0
    else
        log_error "$errors verification check(s) failed"
        return 1
    fi
}

# Display setup summary
show_setup_summary() {
    log_info "Setup Summary:"
    echo
    echo "🎉 Weather AI Profile development environment setup complete!"
    echo
    echo "📁 Project Structure:"
    echo "  • Python virtual environment: venv/"
    echo "  • Configuration files: config/"
    echo "  • Logs directory: logs/"
    echo "  • Data directory: data/"
    echo
    echo "🐳 Docker Containers:"
    echo "  • MongoDB: weather-ai-mongo-dev (port 27017)"
    echo "  • Redis: weather-ai-redis-dev (port 6379)"
    echo
    echo "📝 Next Steps:"
    echo "  1. Update .env.development with your weather API keys"
    echo "  2. Review config/development.json settings"
    echo "  3. Activate Python environment: source venv/bin/activate"
    echo "  4. Start development services"
    echo
    log_warning "Remember to update API keys in .env.development before running the system!"
}

# Main setup function
main() {
    local setup_type=${1:-"full"}
    
    echo "======================================"
    echo "Weather AI Profile - Environment Setup"
    echo "======================================"
    echo
    
    case "$setup_type" in
        "minimal")
            log_info "Running minimal setup..."
            check_root
            detect_os
            setup_python_environment
            create_configuration_files
            ;;
        "full"|*)
            log_info "Running full setup..."
            check_root
            detect_os
            install_system_dependencies
            setup_python_environment
            setup_databases
            create_configuration_files
            verify_installation
            show_setup_summary
            ;;
    esac
    
    log_success "Environment setup completed successfully!"
}

# Handle script interruption
trap 'log_error "Script interrupted"; exit 130' INT TERM

# Run main function
main "$@"