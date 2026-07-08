# SecureDocAI Setup & Execution Guide

This guide walks you through setting up and running **SecureDocAI** from scratch on a new machine. Follow these steps sequentially to set up your virtual environment, install dependencies, download language packs, and run the Streamlit application.

---

## 🛠️ Prerequisites

1. **Python 3.11**: Make sure Python 3.11 is installed on your system.
2. **Tesseract OCR Binary**: 
   - **Windows**: Download and run the installer from [Tesseract OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki). Install it to the default path: `C:\Program Files\Tesseract-OCR\tesseract.exe`.
   - **macOS**: Install via Homebrew: `brew install tesseract`
   - **Linux**: Install via apt: `sudo apt-get install tesseract-ocr`

---

## 🚀 Step-by-Step Setup

### Step 1: Create a Clean Virtual Environment (Python 3.11)
To prevent dependency version mismatches (especially with different Streamlit versions), always use a fresh virtual environment:

```powershell
# Verify Python 3.11 installation
py -3.11 --version

# Create the virtual environment named '.venv'
py -3.11 -m venv .venv
```

### Step 2: Activate the Virtual Environment
Activate the environment based on your operating system and shell:

* **Windows PowerShell**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
* **Windows CMD**:
  ```cmd
  .venv\Scripts\activate.bat
  ```
* **macOS / Linux**:
  ```bash
  source .venv/bin/activate
  ```

### Step 3: Upgrade Pip & Install Dependencies
Upgrade the package manager and install all requirements:

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Download Tesseract Language Packs
Run the automated downloader script to download Telugu (`tel`), Hindi (`hin`), and English (`eng`) language models into your local project workspace:

```bash
python download_tessdata.py
```
This script ensures Tesseract can access language dictionaries without requiring write permissions to protected system directories.

### Step 5: Load Test Model File
Run this before launching the app to confirm the custom recognition model loads cleanly:

```bash
python test_model_load.py
```
If you see "Missing keys" or "Unexpected keys" in the output, copy that output back so the model architecture can be corrected. If you get a dummy prediction with no errors, the model loads and runs correctly.

### Step 6: Configure Environment Variables (`.env`)
Create a file named `.env` in the root folder of the project (`d:\Downloads\SecureDocAI\.env`) and configure your Firebase API keys and Google OAuth Client secrets:

```env
# Firebase Configuration
FIREBASE_API_KEY="your-api-key"
FIREBASE_AUTH_DOMAIN="your-auth-domain"
FIREBASE_PROJECT_ID="your-project-id"
FIREBASE_STORAGE_BUCKET="your-storage-bucket"
FIREBASE_MESSAGING_SENDER_ID="your-sender-id"
FIREBASE_APP_ID="your-app-id"

# Google OAuth Credentials
GOOGLE_OAUTH_CLIENT_SECRETS="data/credentials.json"
```

> [!NOTE]
> Ensure your Google OAuth Client Secrets JSON file is saved at the path specified in the `GOOGLE_OAUTH_CLIENT_SECRETS` variable (default is `data/credentials.json`).

---

## 🏃 Running the Application

Once setup is complete, launch the Streamlit server:

```bash
streamlit run app.py
```

Streamlit will compile the files and automatically open your web browser at `http://localhost:8501/`.

---

## 🛡️ Warnings and Console Cleanup
The application has built-in warning filters to keep the console output clean:
- **RequestsDependencyWarning**: Suppressed automatically in the code.
- **EasyOCR CPU Warnings**: Log levels for the `easyocr` module are set to `ERROR` automatically, preventing warnings about missing GPUs from cluttering the console log.
