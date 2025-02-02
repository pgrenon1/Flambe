#!/bin/bash

echo "[INFO] Checking flambe service status..."
if systemctl is-active --quiet flambe.service; then
    echo "[INFO] Service is running. Stopping and disabling..."
    sudo systemctl stop flambe.service
    sudo systemctl disable flambe.service
    sudo systemctl daemon-reload
    echo "[INFO] Service stopped and disabled"
else
    echo "[INFO] Service is not running. Starting and enabling..."
    sudo systemctl daemon-reload
    sudo systemctl enable flambe.service
    sudo systemctl start flambe.service
    echo "[INFO] Service status:"
    systemctl status flambe.service
    echo "Press q to continue..."
fi 