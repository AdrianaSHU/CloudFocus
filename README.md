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
│   ├── main_edge.py          # Main inference loop (Face + Emotion + Drowsiness)
│   ├── sense_hat_manager.py  # Controls LED Matrix & Env Sensors
│   ├── requirements.txt      # Python dependencies for the Pi
│   ├── models/               # TFLite Model files (Fusion-Lite)
│   └── service_files/        # Systemd & Udev configuration for auto-start
│
├── manage.py                 # Django entry point
└── requirements.txt          # Python dependencies for Azure Cloud
