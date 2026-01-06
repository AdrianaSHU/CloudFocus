# ☁️ CloudFocus: AI-Powered IoT Attention Monitoring

**CloudFocus** is a privacy-first IoT system designed to monitor engagement and wellness in educational settings. It leverages Edge AI (Raspberry Pi) to analyze facial expressions and drowsiness locally, transmitting only anonymized status data to a secure Cloud Backend (Azure + Django) for visualization and long-term analysis.

---

## 📖 Table of Contents
- [System Overview](#-system-overview)
- [Repository Structure](#-repository-structure)
- [Hardware Architecture](#-hardware-architecture)
- [Key Features](#-key-features)
- [Installation & Setup](#-installation--setup)
    - [Edge Device (Raspberry Pi)](#1-edge-device-setup-raspberry-pi)
    - [Cloud Backend (Azure)](#2-cloud-backend-setup-azure)
- [Usage Guide](#-usage-guide)
- [Tech Stack](#-tech-stack)

---

## 🔭 System Overview

CloudFocus bridges the gap between **Computer Vision** and **Data Privacy**. Instead of streaming video to the cloud, the system processes all biometric data locally on the Edge device.
* **Input:** USB Webcam captures video frames.
* **Processing:** A MobileNetV2/V3 Fusion model (TFLite) detects emotions, while MediaPipe Face Mesh calculates Eye Aspect Ratio (EAR) for drowsiness.
* **Output:** Status labels (`Focused`, `Distracted`, `Drowsy`) are sent to Azure every 60 seconds via secure REST API.

---

## 📂 Repository Structure

This repository follows a monorepo structure containing both the cloud infrastructure and edge device logic:

```text
CloudFocus/
├── cloudfocus_project/       # ☁️ Django Project Configuration (Azure Deployment)
├── focus_tracker/            # ☁️ Core Django App (API & Dashboard Logic)
├── static/                   # ☁️ CSS/JS Assets for Web Dashboard
├── templates/                # ☁️ HTML Templates (Dashboard & Chatbot)
│
├── edge_device/              # ⚡ Raspberry Pi Source Code
│   ├── Model/                # TFLite Model & Training Artifacts
│   │   ├── Confusion Matrxix.png
│   │   ├── rafdb_fusion.tflite
│   │   ├── results.txt
│   │   └── v2_colab.ipynb
│   ├── check_camera.py       # Camera diagnostics script
│   ├── detect_drowsiness.py  # Drowsiness (EAR) logic
│   ├── detect_face.py        # Face detection logic
│   ├── main_edge.py          # Main application loop
│   ├── requirements.txt      # RPi-specific dependencies
│   ├── sense_hat_manager.py  # Controls LED Matrix & Env Sensors
│   └── test.py               # Testing script
│
├── manage.py                 # Django entry point
└── requirements.txt          # Python dependencies for Azure Cloud
```
---

## 🛠 Hardware Architecture

The system is optimized for the following hardware configuration:

Edge Compute: Raspberry Pi 4 Model B (4GB RAM)

Vision Sensor: Logitech C270 HD Webcam (USB)

Chosen over CSI Camera for deployment flexibility and cable length.

Feedback/Env Sensor: Raspberry Pi Sense HAT

Used for visual feedback (LED Matrix) and temperature/humidity logging.

---

## ✨ Key Features

Privacy-by-Design: No images or video ever leave the Raspberry Pi. Only text metadata is stored.

Real-Time Drowsiness Detection: Uses Eye Aspect Ratio (EAR) to detect micro-sleeps and fatigue.

Emotion Recognition: Custom "Fusion-Lite" model (MobileNetV2+V3) trained on RAF-DB & FER-2013 datasets (86% accuracy).

Interactive Dashboard: Visualizes focus trends using Plotly.js for granular time-series analysis.

Wellness Chatbot (RAG): An AI assistant that queries your personal logs to answer questions like "When was I most distracted today?".

Self-Healing Service: Custom systemd scripts ensure the device automatically recovers if the camera is unplugged or the script crashes.

---

## 🚀 Installation & Setup

### 1. Edge Device Setup (Raspberry Pi)
Prerequisites: Raspberry Pi OS (Bookworm 64-bit), Python 3.11.

```text
# 1. Clone the repository to your home folder
cd ~
git clone [https://github.com/YOUR_USERNAME/CloudFocus.git](https://github.com/YOUR_USERNAME/CloudFocus.git)
cd CloudFocus/edge_device

# 2. Create and activate a virtual environment
python -m venv env
source env/bin/activate

# 3. Install Edge dependencies
pip install -r requirements.txt

# 4. Setup the Systemd Service (Auto-start on boot)
sudo cp service_files/cloudfocus.service /etc/systemd/system/
sudo systemctl enable cloudfocus.service
sudo systemctl start cloudfocus.service
```

### 2. Cloud Backend Setup (Azure)
Prerequisites: Azure App Service (B1 Plan), Azure Database for PostgreSQL.

Deployment: Push the root of this repository to your Azure App Service via GitHub Actions or Local Git.

Environment Variables: Configure the following in Azure Settings:

DJANGO_SECRET_KEY: Your secure key

DB_HOST, DB_NAME, DB_USER, DB_PASS: Database credentials

AZURE_OPENAI_KEY: For the RAG Chatbot

Migrations:

```text
python manage.py migrate
python manage.py createsuperuser
```

---

## 🎮 Usage Guide

Start a Session: Log in to the CloudFocus Dashboard and click "Start Session".

Device Feedback (Sense HAT):

🟢 Green: State is Focused (Neutral/Happy).

🟠 Orange: State is Distracted (Head turn / Phone use).

🔴 Red (Flashing): State is Drowsy (Eyes closed > 1 sec).

Analyse: View your real-time timeline on the dashboard or ask the Chatbot for a summary.

---

## 💻 Tech Stack

Edge AI: TensorFlow Lite, OpenCV, MediaPipe Face Mesh.

Backend: Python Django 4.2, Django REST Framework.

Database: PostgreSQL (Azure Managed).

Frontend: HTML5, Bootstrap 5, Plotly.js (Visualization).

DevOps: Git, Systemd, Udev.

---

## 🛡 Ethical Note

This project strictly adheres to GDPR guidelines. The "Check-In" mechanism ensures data is only logged when explicit user consent is active. No biometric identifiers are stored permanently.

```text
### ⚠️ Important Action:
Before you save, look at the line inside the code block that says:
`git clone https://github.com/YOUR_USERNAME/CloudFocus.git`

**Manually replace** `YOUR_USERNAME` with your actual GitHub username (which seems to be `CloudFocus` or similar based on your screenshot, but verify the exact URL). Do **not** put brackets `[]` around it in the code block!
```
