import os
from transformers import pipeline
import shap
import numpy as np

# Get the absolute path of the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load model and tokenizer using the official HuggingFace Hub path
# This removes the need to upload the heavy 'spam_model' folder to GitHub/HuggingFace
try:
    classifier = pipeline("text-classification", model="distilbert-base-uncased", tokenizer="distilbert-base-uncased")
except Exception as e:
    classifier = None
    print(f"Error loading model from Hub: {e}")

# Initialize SHAP explainer
try:
    if classifier is not None:
        explainer = shap.Explainer(classifier)
    else:
        explainer = None
except Exception as e:
    explainer = None
    print(f"Error initializing SHAP explainer: {e}")

def predict_spam(text):
    if classifier is None:
        return "Error: Model not loaded. Please check your internet connection."

    if not text or len(text.strip()) == 0:
        return "Ham"

    try:
        # Manual truncation to 1000 characters for safety
        safe_text = text[:1000]
        result = classifier(safe_text, truncation=True, max_length=512)[0]

        label = result['label']
        if label == 'LABEL_1' or label.lower() == 'spam':
            return "Spam"
        else:
            return "Ham"
    except Exception as e:
        return f"Prediction error: {e}"

def explain_prediction(text):
    if explainer is None or classifier is None:
        return "Error: Explainer not initialized."

    try:
        # Truncate for SHAP safety
        truncated_text = text[:500]
        shap_values = explainer([truncated_text])
        tokens = shap_values.data[0]
        values = shap_values.values[0]
        return list(zip(tokens, values))
    except Exception as e:
        return f"Explanation error: {e}"

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        email_text = " ".join(sys.argv[1:])
        result = predict_spam(email_text)
        print(f"Input: {email_text}\nResult: {result}")
        print("\n--- Explanation ---")
        print(explain_prediction(email_text))
    else:
        print("Please provide the email text as an argument.")
