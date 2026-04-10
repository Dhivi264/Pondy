#!/usr/bin/env python3
"""
CLI script for face detection model training.

Usage:
    python train_face_model.py --source-dir data/recordings --epochs 50
    python train_face_model.py --source-dir data/recordings --epochs 50 --skip-collection
"""

import argparse
import os
import sys
import time

# Add the backend directory to sys.path so app imports work
sys.path.insert(0, os.path.dirname(__file__))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a YOLOv11-face detection model on CCTV footage."
    )
    parser.add_argument(
        "--source-dir",
        required=True,
        help="Directory containing raw CCTV footage or face images.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Number of training epochs (default: 50).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Training batch size (default: 16).",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Training device, e.g. 'cpu', 'cuda:0' (default: auto-detect).",
    )
    parser.add_argument(
        "--frame-interval",
        type=float,
        default=1.0,
        help="Seconds between sampled frames during collection (default: 1.0).",
    )
    parser.add_argument(
        "--skip-collection",
        action="store_true",
        help="Skip dataset collection and use an existing dataset directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from app.ai.training.pipeline import TrainingJobConfig, TrainingPipeline

    config = TrainingJobConfig(
        source_dir=args.source_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        device=args.device,
        frame_interval=args.frame_interval,
        skip_collection=args.skip_collection,
    )

    pipeline = TrainingPipeline()

    print(f"Starting training job...")
    print(f"  Source dir:      {args.source_dir}")
    print(f"  Epochs:          {args.epochs}")
    print(f"  Batch size:      {args.batch_size}")
    print(f"  Device:          {args.device or 'auto'}")
    print(f"  Frame interval:  {args.frame_interval}s")
    print(f"  Skip collection: {args.skip_collection}")
    print()

    start_time = time.time()
    job_id = pipeline.start_job(config)
    print(f"Job ID: {job_id}")
    print()

    # Poll until terminal state
    terminal_statuses = {"completed", "failed", "cancelled"}
    last_status = None
    last_epoch = None

    while True:
        job = pipeline.get_job(job_id)
        if job is None:
            print("Error: job not found.", file=sys.stderr)
            sys.exit(1)

        status = job.status
        epoch = job.current_epoch

        # Print progress update when something changes
        if status != last_status or epoch != last_epoch:
            if status == "training":
                print(f"Status: {status}, Epoch: {epoch}/{job.total_epochs}")
            else:
                print(f"Status: {status}")
            last_status = status
            last_epoch = epoch

        if status in terminal_statuses:
            break

        time.sleep(1)

    elapsed = time.time() - start_time

    if job.status == "completed":
        map50 = job.metrics.get("map50", job.metrics.get("mAP@0.5", "N/A"))

        # Determine ONNX path (prefer trained model, fall back to yolo_face)
        onnx_path = "models/face_detection_trained/face_embed.onnx"
        if not os.path.exists(onnx_path):
            onnx_path = "models/yolo_face/face_embed.onnx"

        print()
        print("=" * 50)
        print("Training completed successfully!")
        print(f"  Total time:    {elapsed:.1f}s")
        print(f"  Final mAP@0.5: {map50}")
        print(f"  ONNX model:    {onnx_path}")
        print("=" * 50)

    elif job.status == "failed":
        print(f"Training failed: {job.error}", file=sys.stderr)
        sys.exit(1)

    elif job.status == "cancelled":
        print("Training was cancelled.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
