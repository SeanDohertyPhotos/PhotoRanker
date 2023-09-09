import os
import random
import json
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import rawpy
from queue import Queue
from threading import Thread

RATINGS_FILE = "elo_ratings.json"
TOP_RANK_COUNT = 10
unrated_label = None
Image.MAX_IMAGE_PIXELS = None  # To handle large images

def open_image(img_path):
    return Image.open(img_path) if not img_path.lower().endswith('.dng') else Image.fromarray(rawpy.imread(img_path).postprocess())

def get_images_from_folder(folder_path):
    return [os.path.join(subdir, file) for subdir, _, files in os.walk(folder_path) for file in files if file.lower().endswith(('jpg', 'png', 'jpeg', 'dng'))]

def update_elo_rank(winner_elo, loser_elo, K):
    expected_winner = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    winner_elo += K * (1 - expected_winner)
    loser_elo += K * (expected_winner - 1)
    return winner_elo, loser_elo

def get_unrated_count():
    return sum(1 for img in images if elo_ratings[os.path.basename(img)]['rating'] == 1200)

def select_winner(left_win):
    global image1, image2
    winner, loser = (image1, image2) if left_win else (image2, image1)
    filename_winner, filename_loser = os.path.basename(winner), os.path.basename(loser)

    elo_ratings[filename_winner]['compared'] += 1
    elo_ratings[filename_loser]['compared'] += 1

    winner_elo, loser_elo = elo_ratings[filename_winner]['rating'], elo_ratings[filename_loser]['rating']
    K = 32 if abs(winner_elo - loser_elo) < 100 else 16
    winner_elo, loser_elo = update_elo_rank(winner_elo, loser_elo, K)

    elo_ratings[filename_winner]['rating'] = winner_elo
    elo_ratings[filename_loser]['rating'] = loser_elo
    
    unrated_label.config(text=f"Unrated Images in Current Folder: {get_unrated_count()}")
    
    show_next_images()

def show_next_images():
    global image1, image2
    if not preloaded_images.empty():
        img1_path, img2_path, left_img, right_img = preloaded_images.get()
        image1, image2 = img1_path, img2_path
        left_photo, right_photo = ImageTk.PhotoImage(left_img), ImageTk.PhotoImage(right_img)
        left_label.config(image=left_photo)
        left_label.image = left_photo
        right_label.config(image=right_photo)
        right_label.image = right_photo
        return

    # If there are no preloaded images (though there should be), fall back to existing logic
    top_images = sorted([img for img in images if elo_ratings[os.path.basename(img)]['rating'] > 1200], 
                        key=lambda img: elo_ratings[os.path.basename(img)]['rating'], reverse=True)[:10]
    unrated_images = [img for img in images if elo_ratings[os.path.basename(img)]['rating'] == 1200]
    other_images = [img for img in images if img not in top_images and img not in unrated_images]

    choices = ["top", "unrated", "other"]
    image1_choice, image2_choice = random.choice(choices), random.choice(choices)

    if image1_choice == "top": image1 = random.choice(top_images)
    elif image1_choice == "unrated": image1 = random.choice(unrated_images) if unrated_images else random.choice(other_images)
    else: image1 = random.choice(other_images)

    if image2_choice == "top": image2 = random.choice([img for img in top_images if img != image1])
    elif image2_choice == "unrated": image2 = random.choice([img for img in unrated_images if img != image1]) if unrated_images else random.choice(other_images)
    else: image2 = random.choice([img for img in other_images if img != image1])

    if random.choice([True, False]): image1, image2 = image2, image1

    update_images(image1, image2)

def resize_image(img, width, height):
    img_ratio = img.width / img.height
    target_ratio = width / height
    new_width = width if img_ratio > target_ratio else int(height * img_ratio)
    new_height = int(width / img_ratio) if img_ratio > target_ratio else height
    return img.resize((new_width, new_height), Image.LANCZOS)

def update_images(img1, img2):
    left_img, right_img = open_and_resize_image(img1), open_and_resize_image(img2)
    left_photo, right_photo = ImageTk.PhotoImage(left_img), ImageTk.PhotoImage(right_img)
    left_label.config(image=left_photo)
    left_label.image = left_photo
    right_label.config(image=right_photo)
    right_label.image = right_photo

def on_key(event):
    if event.keysym == 'Left': select_winner(True)
    elif event.keysym == 'Right': select_winner(False)
    elif event.keysym == 'Escape': quit_program()

def save_ratings():
    with open(RATINGS_FILE, 'w') as file:
        json.dump(elo_ratings, file)

def load_ratings():
    if os.path.exists(RATINGS_FILE):
        with open(RATINGS_FILE, 'r') as file:
            loaded_ratings = json.load(file)
            for key, value in loaded_ratings.items():
                if isinstance(value, (int, float)):
                    loaded_ratings[key] = {'path': '', 'rating': value}
            return loaded_ratings
    return {}

