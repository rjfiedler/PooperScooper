"""
Poop Detector - TensorFlow Lite object detection
Uses YOLOv8 model converted to TFLite for efficient edge inference
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
from loguru import logger

try:
    import tflite_runtime.interpreter as tflite
    TFLITE_AVAILABLE = True
except ImportError:
    try:
        import tensorflow.lite as tflite
        TFLITE_AVAILABLE = True
    except ImportError:
        logger.warning("TFLite not available - detection will be simulated")
        TFLITE_AVAILABLE = False


@dataclass
class Detection:
    """Object detection result"""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    center: Tuple[int, int]  # (x, y)


class PoopDetector:
    """
    TensorFlow Lite-based object detector for dog waste

    Loads a YOLOv8n model converted to TFLite and runs inference
    """

    def __init__(self, config: dict, simulate: bool = False):
        """
        Initialize detector

        Args:
            config: Vision configuration dictionary
            simulate: If True, generate fake detections for testing
        """
        self.config = config
        self.simulate = simulate or not TFLITE_AVAILABLE

        self.model_path = config['vision']['model_path']
        self.confidence_threshold = config['vision']['confidence_threshold']
        self.nms_threshold = config['vision']['nms_threshold']
        self.multi_frame_verification = config['vision']['multi_frame_verification']
        self.min_size = config['vision']['min_object_size']
        self.max_size = config['vision']['max_object_size']

        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.input_shape = None

        # Detection history for multi-frame verification
        self.detection_history = []

        # Class names (customize based on your trained model)
        self.class_names = {0: 'poop'}

        if not self.simulate:
            self._load_model()
        else:
            logger.info("Detector initialized in simulation mode")
            self.input_shape = (1, 416, 416, 3)

    def _load_model(self) -> None:
        """Load TFLite model"""
        try:
            # Load TFLite model
            self.interpreter = tflite.Interpreter(model_path=self.model_path)
            self.interpreter.allocate_tensors()

            # Get input/output details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()

            self.input_shape = self.input_details[0]['shape']

            logger.info(f"Model loaded: {self.model_path}")
            logger.info(f"Input shape: {self.input_shape}")
            logger.info(f"Output tensors: {len(self.output_details)}")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            logger.warning("Falling back to simulation mode")
            self.simulate = True

    def detect(self, image: np.ndarray) -> List[Detection]:
        """
        Run object detection on image

        Args:
            image: RGB image as numpy array (H, W, 3)

        Returns:
            List of Detection objects
        """
        if self.simulate:
            return self._simulate_detection(image)

        try:
            # Preprocess image
            input_data = self._preprocess(image)

            # Run inference
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            self.interpreter.invoke()

            # Get outputs
            # Note: Output format depends on YOLOv8 export settings
            # Typical format: [boxes, scores, class_ids]
            boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
            scores = self.interpreter.get_tensor(self.output_details[1]['index'])[0]
            class_ids = self.interpreter.get_tensor(self.output_details[2]['index'])[0]

            # Post-process detections
            detections = self._postprocess(boxes, scores, class_ids, image.shape)

            return detections

        except Exception as e:
            logger.error(f"Detection failed: {e}")
            return []

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for model input

        Args:
            image: Original RGB image

        Returns:
            Preprocessed image tensor
        """
        import cv2

        # Get target size from model
        target_h, target_w = self.input_shape[1:3]

        # Resize
        resized = cv2.resize(image, (target_w, target_h))

        # Normalize to [0, 1]
        normalized = resized.astype(np.float32) / 255.0

        # Add batch dimension
        input_data = np.expand_dims(normalized, axis=0)

        return input_data

    def _postprocess(
        self,
        boxes: np.ndarray,
        scores: np.ndarray,
        class_ids: np.ndarray,
        image_shape: Tuple[int, int, int]
    ) -> List[Detection]:
        """
        Post-process model outputs

        Args:
            boxes: Bounding boxes (N, 4) in format [x1, y1, x2, y2]
            scores: Confidence scores (N,)
            class_ids: Class IDs (N,)
            image_shape: Original image shape

        Returns:
            Filtered detections
        """
        detections = []
        h, w = image_shape[:2]

        for i in range(len(scores)):
            score = scores[i]

            # Filter by confidence
            if score < self.confidence_threshold:
                continue

            # Get box coordinates
            x1, y1, x2, y2 = boxes[i]

            # Scale to original image size
            x1 = int(x1 * w)
            y1 = int(y1 * h)
            x2 = int(x2 * w)
            y2 = int(y2 * h)

            # Filter by size
            box_area = (x2 - x1) * (y2 - y1)
            if box_area < self.min_size or box_area > self.max_size:
                continue

            # Calculate center
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            # Create detection
            class_id = int(class_ids[i])
            class_name = self.class_names.get(class_id, f"class_{class_id}")

            detection = Detection(
                class_id=class_id,
                class_name=class_name,
                confidence=float(score),
                bbox=(x1, y1, x2, y2),
                center=(center_x, center_y)
            )

            detections.append(detection)

        # Apply NMS (Non-Maximum Suppression)
        detections = self._apply_nms(detections)

        return detections

    def _apply_nms(self, detections: List[Detection]) -> List[Detection]:
        """
        Apply non-maximum suppression to remove overlapping boxes

        Args:
            detections: List of detections

        Returns:
            Filtered detections
        """
        if len(detections) == 0:
            return []

        # Sort by confidence
        detections = sorted(detections, key=lambda d: d.confidence, reverse=True)

        # Apply NMS
        keep = []
        while len(detections) > 0:
            best = detections.pop(0)
            keep.append(best)

            # Remove overlapping boxes
            detections = [
                d for d in detections
                if self._calculate_iou(best.bbox, d.bbox) < self.nms_threshold
            ]

        return keep

    def _calculate_iou(self, box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
        """Calculate Intersection over Union"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2

        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)

        if x2_i < x1_i or y2_i < y1_i:
            return 0.0

        intersection = (x2_i - x1_i) * (y2_i - y1_i)

        # Calculate union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def _simulate_detection(self, image: np.ndarray) -> List[Detection]:
        """
        Generate simulated detections for testing

        Args:
            image: Input image

        Returns:
            Fake detections
        """
        h, w = image.shape[:2]

        # Randomly generate 0-2 detections
        num_detections = np.random.choice([0, 0, 0, 1, 1, 2])  # Bias toward 0-1 detections

        detections = []
        for i in range(num_detections):
            # Random position
            center_x = np.random.randint(w // 4, 3 * w // 4)
            center_y = np.random.randint(h // 4, 3 * h // 4)

            # Random size
            size = np.random.randint(30, 80)
            x1 = max(0, center_x - size // 2)
            y1 = max(0, center_y - size // 2)
            x2 = min(w, center_x + size // 2)
            y2 = min(h, center_y + size // 2)

            # Random confidence
            confidence = np.random.uniform(0.7, 0.95)

            detection = Detection(
                class_id=0,
                class_name='poop',
                confidence=confidence,
                bbox=(x1, y1, x2, y2),
                center=(center_x, center_y)
            )

            detections.append(detection)

        return detections

    def verify_multi_frame(self, current_detections: List[Detection]) -> List[Detection]:
        """
        Verify detections across multiple frames

        Args:
            current_detections: Detections from current frame

        Returns:
            Verified detections that appear in N consecutive frames
        """
        self.detection_history.append(current_detections)

        # Keep only recent frames
        if len(self.detection_history) > self.multi_frame_verification:
            self.detection_history.pop(0)

        # Need minimum frames for verification
        if len(self.detection_history) < self.multi_frame_verification:
            return []

        # Find detections that appear in all frames
        verified = []

        for detection in current_detections:
            # Check if similar detection exists in all previous frames
            is_consistent = True

            for past_frame in self.detection_history[:-1]:
                has_match = any(
                    self._is_similar_detection(detection, past_det)
                    for past_det in past_frame
                )

                if not has_match:
                    is_consistent = False
                    break

            if is_consistent:
                verified.append(detection)

        return verified

    def _is_similar_detection(self, det1: Detection, det2: Detection) -> bool:
        """
        Check if two detections are likely the same object

        Args:
            det1, det2: Detections to compare

        Returns:
            True if detections are similar
        """
        # Check center distance
        center_dist = np.sqrt(
            (det1.center[0] - det2.center[0])**2 +
            (det1.center[1] - det2.center[1])**2
        )

        # Similar if centers are within 50 pixels
        return center_dist < 50


if __name__ == "__main__":
    """Test poop detector"""
    import yaml

    # Load config
    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    # Test detector
    detector = PoopDetector(config, simulate=True)

    logger.info("Testing detector...")

    # Create test image
    test_image = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)

    # Run detection
    detections = detector.detect(test_image)

    logger.info(f"Found {len(detections)} detections:")
    for det in detections:
        logger.info(f"  {det.class_name}: {det.confidence:.2f} at {det.center}")

    logger.info("Test complete")
