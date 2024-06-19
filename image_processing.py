from collections import Counter
from PIL import Image
import sqlite3
import os

def resize_image(image_path, multiplier):
    image = Image.open(image_path)
    new_size = tuple([x * multiplier for x in image.size])
    resized_image = image.resize(new_size, Image.ANTIALIAS)
    resized_image_path = f'temp/resized_{os.path.basename(image_path)}'
    resized_image.save(resized_image_path)
    return resized_image_path

def get_top_colors(image_path, num_colors=8):
    try:
        image = Image.open(image_path)
        image = image.convert('RGB')
        image = image.quantize(colors=256).convert('RGB')
        
        pixels = list(image.getdata())
        pixel_counts = Counter(pixels)
        top_colors = pixel_counts.most_common(num_colors)
        
        colors = ['#{:02x}{:02x}{:02x}'.format(*color) for color, count in top_colors]
        return colors

    except Exception as e:
        print(f"Error getting top colors: {e}")

def process_image(image_path, multiplier):
    resized_image_path = resize_image(image_path, multiplier)
    colors = get_top_colors(image_path)

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO images (original_image_path, resized_image_path, colors)
        VALUES (?, ?, ?)
    ''', (image_path, resized_image_path, ','.join(colors)))
    conn.commit()
    conn.close()

    return resized_image_path, colors