import cv2
from transformers import ViTForImageClassification, ViTImageProcessor
from PIL import Image as ImagePIL
from PIL import ImageDraw as ImageDrawPIL
from PIL import ImageFont as ImageFontPIL
import numpy as np
import torch
from collections import Counter
from pythonosc import udp_client


# Load model and processor
model = ViTForImageClassification.from_pretrained("./vit-base-flambe")
processor = ViTImageProcessor.from_pretrained("google/vit-base-patch16-224-in21k")
# Set up OSC client to send data to Unreal Engine
client = udp_client.SimpleUDPClient("127.0.0.1", 8000)

# Video labeling function
def label_video(video_path, output_path, frame_count=50, min_occurrences_ratio=0.9):
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    last_labels = []  # List to store the last 'frame_count' labels

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Convert frame to RGB
        image = ImagePIL.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        inputs = processor(images=image, return_tensors="pt").to(model.device)
        
        # Predict label
        with torch.no_grad():
            outputs = model(**inputs)
            predicted_class_idx = outputs.logits.argmax(-1).item()
            label = model.config.id2label[predicted_class_idx]
        
        # Append the current label to the list
        last_labels.append(label)
        
        # Keep only the last 'frame_count' labels
        if len(last_labels) > frame_count:
            last_labels.pop(0)

        # Get the most common label in the last 'frame_count' frames
        label_counts = Counter(last_labels)
        most_common_label, count = label_counts.most_common(1)[0]
        
        # Only label frames if the most common label meets the minimum occurrence threshold
        if count / frame_count >= min_occurrences_ratio:
            # Draw textbox and label text
            draw = ImageDrawPIL.Draw(image)
            font = ImageFontPIL.truetype("arial.ttf", 20)
            bbox = draw.textbbox((0, 0), most_common_label, font=font)
            text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
            text_position = (image.width // 2 - text_width // 2, image.height - text_height - 10)
            
            # Draw a filled rectangle for the textbox background
            textbox_position = [
                text_position[0] - 5, text_position[1] - 5,
                text_position[0] + text_width + 5, text_position[1] + text_height + 5
            ]
            draw.rectangle(textbox_position, fill="black")
            draw.text(text_position, most_common_label, font=font, fill="white")

            # Print a message when a label is added
            # print(f"Label added: {most_common_label}")
            # Send a value to control movement
            client.send_message("/direction", {most_common_label})

        # Convert back to BGR and write to output video
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        out.write(frame)
        
        # Display the frame
        cv2.imshow('Labeled Video', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    out.release()
    cv2.destroyAllWindows()

# Usage
label_video("./data/raw/right_full.mp4", "labeled_output4.mp4", frame_count=50, min_occurrences_ratio=0.9)
