import ebooklib
import argparse
import io
import logging
import os
from ebooklib import epub
from PIL import Image
from datetime import datetime



def compress_image(image_original_bytes, quality=75):
    image_original_bytes = io.BytesIO(image_original_bytes)
    image_original = Image.open(image_original_bytes)
    original_size = len(image_original_bytes.getvalue())
    
    try: 
        image_compressed_bytes = io.BytesIO()
        image_compressed = image_original.save(image_compressed_bytes, quality=quality, optimize=True, format="JPEG")

        compressed_size = len(image_compressed_bytes.getvalue())
        if compressed_size >= original_size:
            image_compressed = image_original
            image_compressed_bytes = image_original_bytes
            compressed_size = len(image_original_bytes.getvalue())

        logging_text = "Compressed. BEFORE: {:8s}  AFTER: {:8s}  COMPRESSION: {:.2f}%"
        logging.info(logging_text.format(get_size_format(original_size), get_size_format(compressed_size), (original_size - compressed_size)/original_size*100))
    except Exception as e:
        logging.info("Unable to compress")
        image_compressed = image_original
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
    logging.info("Finished! New size is {} (original size: {}). Compression: {:.2f}%".format(get_size_format(epub_new_size), get_size_format(epub_original_size), (epub_original_size - epub_new_size)/epub_original_size*100))



parser = argparse.ArgumentParser(description="Compress an EPUB file by compressing its internal images")
parser.add_argument("input", help="Path to input epub")
parser.add_argument("-o", "--output", default="./compressed.epub", help="Path to output epub (defaults to ./compressed.epub)")
parser.add_argument("-q", "--quality", default=75, type=int, help="Quality of compressed images. 100 best quality and more size, 1 worst quality and less size (defaults to 75)")
parser.add_argument("-c", "--compressionlevel", default=6, type=int, help="Compression level. 0 no compression and fastest, 9 best compression amd slowest (defaults to 6)")
args = parser.parse_args()

print(args)
logging.basicConfig(filename='epub-compressor_{:%Y-%m-%dT%H%M%S}.log'.format(datetime.now()), format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', encoding='utf-8', level=logging.INFO)
compress_epub(args.input, args.output, args.quality, args.compressionlevel)
