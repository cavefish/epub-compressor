import sys
import tkinter as tk
from tkinter import filedialog as tkfd

import ebooklib
import argparse
import io
import logging
import os
from ebooklib import epub
from PIL import Image


class CompressionGUI(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)

        self.title("epub-compressor")
        self.geometry("800x300")

        file_input_label = tk.Label(self, text="Input File")
        file_input_label.grid(row=0, column=0)
        self.file_input_text = tk.Entry(self, width=100)
        self.file_input_text.grid(row=0, column=1, columnspan=4)
        file_input_button = tk.Button(self, text="Find file", command=self.on_file_input_button)
        file_input_button.grid(row=0, column=5)

        file_output_label = tk.Label(self, text="Output File")
        file_output_label.grid(row=1, column=0)
        self.file_output_text = tk.Entry(self, width=100)
        self.file_output_text.grid(row=1, column=1, columnspan=4)
        file_output_button = tk.Button(self, text="Find file", command=self.on_file_output_button)
        file_output_button.grid(row=1, column=5)

        self.quality_selector = tk.Scale(self, from_=0, to=100, orient=tk.HORIZONTAL, label="Quality")
        self.quality_selector.set(75)
        self.quality_selector.grid(row=2, column=0, columnspan=2, sticky="ew")

        self.compression_selector = tk.Scale(self, from_=0, to=9, orient=tk.HORIZONTAL, label="Compression Level")
        self.compression_selector.set(6)
        self.compression_selector.grid(row=2, column=2, columnspan=2, sticky="ew")

        process_button = tk.Button(self, text="Compress", command=self.on_process_button_clicked)
        process_button.grid(row=2, column=4, columnspan=2, sticky="ew")

        self.console_entry = tk.Label(self)
        self.console_entry.grid(row=3, column=0, columnspan=6, rowspan=2)

    def on_file_input_button(self):
        result = tkfd.askopenfilename(
            filetypes=[("ePub", "*.epub")],
            title="Select file",
        )

        if len(result) == 0:
            return

        self.file_input_text.delete(0, "end")
        self.file_input_text.insert(0, result)

        last_dot = result.rindex(".")
        output_filename = result[:last_dot] + " (Compressed).epub"
        self.file_output_text.delete(0, "end")
        self.file_output_text.insert(0, output_filename)

        self.console_entry.configure(text="Input file selected")

    def on_file_output_button(self):
        result = tkfd.asksaveasfilename(
            filetypes=[("ePub", "*.epub")],
            title="Select file",
        )

        if len(result) == 0:
            return

        self.file_output_text.delete(0, "end")
        self.file_output_text.insert(0, result)

        self.console_entry.configure(text="Output file selected")

    def on_process_button_clicked(self):
        self.console_entry.configure(text="Processing ...")
        result = compress_epub(self.file_input_text.get(), self.file_output_text.get(), self.quality_selector.get(), self.compression_selector.get())
        self.console_entry.configure(text=result)


def compress_image(image_original_bytes, quality=75):
    image_original_bytes = io.BytesIO(image_original_bytes)
    image_original = Image.open(image_original_bytes)
    original_size = len(image_original_bytes.getvalue())
    
    try: 
        image_compressed_bytes = io.BytesIO()
        image_original.save(image_compressed_bytes, quality=quality, optimize=True, format="JPEG")

        compressed_size = len(image_compressed_bytes.getvalue())
        if compressed_size >= original_size:
            image_compressed_bytes = image_original_bytes
            compressed_size = len(image_original_bytes.getvalue())

        logging_text = "Compressed. BEFORE: {:8s}  AFTER: {:8s}  COMPRESSION: {:.2f}%"
        logging.info(logging_text.format(get_size_format(original_size), get_size_format(compressed_size), (original_size - compressed_size)/original_size*100))
    except Exception as e:
        logging.info("Unable to compress")
        image_compressed_bytes = image_original_bytes
        compressed_size = len(image_original_bytes.getvalue())

    return image_compressed_bytes.getvalue(), compressed_size, original_size


def get_size_format(b, factor=1024, suffix="B"):
    """
    Scale bytes to its proper byte format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"


def compress_epub(input_path, output_path, quality, compressionlevel=6):
    epub_original_size = os.stat(input_path).st_size
    logging.info("Compressing {} (original size: {}) with {}% image quality and a compression level of {}. Output path: {}".format(input_path, get_size_format(epub_original_size), quality, compressionlevel, output_path))
    book = epub.read_epub(input_path)
    for image in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        logging.info("Compressing image {}".format(image.file_name))
        image_compressed, compressed_size, original_size = compress_image(image.get_content(), quality=quality)
        image.set_content(image_compressed)
    
    epub.write_epub(output_path, book, {"compressionlevel": compressionlevel})
    epub_new_size = os.stat(output_path).st_size
    result = "Finished! New size is {} (original size: {}). Compression: {:.2f}%".format(
        get_size_format(epub_new_size), get_size_format(epub_original_size),
        (epub_original_size - epub_new_size) / epub_original_size * 100)
    logging.info(result)
    return result

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', encoding='utf-8', level=logging.INFO)
    if len(sys.argv) == 1:
        logging.info("Running GUI")
        window = CompressionGUI()
        window.mainloop()
        logging.info("Exiting GUI")
        exit(0)

    logging.info("Running CLI")

    parser = argparse.ArgumentParser(description="Compress an EPUB file by compressing its internal images")
    parser.add_argument("input", help="Path to input epub")
    parser.add_argument("-o", "--output", default="./compressed.epub", help="Path to output epub (defaults to ./compressed.epub)")
    parser.add_argument("-q", "--quality", default=75, type=int, help="Quality of compressed images. 100 best quality and more size, 1 worst quality and less size (defaults to 75)")
    parser.add_argument("-c", "--compressionlevel", default=6, type=int, help="Compression level. 0 no compression and fastest, 9 best compression amd slowest (defaults to 6)")
    args = parser.parse_args()

    print(args)
    compress_epub(args.input, args.output, args.quality, args.compressionlevel)

    logging.info("Exiting CLI")
    exit(0)
