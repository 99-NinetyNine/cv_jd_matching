import os
import fitz  # PyMuPDF
from PIL import Image
import io

def prepare_yolo_dataset(pdf_dir: str, output_dir: str):
    """
    Convert PDFs to images for YOLO training.
    Creates 'images/train' and 'images/val' structure.
    """
    images_dir = os.path.join(output_dir, "images")
    train_dir = os.path.join(images_dir, "train")
    val_dir = os.path.join(images_dir, "val")
    
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(val_dir, exist_ok=True)
    
    # Also create labels dirs
    labels_dir = os.path.join(output_dir, "labels")
    os.makedirs(os.path.join(labels_dir, "train"), exist_ok=True)
    os.makedirs(os.path.join(labels_dir, "val"), exist_ok=True)
    
    files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
    
    # Simple split 80/20
    split_idx = int(len(files) * 0.8)
    train_files = files[:split_idx]
    val_files = files[split_idx:]
    
    def process_files(file_list, target_dir):
        for filename in file_list:
            pdf_path = os.path.join(pdf_dir, filename)
            try:
                doc = fitz.open(pdf_path)
                for i, page in enumerate(doc):
                    pix = page.get_pixmap(dpi=200)
                    img_data = pix.tobytes("png")
                    
                    # Save image
                    base_name = os.path.splitext(filename)[0]
                    img_name = f"{base_name}_page{i}.jpg"
                    img_path = os.path.join(target_dir, img_name)
                    
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                        
                    print(f"Saved {img_path}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")

    print("Processing training set...")
    process_files(train_files, train_dir)
    
    print("Processing validation set...")
    process_files(val_files, val_dir)
    
    print("Dataset preparation complete. Images saved.")
    print("NOTE: You still need to annotate these images (create .txt files in labels/)")

if __name__ == "__main__":
    # Example usage
    # prepare_yolo_dataset("data/raw_pdfs", "data/yolo_dataset")
    pass
