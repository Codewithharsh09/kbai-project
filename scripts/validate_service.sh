#!/bin/bash
# =============================================================================
# AWS CODEDEPLOY VALIDATE SERVICE SCRIPT - FLASK ENTERPRISE TEMPLATE
# =============================================================================
# This script validates that the Flask application is running correctly
# It performs comprehensive health checks and service validation

set -e  # Exit on any error

# Configuration
APP_NAME="flask-enterprise-app"
APP_DIR="/var/www/${APP_NAME}"
LOG_FILE="/var/log/codedeploy-${APP_NAME}.log"
HEALTH_CHECK_RETRIES=10
HEALTH_CHECK_DELAY=3

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Success/Error tracking
VALIDATION_ERRORS=0
VALIDATION_WARNINGS=0

# Function to record validation error
record_error() {
    local message="$1"
    log "❌ ERROR: $message"
    ((VALIDATION_ERRORS++))
}

# Function to record validation warning
record_warning() {
    local message="$1"
    log "⚠️  WARNING: $message"
    ((VALIDATION_WARNINGS++))
}

# Function to record validation success
record_success() {
    local message="$1"
    log "✅ SUCCESS: $message"
}

log "Starting validate_service.sh script for Flask Enterprise Template"

# =============================================================================
# BASIC INFRASTRUCTURE VALIDATION
# =============================================================================

log "=== BASIC INFRASTRUCTURE VALIDATION ==="

# Check if application directory exists
if [ -d "$APP_DIR" ]; then
    record_success "Application directory exists: $APP_DIR"
    cd "$APP_DIR"
else
    record_error "Application directory not found: $APP_DIR"
    exit 1
fi

