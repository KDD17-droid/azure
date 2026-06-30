import os
import base64
from flask import Flask, request, jsonify, send_from_directory
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static")

VISION_KEY = os.environ.get("VISION_KEY", "")
VISION_ENDPOINT = os.environ.get("VISION_ENDPOINT", "").rstrip("/")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    if not VISION_KEY or not VISION_ENDPOINT:
        return jsonify({"error": "Azure Vision not configured"}), 500

    data = request.get_json(silent=True) or {}
    image_url = data.get("url")
    image_base64 = data.get("image_base64")

    headers = {
        "Ocp-Apim-Subscription-Key": VISION_KEY
    }

    analyze_url = (
        f"{VISION_ENDPOINT}/vision/v3.2/analyze"
        "?visualFeatures=Brands,Categories,Faces,Tags,Description"
        "&details=Landmarks"
    )

    try:

        # ---------------- IMAGE ----------------
        if image_url:
            headers["Content-Type"] = "application/json"

            analyze_resp = requests.post(
                analyze_url,
                headers=headers,
                json={"url": image_url},
                timeout=30
            )

        elif image_base64:

            if "," in image_base64:
                image_base64 = image_base64.split(",", 1)[1]

            image_bytes = base64.b64decode(image_base64)

            headers["Content-Type"] = "application/octet-stream"

            analyze_resp = requests.post(
                analyze_url,
                headers=headers,
                data=image_bytes,
                timeout=30
            )

        else:
            return jsonify({"error": "No image provided"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    body = analyze_resp.json()

    # ---------------- OCR ----------------
    try:

        read_url = f"{VISION_ENDPOINT}/vision/v3.2/read/analyze"

        if image_url:

            read_resp = requests.post(
                read_url,
                headers={
                    "Ocp-Apim-Subscription-Key": VISION_KEY,
                    "Content-Type": "application/json"
                },
                json={"url": image_url}
            )

        else:

            read_resp = requests.post(
                read_url,
                headers={
                    "Ocp-Apim-Subscription-Key": VISION_KEY,
                    "Content-Type": "application/octet-stream"
                },
                data=image_bytes
            )

        operation = read_resp.headers.get("Operation-Location")

        if operation:

            import time

            for _ in range(10):

                time.sleep(1)

                result = requests.get(
                    operation,
                    headers={
                        "Ocp-Apim-Subscription-Key": VISION_KEY
                    }
                ).json()

                if result["status"] == "succeeded":
                    body["readResult"] = result["analyzeResult"]
                    break

    except Exception:
        pass

    return jsonify(body)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "configured": bool(VISION_KEY and VISION_ENDPOINT)})


if __name__ == "__main__":
    app.run(debug=True)
