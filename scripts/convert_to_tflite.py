"""
Convert YOLOv8 PyTorch model to TensorFlow Lite
For deployment on Raspberry Pi
"""

import argparse
from pathlib import Path
from ultralytics import YOLO
from loguru import logger


def convert_to_tflite(
    model_path: str,
    output_path: str,
    img_size: int = 416,
    int8: bool = True
):
    """
    Convert YOLOv8 model to TensorFlow Lite

    Args:
        model_path: Path to .pt model file
        output_path: Path to save .tflite file
        img_size: Input image size
        int8: Use INT8 quantization for smaller/faster model
    """
    logger.info(f"Converting {model_path} to TensorFlow Lite")
    logger.info(f"INT8 quantization: {int8}")

    # Load model
    model = YOLO(model_path)

    # Export to TensorFlow Lite
    model.export(
        format='tflite',
        imgsz=img_size,
        int8=int8,  # INT8 quantization for speed
        optimize=True,
    )

    # The export creates a file with _saved_model/model_float32.tflite or similar
    # Move to desired location
    exported_dir = Path(model_path).parent
    tflite_files = list(exported_dir.glob("*_saved_model/*.tflite"))

    if tflite_files:
        tflite_file = tflite_files[0]
        logger.info(f"Found exported TFLite model: {tflite_file}")

        # Copy to output location
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        import shutil
        shutil.copy(tflite_file, output_path)

        logger.info(f"TFLite model saved to: {output_path}")
    else:
        logger.error("Could not find exported TFLite model")


def main():
    parser = argparse.ArgumentParser(description="Convert YOLOv8 to TensorFlow Lite")
    parser.add_argument('--model', type=str, required=True, help='Path to .pt model file')
    parser.add_argument('--output', type=str, default='models/poop_detector.tflite', help='Output path for .tflite')
    parser.add_argument('--img-size', type=int, default=416, help='Input image size')
    parser.add_argument('--no-int8', action='store_true', help='Disable INT8 quantization')

    args = parser.parse_args()

    convert_to_tflite(
        model_path=args.model,
        output_path=args.output,
        img_size=args.img_size,
        int8=not args.no_int8
    )


if __name__ == "__main__":
    main()
