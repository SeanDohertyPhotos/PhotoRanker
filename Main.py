import os
import random
import json
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk

RATINGS_FILE = "elo_ratings.json"
TOP_RANK_COUNT = 10
unrated_label = None


def get_images_from_folder(folder_path):
    images = []
    for subdir, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(('jpg', 'png', 'jpeg')):
                images.append(os.path.join(subdir, file))
    return images

def update_elo_rank(winner_elo, loser_elo):
    K = 32
    expected_winner = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    expected_loser = 1 / (1 + 10 ** ((winner_elo - loser_elo) / 400))
    winner_elo += K * (1 - expected_winner)
    loser_elo += K * (0 - expected_loser)
    return winner_elo, loser_elo
    save_ratings()

def select_winner(left_win):
    global image1, image2
    winner = image1 if left_win else image2
    loser = image2 if left_win else image1
    filename_winner = os.path.basename(winner)
    filename_loser = os.path.basename(loser)
    elo_ratings[filename_winner]['rating'], elo_ratings[filename_loser]['rating'] = update_elo_rank(elo_ratings[filename_winner]['rating'], elo_ratings[filename_loser]['rating'])
    show_next_images()

def show_next_images():
    global image1, image2
    # Sort the images based on their rating, and select two images with a bias towards higher ratings
    weighted_images = sorted(images, key=lambda img: elo_ratings[os.path.basename(img)]['rating'], reverse=True)
    image1 = random.choices(weighted_images, weights=[i + 1 for i in range(len(weighted_images))], k=1)[0]
    image2 = random.choice([img for img in weighted_images if img != image1])
    update_images(image1, image2)
    
    # Count the number of unrated images (those with the default rating)
    unrated_count = sum(1 for details in elo_ratings.values() if details['rating'] == 1200)
    unrated_label.config(text=f"Unrated Images: {unrated_count}")  # Update the unrated_label with the count



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

def update_images(img1, img2):
    left_img = Image.open(img1)
    right_img = Image.open(img2)
    left_img = resize_image(left_img, image_width, image_height)
    right_img = resize_image(right_img, image_width, image_height)
    left_photo = ImageTk.PhotoImage(left_img)
    right_photo = ImageTk.PhotoImage(right_img)
    left_label.config(image=left_photo)
    left_label.image = left_photo
    right_label.config(image=right_photo)
    right_label.image = right_photo

def on_key(event):
    if event.keysym == 'Left':
        select_winner(True)
    elif event.keysym == 'Right':
        select_winner(False)
    elif event.keysym == 'Escape':
        quit_program()

def save_ratings():
    with open(RATINGS_FILE, 'w') as file:
        json.dump(elo_ratings, file)

def load_ratings():
    if os.path.exists(RATINGS_FILE):
        with open(RATINGS_FILE, 'r') as file:
            loaded_ratings = json.load(file)
            # Normalize the loaded ratings
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
    
    # Create a canvas inside the top_rank_window
    canvas = tk.Canvas(top_rank_window)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # Add a scrollbar to the canvas
    scrollbar = tk.Scrollbar(top_rank_window, command=canvas.yview)
    scrollbar.pack(side=tk.LEFT, fill=tk.Y)
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Create a frame inside the canvas
    frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=frame, anchor='nw')

    for filename, details in sorted(elo_ratings.items(), key=lambda x: x[1]['rating'], reverse=True)[:TOP_RANK_COUNT]:
        img_path = details["path"]
        rating = round(details["rating"])  # Round the rating to the nearest integer
        if os.path.exists(img_path):  # Check if the image file exists
            img = Image.open(img_path)
            img = resize_image(img, image_width, image_height)
            photo = ImageTk.PhotoImage(img)
            image_label = tk.Label(frame, image=photo)
            image_label.image = photo
            image_label.pack()
            tk.Label(frame, text=f'Rating: {rating}').pack()  # Use the rounded rating
        else:
            tk.Label(frame, text=f'{filename} not found. Rating: {rating}').pack()  # Use the rounded rating
            
    # Update the scroll region to match the size of the frame
    frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))


def quit_program():
    save_ratings()
    root.quit()

folder_path = filedialog.askdirectory(title='Select a folder containing images')
images = get_images_from_folder(folder_path)
elo_ratings = load_ratings()
for image in images:
    filename = os.path.basename(image)
    existing_entry = elo_ratings.get(filename, {'rating': 1200})
    existing_rating = existing_entry if isinstance(existing_entry, (int, float)) else existing_entry.get('rating', 1200)
    elo_ratings[filename] = {'path': image, 'rating': existing_rating}
image1, image2 = None, None
image_width, image_height = 800, 600

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

unrated_label = tk.Label(root, text="Unrated Images:", bg='black', fg='white')
unrated_label.pack(side=tk.BOTTOM, pady=5)

root.bind('<Left>', on_key)
root.bind('<Right>', on_key)
root.bind('<Escape>', on_key)

show_next_images()
root.mainloop()
