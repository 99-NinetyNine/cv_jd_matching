from ultralytics import YOLO
import os

def train_yolo(data_yaml: str, epochs: int = 50, img_size: int = 640):
    """
    Train YOLOv8 model.
    """
    # Load a model
    model = YOLO("yolov8n.pt")  # load a pretrained model (recommended for training)

    # Train the model
    results = model.train(data=data_yaml, epochs=epochs, imgsz=img_size)
    
    print("Training complete.")
    print(f"Best model saved at: {results.save_dir}")

if __name__ == "__main__":
    # Example usage
    # train_yolo("data/yolo_dataset/data.yaml")
    pass