def view_rankings():
    ranking_window = tk.Toplevel(root)
    ranking_window.title('Image Rankings')
    for image, details in sorted(elo_ratings.items(), key=lambda x: x[1]['rating'], reverse=True):
        tk.Label(ranking_window, text=f'{image} - {details["path"]}: {details["rating"]}').pack()

def view_top_ranked():
    top_rank_window = tk.Toplevel(root)
    top_rank_window.title('Top Ranked Images')
    canvas = tk.Canvas(top_rank_window)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar = tk.Scrollbar(top_rank_window, command=canvas.yview)
    scrollbar.pack(side=tk.LEFT, fill=tk.Y)
    canvas.configure(yscrollcommand=scrollbar.set)
    frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=frame, anchor='nw')
    for filename, details in sorted(elo_ratings.items(), key=lambda x: x[1]['rating'], reverse=True)[:TOP_RANK_COUNT]:
        img_path = details["path"]
        rating = round(details["rating"])
        if os.path.exists(img_path):
            img = open_and_resize_image(img_path)
            photo = ImageTk.PhotoImage(img)
            image_label = tk.Label(frame, image=photo)
            image_label.image = photo
            image_label.pack()
            tk.Label(frame, text=f'Rating: {rating}').pack()
        else:
            tk.Label(frame, text=f'{filename} not found. Rating: {rating}').pack()
    frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

def quit_program():
    save_ratings()
    root.quit()

def open_and_resize_image(img_path):
    img = open_image(img_path)
    return resize_image(img, image_width, image_height)

def get_next_images_for_preload():
    top_images = sorted([img for img in images if elo_ratings[os.path.basename(img)]['rating'] > 1200], 
                        key=lambda img: elo_ratings[os.path.basename(img)]['rating'], reverse=True)[:10]
    unrated_images = [img for img in images if elo_ratings[os.path.basename(img)]['rating'] == 1200]
    other_images = [img for img in images if img not in top_images and img not in unrated_images]

    choices = ["top", "unrated", "other"]
    image1_choice, image2_choice = random.choice(choices), random.choice(choices)

    if image1_choice == "top": img1 = random.choice(top_images)
    elif image1_choice == "unrated": img1 = random.choice(unrated_images) if unrated_images else random.choice(other_images)
    else: img1 = random.choice(other_images)

    if image2_choice == "top": img2 = random.choice([img for img in top_images if img != img1])
    elif image2_choice == "unrated": img2 = random.choice([img for img in unrated_images if img != img1]) if unrated_images else random.choice(other_images)
    else: img2 = random.choice([img for img in other_images if img != img1])

    return img1, img2

def preload_images():
    while True:
        img1, img2 = get_next_images_for_preload()
        left_img = open_and_resize_image(img1)
        right_img = open_and_resize_image(img2)
        preloaded_images.put((img1, img2, left_img, right_img))

folder_path = filedialog.askdirectory(title='Select a folder containing images')
images = get_images_from_folder(folder_path)
elo_ratings = load_ratings()
for image in images:
    filename = os.path.basename(image)
    existing_entry = elo_ratings.get(filename, {'rating': 1200, 'compared': 0})
    elo_ratings[filename] = {
        'path': image,
        'rating': existing_entry.get('rating', 1200),
        'compared': existing_entry.get('compared', 0)
    }

image_width, image_height = 800, 600
preloaded_images = Queue(maxsize=5)
Thread(target=preload_images, daemon=True).start()

root = tk.Tk()
root.title('Image Ranking')
root.configure(bg='black')
root.state('zoomed')

left_label = tk.Label(root, bg='black')
left_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
right_label = tk.Label(root, bg='black')
right_label.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
button_frame = tk.Frame(root, bg='black')
button_frame.pack(side=tk.BOTTOM, pady=10)
left_button = tk.Button(button_frame, text="Left", command=lambda: select_winner(True), bg='gray', fg='white')
left_button.pack(side=tk.LEFT, padx=5)
right_button = tk.Button(button_frame, text="Right", command=lambda: select_winner(False), bg='gray', fg='white')
right_button.pack(side=tk.LEFT, padx=5)
view_ranking_button = tk.Button(button_frame, text="View Rankings", command=view_rankings, bg='gray', fg='white')
view_ranking_button.pack(side=tk.LEFT, padx=5)
view_top_button = tk.Button(button_frame, text="View Top Ranked", command=view_top_ranked, bg='gray', fg='white')
view_top_button.pack(side=tk.LEFT, padx=5)
quit_button = tk.Button(button_frame, text="Quit", command=quit_program, bg='gray', fg='white')
quit_button.pack(side=tk.LEFT, padx=5)

unrated_label = tk.Label(root, text=f"Unrated Images in Current Folder: {get_unrated_count()}", bg='black', fg='white')
unrated_label.pack(side=tk.BOTTOM, pady=5)

root.bind('<Left>', on_key)
root.bind('<Right>', on_key)
root.bind('<Escape>', on_key)

show_next_images()
root.mainloop()
