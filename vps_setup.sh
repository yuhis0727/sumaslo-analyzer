#!/bin/bash
# Oracle Cloud Ubuntu 22.04 (ARM) セットアップスクリプト
# 実行: bash vps_setup.sh

set -e
echo "=== スロットスクレイパー VPS セットアップ ==="

# --- Python 3.11 ---
echo "[1/6] Python 3.11 インストール中..."
sudo apt-get update -q
sudo apt-get install -y python3.11 python3.11-venv python3-pip

# --- Google Chrome (ARM対応: chromium-browser) ---
echo "[2/6] Chromium インストール中..."
sudo apt-get install -y chromium-browser

# --- Xvfb (仮想ディスプレイ: ヘッドレス回避用) ---
echo "[3/6] Xvfb インストール中..."
sudo apt-get install -y xvfb

# --- Python ライブラリ ---
echo "[4/6] Python ライブラリ インストール中..."
pip3 install \
  undetected-chromedriver==3.5.5 \
  selenium \
  beautifulsoup4 \
  httpx \
  curl-cffi \
  cloudscraper

# --- プロジェクトディレクトリ ---
echo "[5/6] プロジェクトディレクトリ作成..."
mkdir -p ~/slot-scraper/data

# --- Xvfb 自動起動サービス ---
echo "[6/6] Xvfb サービス設定..."
sudo tee /etc/systemd/system/xvfb.service > /dev/null << 'EOF'
[Unit]
Description=Xvfb virtual display
After=network.target

[Service]
ExecStart=/usr/bin/Xvfb :99 -screen 0 1920x1080x24
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable xvfb
sudo systemctl start xvfb

echo ""
echo "=== セットアップ完了 ==="
echo "Chromiumパス: $(which chromium-browser)"
echo "Xvfb: $(systemctl is-active xvfb)"
echo ""
echo "次: スクリプトをアップロードして python3 ~/slot-scraper/anaslo_scraper.py を実行"
