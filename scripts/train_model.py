"""
Train YOLOv8 model for poop detection
Uses Ultralytics YOLOv8 framework
"""

import argparse
from pathlib import Path
from ultralytics import YOLO
from loguru import logger


def train_model(
    data_yaml: str,
    epochs: int = 100,
    img_size: int = 416,
    batch_size: int = 16,
    model_size: str = 'n'
):
    """
    Train YOLOv8 model

    Args:
        data_yaml: Path to data.yaml file
        epochs: Number of training epochs
        img_size: Input image size
        batch_size: Batch size (reduce if OOM)
        model_size: Model size ('n', 's', 'm', 'l', 'x')
    """
    logger.info(f"Training YOLOv8{model_size} model")
    logger.info(f"Data: {data_yaml}")
    logger.info(f"Epochs: {epochs}, Image size: {img_size}, Batch: {batch_size}")

    # Load pre-trained YOLOv8 model
    model = YOLO(f'yolov8{model_size}.pt')

    # Train the model
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=img_size,
        batch=batch_size,
        device='cpu',  # Use 'cuda' if GPU available
        project='runs/detect',
        name='poop_detector',
        exist_ok=True,
        patience=50,  # Early stopping
        save=True,
        plots=True,
    )

    logger.info("Training complete!")
    logger.info(f"Model saved to: runs/detect/poop_detector/weights/best.pt")

    return results


def create_data_yaml(train_dir: str, val_dir: str, output_path: str):
    """
    Create data.yaml file for YOLO training

    Args:
        train_dir: Path to training images
        val_dir: Path to validation images
        output_path: Where to save data.yaml
    """
    data_yaml_content = f"""
# Poop Detection Dataset
path: {Path(train_dir).parent.absolute()}
train: {Path(train_dir).name}
val: {Path(val_dir).name}

# Classes
names:
  0: poop
"""

    with open(output_path, 'w') as f:
        f.write(data_yaml_content)

    logger.info(f"Created data.yaml at {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8 poop detector")
    parser.add_argument('--data', type=str, required=True, help='Path to data.yaml or training directory')
    parser.add_argument('--epochs', type=int, default=100, help='Number of epochs')
    parser.add_argument('--img-size', type=int, default=416, help='Image size')
    parser.add_argument('--batch', type=int, default=16, help='Batch size')
    parser.add_argument('--model-size', type=str, default='n', choices=['n', 's', 'm', 'l', 'x'], help='Model size')

    args = parser.parse_args()

    # Train model
    train_model(
        data_yaml=args.data,
        epochs=args.epochs,
        img_size=args.img_size,
        batch_size=args.batch,
        model_size=args.model_size
    )


if __name__ == "__main__":
    main()
