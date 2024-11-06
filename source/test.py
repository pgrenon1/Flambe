import torch
from transformers import ViTForImageClassification, ViTImageProcessor
from PIL import Image as ImagePIL
from PIL import ImageDraw as ImageDrawPIL
from PIL import ImageFont as ImageFontPIL
import time

# Load the model and processor
model = ViTForImageClassification.from_pretrained("./vit-base-flambe")
processor = ViTImageProcessor.from_pretrained("google/vit-base-patch16-224-in21k")

def predict_and_label_image(image_path):
    # Load and preprocess the image
    image = ImagePIL.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt").to(model.device)
    
    # Measure inference time
    start_time = time.time()
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        predicted_class_idx = logits.argmax(-1).item()
        label = model.config.id2label[predicted_class_idx]
    inference_time = time.time() - start_time
    print(f"Inference time: {inference_time:.4f} seconds")
    
    # Add the label to the image
    draw = ImageDrawPIL.Draw(image)
    font = ImageFontPIL.truetype("arial.ttf", 20)
    bbox = draw.textbbox((0, 0), label, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Center text at the bottom of the image
    text_position = (image.width // 2 - text_width // 2, image.height - text_height - 10)
    draw.text(text_position, label, font=font, fill="white")
    
    # Display or save the labeled image
    image.show() 
    image.save(image_path)
    return image

predict_and_label_image("./data/split/forward/forward1_0002.jpg")