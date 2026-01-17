FROM grafana/grafana:latest

# Switch to root to install additional packages
USER root

# Install dependencies for potential report generation and plugin installation
RUN apk add --no-cache wget curl unzip

# Switch back to grafana user
USER 472

# Install useful plugins for monitoring dashboards
# State Timeline, Heatmap, and other visualization plugins are built-in
# Install infinity datasource for flexible API queries (optional but useful)
RUN cd /var/lib/grafana/plugins && \
    wget -4 -O infinity.zip https://grafana.com/api/plugins/yesoreyeram-infinity-datasource/versions/latest/download 2>/dev/null && \
    unzip -q infinity.zip 2>/dev/null && \
    rm -f infinity.zip || true

# Copy configuration files
COPY grafana.ini /etc/grafana/grafana.ini
COPY provisioning /etc/grafana/provisioning
COPY dashboards /var/lib/grafana/dashboards

# Set proper permissions
USER root
RUN chown -R 472:472 /var/lib/grafana/dashboards 2>/dev/null || true
USER 472

# Expose Grafana port
EXPOSE 3000

# Default entrypoint from base image will start Grafana
