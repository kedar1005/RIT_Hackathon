"""
CitiZen AI — MobileNetV3 Image Classifier
Predicts complaint category from uploaded photos using a pretrained CNN.
"""
import os
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image

CATEGORIES = [
    'Roads & Potholes',
    'Streetlight & Electricity',
    'Garbage & Waste Management',
    'Water Supply Issues',
    'Drainage & Water Logging',
    'Tree Fall & Maintenance',
    'Traffic & Parking',
    'Public Safety & Others'
]

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
IMAGE_MODEL_PATH = os.path.join(MODEL_DIR, "image_model.pt")

_image_model = None


def load_or_create_image_model():
    """Load fine-tuned model or create pretrained baseline."""
    global _image_model
    try:
        model = models.mobilenet_v3_small(weights='DEFAULT')
        # Replace classifier for 8 categories
        num_features = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(num_features, len(CATEGORIES))

        if os.path.exists(IMAGE_MODEL_PATH):
            try:
                model.load_state_dict(torch.load(IMAGE_MODEL_PATH, map_location='cpu'))
            except Exception:
                pass  # Use pretrained weights as fallback

        model.eval()
        _image_model = model
        return model
    except Exception as e:
        print(f"Error loading image model: {e}")
        _image_model = None
        return None


def get_image_model():
    """Get the loaded image model, creating if needed."""
    global _image_model
    if _image_model is None:
        load_or_create_image_model()
    return _image_model


def predict_from_image(image_path):
    """Predict complaint category from an image file."""
    model = get_image_model()
    if model is None:
        return "Public Safety & Others", 0.3

    try:
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        img = Image.open(image_path).convert('RGB')
        tensor = transform(img).unsqueeze(0)

        with torch.no_grad():
            output = model(tensor)
            probs = torch.softmax(output, dim=1)[0]
            confidence, predicted = torch.max(probs, 0)

        category = CATEGORIES[predicted.item()]
        return category, float(confidence.item())
    except Exception as e:
        print(f"Image prediction error: {e}")
        return "Public Safety & Others", 0.3


def predict_from_pil_image(pil_image):
    """Predict complaint category from a PIL Image object."""
    model = get_image_model()
    if model is None:
        return "Public Safety & Others", 0.3

    try:
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        img = pil_image.convert('RGB')
        tensor = transform(img).unsqueeze(0)

        with torch.no_grad():
            output = model(tensor)
            probs = torch.softmax(output, dim=1)[0]
            confidence, predicted = torch.max(probs, 0)

        category = CATEGORIES[predicted.item()]
        return category, float(confidence.item())
    except Exception as e:
        print(f"Image prediction error: {e}")
        return "Public Safety & Others", 0.3


def dual_predict(description, category_from_form, image_path=None):
    """Run both text and image models, return best prediction."""
    from ml.model import predict_full, predict_urgency, predict_resolution_time

    # Text model prediction
    text_result = predict_full(description, category_from_form)
    text_confidence = text_result['confidence']

    # Image model prediction (if image exists)
    if image_path and os.path.exists(image_path):
        try:
            img_category, img_confidence = predict_from_image(image_path)

            # Use image if high confidence, else use text
            if img_confidence > 0.70:
                final_category = img_category
                method = "dual"
            else:
                final_category = category_from_form or text_result['category']
                method = "text"

            final_confidence = max(text_confidence, img_confidence)
        except Exception:
            final_category = category_from_form or text_result['category']
            method = "text"
            final_confidence = text_confidence
    else:
        final_category = category_from_form or text_result['category']
        method = "text"
        final_confidence = text_confidence

    urgency, urg_conf = predict_urgency(description, final_category)
    resolution = predict_resolution_time(description, final_category, urgency)

    return {
        'category': final_category,
        'urgency': urgency,
        'confidence': final_confidence,
        'resolution_time': resolution,
        'method': method
    }
