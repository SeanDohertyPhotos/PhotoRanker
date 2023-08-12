import os
import json
import tkinter as tk
from PIL import Image, ImageTk

RATINGS_FILE = "elo_ratings.json"
REFRESH_INTERVAL = 1000  # Refresh interval in milliseconds (1 second)
IMAGE_WIDTH = 200
IMAGE_HEIGHT = 150

def load_ratings():
    if os.path.exists(RATINGS_FILE):
        with open(RATINGS_FILE, 'r') as file:
            return json.load(file)
    return {}

def resize_image(img, width, height):
    img_ratio = img.width / img.height
    target_ratio = width / height
    if img_ratio > target_ratio:
        new_width = width
        new_height = int(width / img_ratio)
    else:
        new_height = height
        new_width = int(height * img_ratio)
    return img.resize((new_width, new_height), Image.LANCZOS)

def update_rankings():
    for widget in rankings_frame.winfo_children():
        widget.destroy()
    elo_ratings = load_ratings()
    sorted_ratings = sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True)
    for filename, rating in sorted_ratings:
        img_path = [img for img in images if os.path.basename(img) == filename][0]
        img = Image.open(img_path)
        img = resize_image(img, IMAGE_WIDTH, IMAGE_HEIGHT)
        photo = ImageTk.PhotoImage(img)
        image_label = tk.Label(rankings_frame, image=photo)
        image_label.image = photo
        image_label.pack()
        tk.Label(rankings_frame, text=f'Rating: {rating}').pack()
    root.after(REFRESH_INTERVAL, update_rankings)

def get_images_from_folder(folder_path):
    images = []
    for subdir, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(('jpg', 'png', 'jpeg')):
                images.append(os.path.join(subdir, file))
    return images

folder_path = input('Enter the path to the folder containing images: ')
images = get_images_from_folder(folder_path)

root = tk.Tk()
root.title('Live Image Rankings')
root.geometry('300x600')

scrollbar = tk.Scrollbar(root)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

rankings_frame = tk.Frame(root)
rankings_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

canvas = tk.Canvas(rankings_frame, yscrollcommand=scrollbar.set)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

scrollbar.config(command=canvas.yview)

canvas_frame = tk.Frame(canvas)
canvas.create_window((0, 0), window=canvas_frame, anchor=tk.NW)

root.bind("<Configure>", lambda e: canvas.config(scrollregion=canvas.bbox(tk.ALL)))

update_rankings()
root.mainloop()
