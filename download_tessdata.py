import os
import shutil
import urllib.request

def main():
    local_dir = os.path.abspath("tessdata")
    os.makedirs(local_dir, exist_ok=True)
    print(f"Local tessdata directory: {local_dir}")

    # URLs for the traineddata files from the official tessdata_fast repository
    urls = {
        "tel.traineddata": "https://github.com/tesseract-ocr/tessdata_fast/raw/main/tel.traineddata",
        "hin.traineddata": "https://github.com/tesseract-ocr/tessdata_fast/raw/main/hin.traineddata",
        "eng.traineddata": "https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata",
    }

    # Standard Windows path for English model
    default_eng_path = r"C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata"
    local_eng_path = os.path.join(local_dir, "eng.traineddata")

    # Copy existing eng.traineddata if available
    if os.path.exists(default_eng_path) and not os.path.exists(local_eng_path):
        try:
            print("Copying local eng.traineddata...")
            shutil.copy(default_eng_path, local_eng_path)
        except Exception as e:
            print(f"Could not copy eng.traineddata: {e}")

    # Download missing models
    for name, url in urls.items():
        dest = os.path.join(local_dir, name)
        if not os.path.exists(dest):
            print(f"Downloading {name} from {url}...")
            try:
                urllib.request.urlretrieve(url, dest)
                print(f"Successfully downloaded {name}.")
            except Exception as e:
                print(f"Failed to download {name}: {e}")
        else:
            print(f"{name} already exists.")

if __name__ == "__main__":
    main()
