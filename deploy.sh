#!/bin/bash

# Production Deployment Script for Pyth Keeper SSE
# Usage: ./deploy.sh [local|docker|k8s]

set -euo pipefail

DEPLOYMENT_TYPE=${1:-"local"}
PROJECT_NAME="pyth-keeper"
IMAGE_TAG="v2.0.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

check_requirements() {
    log "Checking requirements..."

    if [[ ! -f .env ]]; then
        warn ".env file not found. Please copy .env.example to .env and configure it."
        if [[ "$DEPLOYMENT_TYPE" != "k8s" ]]; then
            error "Local and Docker deployments require .env file"
        fi
    fi

    if [[ "$DEPLOYMENT_TYPE" == "docker" ]] && ! command -v docker &> /dev/null; then
        error "Docker is required but not installed"
    fi

    if [[ "$DEPLOYMENT_TYPE" == "k8s" ]] && ! command -v kubectl &> /dev/null; then
        error "kubectl is required but not installed"
    fi
}

install_dependencies() {
    log "Installing Node.js dependencies..."
    npm install
}

build_image() {
    log "Building Docker image..."
    docker build -t ${PROJECT_NAME}:${IMAGE_TAG} .
    docker tag ${PROJECT_NAME}:${IMAGE_TAG} ${PROJECT_NAME}:latest
}

deploy_local() {
    log "Deploying locally..."

    # Create logs directory
    mkdir -p logs

    # Install dependencies
    install_dependencies

    # Start the keeper
    log "Starting Pyth Keeper SSE..."
    node production-keeper-sse.js
}

deploy_docker() {
    log "Deploying with Docker Compose..."

    # Build image
    build_image

    # Create logs directory
    mkdir -p logs
    mkdir -p monitoring/grafana/provisioning/datasources
    mkdir -p monitoring/grafana/provisioning/dashboards

    # Start services
    log "Starting Docker Compose services..."
    docker-compose up -d

    # Wait for services to be ready
    log "Waiting for services to start..."
    sleep 10

    # Check health
    check_docker_health
}

deploy_k8s() {
    log "Deploying to Kubernetes..."

    # Build and tag image (assuming registry push)
    build_image

    # Apply ConfigMap and Secret first
    log "Applying Kubernetes configurations..."
    kubectl apply -f k8s/deployment.yaml

    # Apply HPA
    kubectl apply -f k8s/hpa.yaml

    # Apply ServiceMonitor if Prometheus Operator is available
    if kubectl get crd servicemonitors.monitoring.coreos.com &> /dev/null; then
        kubectl apply -f k8s/servicemonitor.yaml
    else
        warn "Prometheus Operator not found, skipping ServiceMonitor"
    fi

    # Wait for deployment
    log "Waiting for deployment to be ready..."
    kubectl rollout status deployment/pyth-keeper --timeout=300s

    # Check health
    check_k8s_health
}

check_docker_health() {
    log "Checking service health..."

    # Check keeper health
    if curl -f http://localhost:9090/health &> /dev/null; then
        log "✅ Pyth Keeper is healthy"
    else
        error "❌ Pyth Keeper health check failed"
    fi

    # Check Prometheus
    if curl -f http://localhost:9091/-/healthy &> /dev/null; then
        log "✅ Prometheus is healthy"
    else
        warn "⚠️ Prometheus health check failed"
    fi

    # Check Grafana
    if curl -f http://localhost:3001/api/health &> /dev/null; then
        log "✅ Grafana is healthy"
    else
        warn "⚠️ Grafana health check failed"
    fi

    log "🎉 Deployment completed successfully!"
    log "📊 Metrics: http://localhost:9090/metrics"
    log "📈 Prometheus: http://localhost:9091"
    log "📊 Grafana: http://localhost:3001 (admin/admin123)"
    log "🏥 Health: http://localhost:9090/health"
    log "📋 Status: http://localhost:9090/status"
}

check_k8s_health() {
    log "Checking Kubernetes deployment health..."

    # Get service endpoint
    SERVICE_PORT=$(kubectl get svc pyth-keeper-service -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "")

    if [[ -n "$SERVICE_PORT" ]]; then
        HEALTH_URL="http://localhost:${SERVICE_PORT}/health"
    else
        # Use port-forward for ClusterIP
        log "Setting up port-forward for health check..."
        kubectl port-forward svc/pyth-keeper-service 9090:9090 &
        PORT_FORWARD_PID=$!
        sleep 5
        HEALTH_URL="http://localhost:9090/health"
    fi

    # Check health
    if curl -f "$HEALTH_URL" &> /dev/null; then
        log "✅ Pyth Keeper is healthy in Kubernetes"
    else
        error "❌ Pyth Keeper health check failed in Kubernetes"
    fi

    # Cleanup port-forward if used
    if [[ -n "${PORT_FORWARD_PID:-}" ]]; then
        kill $PORT_FORWARD_PID 2>/dev/null || true
    fi

    log "🎉 Kubernetes deployment completed successfully!"
    log "📋 Check status: kubectl get pods -l app=pyth-keeper"
    log "📊 View logs: kubectl logs -l app=pyth-keeper -f"
    log "🔄 Port-forward: kubectl port-forward svc/pyth-keeper-service 9090:9090"
}

cleanup() {
    case "$DEPLOYMENT_TYPE" in
        "docker")
            log "Stopping Docker services..."
            docker-compose down
            ;;
        "k8s")
            log "Cleaning up Kubernetes resources..."
            kubectl delete -f k8s/ --ignore-not-found=true
            ;;
        *)
            log "No cleanup needed for local deployment"
            ;;
    esac
}

show_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  local     Deploy locally (default)"
    echo "  docker    Deploy with Docker Compose"
    echo "  k8s       Deploy to Kubernetes"
    echo "  cleanup   Clean up deployed resources"
    echo "  help      Show this help"
    echo ""
    echo "Environment Variables:"
    echo "  IMAGE_TAG    Docker image tag (default: v2.0.0)"
    echo ""
    echo "Examples:"
    echo "  $0 local                 # Run locally"
    echo "  $0 docker                # Deploy with Docker"
    echo "  $0 k8s                   # Deploy to Kubernetes"
    echo "  $0 cleanup               # Clean up resources"
}

main() {
    case "${DEPLOYMENT_TYPE}" in
        "local")
            check_requirements
            deploy_local
            ;;
        "docker")
            check_requirements
            deploy_docker
            ;;
        "k8s")
            check_requirements
            deploy_k8s
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            error "Unknown deployment type: $DEPLOYMENT_TYPE. Use 'help' for usage."
            ;;
    esac
}

# Trap for cleanup on exit
trap 'error "Deployment interrupted"' INT TERM

# Run main function
main "$@"