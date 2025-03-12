#!/bin/bash

set -e

# Define variables
GO2RTC_VERSION="latest"  # You can specify a version instead of "latest"
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/etc/go2rtc"
CONFIG_FILE="$CONFIG_DIR/go2rtc.yaml"
SERVICE_FILE="/etc/systemd/system/go2rtc.service"

echo "Installing dependencies..."
apt update && apt install -y wget curl

echo "Downloading go2rtc..."
ARCH=$(uname -m)
if [[ "$ARCH" == "x86_64" ]]; then
    GO2RTC_ARCH="linux_amd64"
elif [[ "$ARCH" == "aarch64" ]]; then
    GO2RTC_ARCH="linux_arm64"
elif [[ "$ARCH" == "armv7l" ]]; then
    GO2RTC_ARCH="linux_arm"
else
    echo "Unsupported architecture: $ARCH"
    exit 1
fi

GO2RTC_URL="https://github.com/AlexxIT/go2rtc/releases/download/v1.9.8/go2rtc_$GO2RTC_ARCH"
# wget -O "$INSTALL_DIR/go2rtc" "$GO2RTC_URL"
chmod +x "$INSTALL_DIR/go2rtc"

echo "Creating configuration directory..."
mkdir -p "$CONFIG_DIR"

echo "Creating default config file with API and RTSP settings..."
cat <<EOF > "$CONFIG_FILE"
# go2rtc configuration

api:
  listen: ":1984"  # HTTP API Port

rtsp:
  listen: ":8554"  # RTSP Server Port

EOF

echo "Creating systemd service file..."
cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=go2rtc Service
After=network.target

[Service]
ExecStart=$INSTALL_DIR/go2rtc -config $CONFIG_FILE
Restart=always
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=go2rtc
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd..."
systemctl daemon-reload

echo "Enabling and starting go2rtc service..."
systemctl enable go2rtc
systemctl restart go2rtc

echo "Installation complete!"
echo "API is running on port 1984."
echo "RTSP server is running on port 8554."
echo "Check service status with: sudo systemctl status go2rtc"
