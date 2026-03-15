import fitz
import os

def extract_content_from_pdf(pdf_path, output_dir="extracted_content"):
    """
    Extracts all text and images from a PDF and saves them to a directory.

    Args:
        pdf_path (str): The file path to the PDF document.
        output_dir (str): The directory to save the extracted images.

    Returns:W
        tuple: (all_text, extracted_image_paths)
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    all_text = ""
    extracted_image_paths = []

    try:
        # Open the PDF file
        doc = fitz.open(pdf_path)
        print(f"[INFO] Opened PDF: {pdf_path} with {len(doc)} pages")

        for page_num, page in enumerate(doc, start=1):
            # --- Text Extraction ---
            page_text = page.get_text()
            all_text += page_text + "\n"

            # --- Image Extraction ---
            image_list = page.get_images(full=True)
            if image_list:
                print(f"[INFO] Page {page_num} has {len(image_list)} images")
            else:
                continue

            for img_index, img_info in enumerate(image_list, start=1):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    image_filename = f"page_{page_num}_image_{img_index}.{image_ext}"
                    image_path = os.path.join(output_dir, image_filename)

                    with open(image_path, "wb") as img_file:
                        img_file.write(image_bytes)
                    extracted_image_paths.append(image_path)
                    print(f"[+] Saved image: {image_path}")

                except Exception as e:
                    print(f"[WARNING] Skipping image {img_index} on page {page_num}: {e}")

        doc.close()

    except FileNotFoundError:
        print(f"[ERROR] File not found: {pdf_path}")
        return None, None
    except Exception as e:
        print(f"[ERROR] Failed to process PDF: {e}")
        return None, None

    return all_text.strip(), extracted_image_paths



if __name__ == "__main__":
    # # --- Example Usage ---
    pdf_document_path = "certificate_4.pdf"
    text_content, image_paths = extract_content_from_pdf(pdf_document_path)

    if text_content:
        print("\n--- Extracted Text ---")
        print(text_content[:1000], "..." if len(text_content) > 1000 else "")

        print("\n--- Extracted Images Paths ---")
        for path in image_paths:
            print(path)