# Check if required files exist
log "Checking required files..."
REQUIRED_FILES=(
    "wsgi.py"
    "gunicorn.conf.py"
    ".env"
    "venv/bin/python"
    "venv/bin/gunicorn"
    "src/app.py"
    "src/db_setup.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        record_success "Required file exists: $file"
    else
        record_error "Required file missing: $file"
    fi
done

# Check if required directories exist
log "Checking required directories..."
REQUIRED_DIRS=(
    "logs"
    "src"
    "venv"
    "scripts"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        record_success "Required directory exists: $dir"
    else
        record_error "Required directory missing: $dir"
    fi
done

# Check file permissions
log "Checking file permissions..."
if [ -r ".env" ]; then
    record_success "Environment file is readable"
else
    record_error "Environment file is not readable"
fi

if [ -x "venv/bin/python" ]; then
    record_success "Python executable is accessible"
else
    record_error "Python executable is not accessible"
fi

# =============================================================================
# PROCESS VALIDATION
# =============================================================================

log "=== PROCESS VALIDATION ==="

# Check for Gunicorn processes
log "Checking Gunicorn processes..."
gunicorn_pids=$(pgrep -f "gunicorn.*${APP_NAME}" 2>/dev/null || true)

if [ -n "$gunicorn_pids" ]; then
    record_success "Gunicorn processes found: $gunicorn_pids"

    # Count processes
    process_count=$(echo "$gunicorn_pids" | wc -w)
    log "Number of Gunicorn processes: $process_count"

    if [ "$process_count" -ge 2 ]; then
        record_success "Sufficient Gunicorn worker processes running"
    else
        record_warning "Only $process_count Gunicorn process running, consider increasing workers"
    fi
else
    record_error "No Gunicorn processes found for $APP_NAME"
fi

# Check process health (memory, CPU)
log "Checking process resource usage..."
if [ -n "$gunicorn_pids" ]; then
    for pid in $gunicorn_pids; do
        if ps -p "$pid" -o pid,ppid,pcpu,pmem,cmd --no-headers 2>/dev/null; then
            memory_usage=$(ps -p "$pid" -o pmem --no-headers 2>/dev/null | tr -d ' ')
            # shellcheck disable=SC2034
            cpu_usage=$(ps -p "$pid" -o pcpu --no-headers 2>/dev/null | tr -d ' ')

            # Check if memory usage is reasonable (less than 10%)
            # shellcheck disable=SC2046
            if [ $(echo "$memory_usage < 10" | bc -l 2>/dev/null || echo 0) -eq 1 ]; then
                record_success "Process $pid memory usage acceptable: ${memory_usage}%"
            else
                record_warning "Process $pid high memory usage: ${memory_usage}%"
            fi
        fi
    done
fi

# =============================================================================
# SERVICE VALIDATION
# =============================================================================

log "=== SERVICE VALIDATION ==="

# Check Supervisor status
log "Checking Supervisor service..."
if command -v supervisorctl &> /dev/null; then
    if systemctl is-active --quiet supervisor; then
        record_success "Supervisor service is running"

        # Check managed services
        supervisor_status=$(supervisorctl status ${APP_NAME}:* 2>/dev/null || echo "No services found")
        log "Supervisor status: $supervisor_status"

        if echo "$supervisor_status" | grep -q "RUNNING"; then
            record_success "Application services are running under Supervisor"
        else
            record_error "Application services are not running under Supervisor"
        fi
    else
        record_error "Supervisor service is not running"
    fi
else
    record_warning "Supervisorctl not available"
fi

# Check Nginx status
log "Checking Nginx service..."
if systemctl is-active --quiet nginx; then
    record_success "Nginx service is running"

    # Check if our site is enabled
    if [ -f "/etc/nginx/sites-enabled/${APP_NAME}" ]; then
        record_success "Application Nginx site is enabled"
    else
        record_warning "Application Nginx site is not enabled"
    fi

    # Test Nginx configuration
    if nginx -t &>/dev/null; then
        record_success "Nginx configuration is valid"
    else
        record_error "Nginx configuration is invalid"
    fi
else
    record_error "Nginx service is not running"
fi

# =============================================================================
# NETWORK VALIDATION
# =============================================================================

log "=== NETWORK VALIDATION ==="

# Check listening ports
log "Checking listening ports..."

# Check if application is listening on expected port
if netstat -tlnp 2>/dev/null | grep -q ":5000.*gunicorn"; then
    record_success "Application is listening on port 5000"
else
    record_warning "Application may not be listening on port 5000"
fi

# Check if Nginx is listening on HTTP port
if netstat -tlnp 2>/dev/null | grep -q ":80.*nginx"; then
    record_success "Nginx is listening on port 80"
else
    record_error "Nginx is not listening on port 80"
fi

# Check if HTTPS port is available (optional)
if netstat -tlnp 2>/dev/null | grep -q ":443.*nginx"; then
    record_success "Nginx is listening on port 443 (HTTPS)"
else
    record_warning "Nginx is not listening on port 443 (HTTPS not configured)"
fi

# =============================================================================
# DATABASE VALIDATION
# =============================================================================

log "=== DATABASE VALIDATION ==="

# Test database connectivity
log "Testing database connection..."
if [ -f "venv/bin/python" ] && [ -f ".env" ]; then
    source venv/bin/activate
    source .env 2>/dev/null || true

    # Test database connection
    db_test_result=$(python -c "
import sys
sys.path.insert(0, '.')
try:
    from src.db_setup import check_db_connection
    healthy, message = check_db_connection()
    if healthy:
        print('SUCCESS')
    else:
        print(f'ERROR: {message}')
except Exception as e:
    print(f'ERROR: {e}')
" 2>/dev/null)

    if [[ "$db_test_result" == "SUCCESS" ]]; then
        record_success "Database connection is healthy"
    else
        record_error "Database connection failed: $db_test_result"
    fi
else
    record_warning "Unable to test database connection (missing files)"
fi

# =============================================================================
# APPLICATION VALIDATION
# =============================================================================

log "=== APPLICATION VALIDATION ==="

# Test application imports
log "Testing application imports..."
if [ -f "venv/bin/python" ]; then
    source venv/bin/activate

    import_test_result=$(python -c "
import sys
sys.path.insert(0, '.')
try:
    from src.app import create_app
    from src.models.db_model import User
    from src.models.auth import token_required
    print('SUCCESS')
except Exception as e:
    print(f'ERROR: {e}')
" 2>/dev/null)

    if [[ "$import_test_result" == "SUCCESS" ]]; then
        record_success "Application modules import successfully"
    else
        record_error "Application import failed: $import_test_result"
    fi
fi

# =============================================================================
# HTTP ENDPOINT VALIDATION
# =============================================================================

log "=== HTTP ENDPOINT VALIDATION ==="

# Function to test HTTP endpoint
test_endpoint() {
    local url="$1"
    local expected_status="$2"
    local description="$3"

    log "Testing endpoint: $url"

    # Test with curl
    if command -v curl &> /dev/null; then
        response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")

        if [ "$response" = "$expected_status" ]; then
            record_success "$description (Status: $response)"
            return 0
        else
            record_error "$description (Status: $response, Expected: $expected_status)"
            return 1
        fi
    else
        record_warning "curl not available, skipping HTTP test for $description"
        return 1
    fi
}

# Test health check endpoint
log "Testing health check endpoint..."
for attempt in $(seq 1 $HEALTH_CHECK_RETRIES); do
    if test_endpoint "http://localhost/health" "200" "Health check endpoint"; then
        break
    else
        if [ "$attempt" -lt $HEALTH_CHECK_RETRIES ]; then
            log "Health check failed, retrying in ${HEALTH_CHECK_DELAY} seconds... (Attempt $attempt/$HEALTH_CHECK_RETRIES)"
            sleep $HEALTH_CHECK_DELAY
        else
            record_error "Health check endpoint failed after $HEALTH_CHECK_RETRIES attempts"
        fi
    fi
done

# Test main application endpoint
test_endpoint "http://localhost/" "200" "Main application endpoint"

# Test API base endpoint
test_endpoint "http://localhost/api/v1/" "200" "API base endpoint"

# Test static files (if available)
if [ -f "src/static/style.css" ]; then
    test_endpoint "http://localhost/static/style.css" "200" "Static files serving"
fi

# =============================================================================
# SECURITY VALIDATION
# =============================================================================

log "=== SECURITY VALIDATION ==="

# Check file permissions
log "Checking security-related file permissions..."

# .env file should not be world-readable
env_perms=$(stat -c "%a" .env 2>/dev/null || echo "000")
if [ "$env_perms" = "600" ] || [ "$env_perms" = "640" ]; then
    record_success "Environment file has secure permissions ($env_perms)"
else
    record_warning "Environment file permissions may be too open ($env_perms)"
fi

# Check if running as appropriate user
current_user=$(whoami)
if [ "$current_user" = "root" ]; then
    record_warning "Validation running as root user"
else
    record_success "Validation running as non-root user ($current_user)"
fi

# Check for sensitive files in web-accessible areas
log "Checking for sensitive files in web-accessible locations..."
sensitive_patterns=(
    "*.env*"
    "*.key"
    "*.pem"
    "*.log"
    "*config*.py"
)

for pattern in "${sensitive_patterns[@]}"; do
    if find src/static -name "$pattern" 2>/dev/null | grep -q .; then
        record_warning "Potentially sensitive files found in static directory: $pattern"
    fi
done

# =============================================================================
# PERFORMANCE VALIDATION
# =============================================================================

log "=== PERFORMANCE VALIDATION ==="

# Check system resources
log "Checking system resource usage..."

# Memory usage
memory_info=$(free -m | awk 'NR==2{printf "Used: %d MB (%.1f%%), Available: %d MB", $3, $3*100/$2, $7}')
record_success "Memory status: $memory_info"

# Disk usage
disk_usage=$(df -h "$APP_DIR" | awk 'NR==2{printf "Used: %s (%s)", $3, $5}')
record_success "Disk usage for app directory: $disk_usage"

# Load average
load_avg=$(uptime | awk -F'load average:' '{print $2}' | xargs)
record_success "System load average: $load_avg"

# Response time test
log "Testing application response time..."
if command -v curl &> /dev/null; then
    response_time=$(curl -o /dev/null -s -w "%{time_total}" "http://localhost/health" 2>/dev/null || echo "0")
    response_time_ms=$(echo "$response_time * 1000" | bc -l 2>/dev/null || echo "0")

    # shellcheck disable=SC2046
    if [ $(echo "$response_time < 2.0" | bc -l 2>/dev/null || echo 0) -eq 1 ]; then
        record_success "Response time acceptable: ${response_time_ms} ms"
    else
        record_warning "Response time may be slow: ${response_time_ms} ms"
    fi
fi

# =============================================================================
# LOG FILE VALIDATION
# =============================================================================

log "=== LOG FILE VALIDATION ==="

# Check if log files exist and are being written to
log "Checking log files..."
LOG_FILES=(
    "logs/supervisor.log"
    "logs/gunicorn_error.log"
    "logs/gunicorn_access.log"
)

for log_file in "${LOG_FILES[@]}"; do
    if [ -f "$log_file" ]; then
        # Check if file was modified recently (within last hour)
        # shellcheck disable=SC2046
        if [ $(find "$log_file" -mmin -60 2>/dev/null | wc -l) -gt 0 ]; then
            record_success "Log file active: $log_file"
        else
            record_warning "Log file may be stale: $log_file"
        fi

        # Check log size
        log_size=$(stat -c%s "$log_file" 2>/dev/null || echo 0)
        if [ "$log_size" -gt 0 ]; then
            record_success "Log file has content: $log_file (${log_size} bytes)"
        else
            record_warning "Log file is empty: $log_file"
        fi
    else
        record_warning "Log file missing: $log_file"
    fi
done

# Check for error patterns in logs
log "Checking for errors in recent logs..."
if [ -f "logs/gunicorn_error.log" ]; then
    # shellcheck disable=SC2126
    recent_errors=$(tail -n 100 logs/gunicorn_error.log 2>/dev/null | grep -i error | wc -l)
    if [ "$recent_errors" -eq 0 ]; then
        record_success "No recent errors found in Gunicorn logs"
    else
        record_warning "Found $recent_errors recent errors in Gunicorn logs"
    fi
fi

# =============================================================================
# VALIDATION SUMMARY
# =============================================================================

log "=== VALIDATION SUMMARY ==="

# Create validation report
VALIDATION_REPORT="$APP_DIR/validation_report.json"
cat > "$VALIDATION_REPORT" << EOF
{
    "validation_time": "$(date -Iseconds)",
    "validation_status": "$([ $VALIDATION_ERRORS -eq 0 ] && echo "success" || echo "failed")",
    "application_name": "${APP_NAME}",
    "errors": $VALIDATION_ERRORS,
    "warnings": $VALIDATION_WARNINGS,
    "gunicorn_processes": "${gunicorn_pids}",
    "supervisor_running": $(systemctl is-active --quiet supervisor && echo "true" || echo "false"),
    "nginx_running": $(systemctl is-active --quiet nginx && echo "true" || echo "false"),
    "database_healthy": $([ -n "$db_test_result" ] && [ "$db_test_result" = "SUCCESS" ] && echo "true" || echo "false")
}
EOF

chown www-data:www-data "$VALIDATION_REPORT" 2>/dev/null || true

# Print summary
echo ""
echo "=============================================="
echo "📋 VALIDATION SUMMARY"
echo "=============================================="
echo "Total Errors: $VALIDATION_ERRORS"
echo "Total Warnings: $VALIDATION_WARNINGS"
echo ""

if [ $VALIDATION_ERRORS -eq 0 ]; then
    echo "🎉 VALIDATION PASSED"
    echo "Flask Enterprise Template is running correctly!"
    echo ""
    echo "✅ All critical checks passed"
    if [ $VALIDATION_WARNINGS -gt 0 ]; then
        echo "⚠️  $VALIDATION_WARNINGS warnings found (non-critical)"
    fi
    echo ""
    echo "Service Status:"
    echo "  🚀 Application: Running"
    echo "  🌐 Web Server: Active"
    echo "  🗄️  Database: Connected"
    echo "  📊 Health Checks: Passing"
    echo ""
    echo "Access URLs:"
    echo "  🏠 Main: http://$(hostname -I | awk '{print $1}')"
    echo "  ❤️  Health: http://$(hostname -I | awk '{print $1}')/health"
    echo "  🔌 API: http://$(hostname -I | awk '{print $1}')/api/v1/"
else
    echo "❌ VALIDATION FAILED"
    echo "Flask Enterprise Template has critical issues!"
    echo ""
    echo "🚨 $VALIDATION_ERRORS critical errors found"
    echo "⚠️  $VALIDATION_WARNINGS warnings found"
    echo ""
    echo "Please check the logs for detailed error information:"
    echo "  📄 Deployment Log: $LOG_FILE"
    echo "  📄 Application Logs: $APP_DIR/logs/"
    echo "  📄 Validation Report: $VALIDATION_REPORT"
fi

echo "=============================================="

# Final log message
if [ $VALIDATION_ERRORS -eq 0 ]; then
    log "🎉 Validation completed successfully! Application is healthy."
    exit 0
else
    log "❌ Validation failed with $VALIDATION_ERRORS errors"
    exit 1
fi

# TODO: PROJECT_SPECIFIC - Add custom validation steps here
# Examples:
# - Check external API connectivity
# - Validate business-specific configurations
# - Test custom application features
# - Check integration with third-party services
# - Validate custom database schemas