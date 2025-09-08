#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE="$SCRIPT_DIR/.env"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root for security reasons"
        exit 1
    fi
}

check_requirements() {
    log_info "Checking system requirements..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    AVAILABLE_SPACE=$(df "$PROJECT_ROOT" | tail -1 | awk '{print $4}')
    REQUIRED_SPACE=10485760
    
    if [[ $AVAILABLE_SPACE -lt $REQUIRED_SPACE ]]; then
        log_error "Insufficient disk space. Required: 10GB, Available: $((AVAILABLE_SPACE/1048576))GB"
        exit 1
    fi
    
    AVAILABLE_MEMORY=$(free -m | grep '^Mem:' | awk '{print $2}')
    REQUIRED_MEMORY=4096
    
    if [[ $AVAILABLE_MEMORY -lt $REQUIRED_MEMORY ]]; then
        log_warning "Low memory detected. Recommended: 4GB, Available: ${AVAILABLE_MEMORY}MB"
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "System requirements check passed"
}

setup_environment() {
    log_info "Setting up environment variables..."
    
    if [[ ! -f "$ENV_FILE" ]]; then
        log_info "Creating environment file from template..."
        cp "$SCRIPT_DIR/.env.template" "$ENV_FILE"
        
        MONGO_PASSWORD=$(openssl rand -base64 32)
        REDIS_PASSWORD=$(openssl rand -base64 32)
        JWT_SECRET=$(openssl rand -base64 64)
        GRAFANA_PASSWORD=$(openssl rand -base64 16)
        
        sed -i "s/CHANGE_ME_MONGO_PASSWORD/$MONGO_PASSWORD/g" "$ENV_FILE"
        sed -i "s/CHANGE_ME_REDIS_PASSWORD/$REDIS_PASSWORD/g" "$ENV_FILE"
        sed -i "s/CHANGE_ME_JWT_SECRET/$JWT_SECRET/g" "$ENV_FILE"
        sed -i "s/CHANGE_ME_GRAFANA_PASSWORD/$GRAFANA_PASSWORD/g" "$ENV_FILE"
        
        log_warning "Environment file created at $ENV_FILE"
        log_warning "Please update the following variables with your actual values:"
        log_warning "- OPENWEATHERMAP_API_KEY"
        log_warning "- NOAA_API_KEY (optional)"
        log_warning "- WEATHERAPI_KEY (optional)"
        log_warning "- S3_BACKUP_BUCKET (for backups)"
        log_warning "- S3_ACCESS_KEY (for backups)"
        log_warning "- S3_SECRET_KEY (for backups)"
        
        read -p "Press Enter after updating the environment file..."
    fi
    
    source "$ENV_FILE"
    
    REQUIRED_VARS=(
        "MONGO_ROOT_USERNAME"
        "MONGO_ROOT_PASSWORD"
        "REDIS_PASSWORD"
        "JWT_SECRET"
        "OPENWEATHERMAP_API_KEY"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    log_success "Environment setup completed"
}

setup_directories() {
    log_info "Creating necessary directories..."
    
    DIRECTORIES=(
        "$PROJECT_ROOT/logs"
        "$PROJECT_ROOT/backups"
        "$PROJECT_ROOT/config"
        "$PROJECT_ROOT/models"
        "$PROJECT_ROOT/monitoring/grafana/dashboards"
        "$PROJECT_ROOT/monitoring/grafana/datasources"
        "$PROJECT_ROOT/nginx/ssl"
        "$PROJECT_ROOT/mongodb/init"
    )
    
    for dir in "${DIRECTORIES[@]}"; do
        mkdir -p "$dir"
        log_info "Created directory: $dir"
    done
    
    chmod 755 "$PROJECT_ROOT/logs"
    chmod 700 "$PROJECT_ROOT/backups"
    chmod 600 "$ENV_FILE"
    
    log_success "Directory setup completed"
}

setup_configuration() {
    log_info "Setting up configuration files..."
    
    cat > "$PROJECT_ROOT/mongodb/init/init-weather-ai.js" << 'EOF'
db = db.getSiblingDB('weather_ai_profile');

db.createCollection('weather_readings');
db.weather_readings.createIndex({ "location_id": 1, "timestamp": -1 });
db.weather_readings.createIndex({ "timestamp": -1 });
db.weather_readings.createIndex({ "data_source": 1, "timestamp": -1 });

db.createCollection('production_events');
db.production_events.createIndex({ "location_id": 1, "timestamp": -1 });
db.production_events.createIndex({ "machine_id": 1, "timestamp": -1 });
db.production_events.createIndex({ "status": 1, "timestamp": -1 });

db.createCollection('weather_alerts');
db.weather_alerts.createIndex({ "location_id": 1, "timestamp": -1 });
db.weather_alerts.createIndex({ "severity": 1, "valid_until": 1 });

db.createCollection('production_optimizations');
db.production_optimizations.createIndex({ "location_id": 1, "timestamp": -1 });
db.production_optimizations.createIndex({ "confidence_score": -1, "timestamp": -1 });

db.createCollection('enriched_production_events');
db.enriched_production_events.createIndex({ "location_id": 1, "timestamp": -1 });
db.enriched_production_events.createIndex({ "machine_id": 1, "timestamp": -1 });

db.createUser({
  user: process.env.MONGO_ROOT_USERNAME,
  pwd: process.env.MONGO_ROOT_PASSWORD,
  roles: [
    { role: "readWrite", db: "weather_ai_profile" },
    { role: "dbAdmin", db: "weather_ai_profile" }
  ]
});

print('Weather AI Profile database initialized successfully');
EOF

    cat > "$PROJECT_ROOT/nginx/nginx.conf" << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream api {
        server api-gateway:8080;
    }
    
    upstream dashboard {
        server dashboard:3000;
    }
    
    server {
        listen 80;
        server_name localhost;
        
        location /health {
            return 200 'healthy\n';
            add_header Content-Type text/plain;
        }
        
        location /api/ {
            proxy_pass http://api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
        
        location / {
            proxy_pass http://dashboard/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

    cat > "$PROJECT_ROOT/monitoring/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'weather-pipeline'
    static_configs:
      - targets: ['weather-pipeline:8080']

  - job_name: 'production-processor'
    static_configs:
      - targets: ['production-processor:8081']

  - job_name: 'correlation-engine'
    static_configs:
      - targets: ['correlation-engine:8082']

  - job_name: 'api-gateway'
    static_configs:
      - targets: ['api-gateway:8080']
EOF

    cat > "$PROJECT_ROOT/monitoring/grafana/datasources/prometheus.yml" << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

    mkdir -p "$PROJECT_ROOT/logging"
    cat > "$PROJECT_ROOT/logging/logstash.conf" << 'EOF'
input {
  file {
    path => "/var/log/weather-ai/*.log"
    start_position => "beginning"
  }
}

filter {
  if [path] =~ "weather-pipeline" {
    mutate { add_tag => "weather-pipeline" }
  } else if [path] =~ "production-processor" {
    mutate { add_tag => "production-processor" }
  } else if [path] =~ "correlation-engine" {
    mutate { add_tag => "correlation-engine" }
  }
  
  grok {
    match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{GREEDYDATA:message}" }
  }
  
  date {
    match => [ "timestamp", "ISO8601" ]
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "weather-ai-logs-%{+YYYY.MM.dd}"
  }
}
EOF

    log_success "Configuration files created"
}

build_images() {
    log_info "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    log_info "Building weather pipeline image..."
    docker build -f Dockerfile.weather-pipeline -t weather-ai/weather-pipeline:latest .
    
    log_info "Building production processor image..."
    docker build -f Dockerfile.production-processor -t weather-ai/production-processor:latest .
    
    log_info "Building correlation engine image..."
    docker build -f Dockerfile.correlation-engine -t weather-ai/correlation-engine:latest .
    
    log_info "Building API gateway image..."
    docker build -f Dockerfile.api-gateway -t weather-ai/api-gateway:latest .
    
    log_info "Building backup service image..."
    docker build -f Dockerfile.backup -t weather-ai/backup:latest .
    
    if [[ -d "$PROJECT_ROOT/frontend" ]]; then
        log_info "Building frontend image..."
        cd "$PROJECT_ROOT/frontend"
        docker build -t weather-ai/dashboard:latest .
        cd "$PROJECT_ROOT"
    fi
    
    log_success "Docker images built successfully"
}

deploy_application() {
    log_info "Deploying Weather AI Profile application..."
    
    cd "$SCRIPT_DIR"
    
    log_info "Starting core infrastructure services..."
    docker-compose up -d mongodb redis zookeeper kafka
    
    log_info "Waiting for core services to be healthy..."
    wait_for_service "mongodb"
    wait_for_service "redis"
    wait_for_service "kafka"
    
    log_info "Starting application services..."
    docker-compose up -d weather-pipeline production-processor correlation-engine api-gateway
    
    log_info "Waiting for application services to be healthy..."
    wait_for_service "weather-pipeline"
    wait_for_service "production-processor"
    wait_for_service "correlation-engine"
    wait_for_service "api-gateway"
    
    log_info "Starting frontend and proxy services..."
    docker-compose up -d dashboard nginx
    
    log_info "Starting monitoring services..."
    docker-compose up -d prometheus grafana elasticsearch logstash kibana
    
    log_info "Starting backup service..."
    docker-compose up -d backup
    
    log_success "Application deployment completed"
}

wait_for_service() {
    local service_name=$1
    local max_attempts=30
    local attempt=1
    
    log_info "Waiting for $service_name to be healthy..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose ps "$service_name" | grep -q "healthy\|Up"; then
            log_success "$service_name is healthy"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts - $service_name not ready yet, waiting..."
        sleep 10
        ((attempt++))
    done
    
    log_error "$service_name failed to become healthy within expected time"
    return 1
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    SERVICES=(
        "mongodb:27017"
        "redis:6379"
        "kafka:9092"
        "api-gateway:8080"
        "dashboard:3000"
        "prometheus:9090"
        "grafana:3000"
        "elasticsearch:9200"
        "kibana:5601"
    )
    
    for service in "${SERVICES[@]}"; do
        service_name=$(echo "$service" | cut -d':' -f1)
        if docker-compose ps "$service_name" | grep -q "Up\|healthy"; then
            log_success "$service_name is running"
        else
            log_error "$service_name is not running properly"
        fi
    done
    
    log_info "Testing API endpoints..."
    
    if curl -f http://localhost:8080/health &> /dev/null; then
        log_success "API Gateway health check passed"
    else
        log_error "API Gateway health check failed"
    fi
    
    if curl -f http://localhost:3000 &> /dev/null; then
        log_success "Dashboard accessibility check passed"
    else
        log_error "Dashboard accessibility check failed"
    fi
    
    log_info "Checking service logs for errors..."
    
    ERROR_COUNT=$(docker-compose logs --tail=100 2>&1 | grep -i error | wc -l)
    if [[ $ERROR_COUNT -gt 0 ]]; then
        log_warning "Found $ERROR_COUNT error messages in logs"
    else
        log_success "No critical errors found in logs"
    fi
    
    log_success "Deployment verification completed"
}

show_deployment_info() {
    log_info "Deployment Information:"
    echo
    echo "🌐 Web Dashboard: http://localhost:3000"
    echo "🔌 API Gateway: http://localhost:8080"
    echo "📊 Grafana: http://localhost:3001 (admin/$(grep GRAFANA_ADMIN_PASSWORD "$ENV_FILE" | cut -d'=' -f2))"
    echo "🔍 Kibana: http://localhost:5601"
    echo "📈 Prometheus: http://localhost:9090"
    echo
    log_info "Useful Commands:"
    echo "  View logs: docker-compose logs -f [service-name]"
    echo "  Stop all: docker-compose down"
    echo "  Restart service: docker-compose restart [service-name]"
    echo "  View status: docker-compose ps"
    echo
    log_info "Configuration files are stored in:"
    echo "  Environment: $ENV_FILE"
    echo "  Docker Compose: $COMPOSE_FILE"
    echo "  Logs: $PROJECT_ROOT/logs/"
    echo "  Backups: $PROJECT_ROOT/backups/"
    echo
}

rollback_deployment() {
    log_warning "Rolling back deployment..."
    
    cd "$SCRIPT_DIR"
    
    docker-compose down
    
    docker image rm -f weather-ai/weather-pipeline:latest || true
    docker image rm -f weather-ai/production-processor:latest || true
    docker image rm -f weather-ai/correlation-engine:latest || true
    docker image rm -f weather-ai/api-gateway:latest || true
    docker image rm -f weather-ai/backup:latest || true
    docker image rm -f weather-ai/dashboard:latest || true
    
    log_success "Rollback completed"
}

cleanup_deployment() {
    log_warning "Cleaning up deployment..."
    
    cd "$SCRIPT_DIR"
    
    read -p "This will remove ALL containers, images, and volumes. Are you sure? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleanup cancelled"
        return 0
    fi
    
    docker-compose down -v --remove-orphans
    
    docker image rm -f weather-ai/weather-pipeline:latest || true
    docker image rm -f weather-ai/production-processor:latest || true
    docker image rm -f weather-ai/correlation-engine:latest || true
    docker image rm -f weather-ai/api-gateway:latest || true
    docker image rm -f weather-ai/backup:latest || true
    docker image rm -f weather-ai/dashboard:latest || true
    
    docker system prune -f
    docker volume prune -f
    docker network prune -f
    
    log_success "Cleanup completed"
}

main() {
    local action=${1:-deploy}
    
    case "$action" in
        "deploy")
            log_info "Starting Weather AI Profile deployment..."
            check_root
            check_requirements
            setup_environment
            setup_directories
            setup_configuration
            build_images
            deploy_application
            verify_deployment
            show_deployment_info
            log_success "Deployment completed successfully!"
            ;;
        "rollback")
            rollback_deployment
            ;;
        "cleanup")
            cleanup_deployment
            ;;
        "verify")
            verify_deployment
            ;;
        "info")
            show_deployment_info
            ;;
        *)
            echo "Usage: $0 [deploy|rollback|cleanup|verify|info]"
            echo
            echo "Commands:"
            echo "  deploy   - Deploy the entire Weather AI Profile system"
            echo "  rollback - Rollback the deployment"
            echo "  cleanup  - Remove all containers, images, and volumes"
            echo "  verify   - Verify the current deployment"
            echo "  info     - Show deployment information"
            exit 1
            ;;
    esac
}

trap 'log_error "Script interrupted"; exit 130' INT TERM

main "$@"