import os
import random
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk

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

def select_winner(left_win):
    global image1, image2
    if left_win:
        elo_ratings[image1], elo_ratings[image2] = update_elo_rank(elo_ratings[image1], elo_ratings[image2])
    else:
        elo_ratings[image2], elo_ratings[image1] = update_elo_rank(elo_ratings[image2], elo_ratings[image1])
    show_next_images()

def show_next_images():
    global image1, image2
    image1, image2 = random.sample(images, 2)
    update_images(image1, image2)

def update_images(img1, img2):
    global image_width, image_height
    actual_width = max(image_width, 100)  # Ensure the width is at least 100
    actual_height = max(image_height, 100) # Ensure the height is at least 100
    left_img = Image.open(img1)
    right_img = Image.open(img2)
    left_img.thumbnail((actual_width, actual_height))
    right_img.thumbnail((actual_width, actual_height))
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

def on_resize(event):
    global image_width, image_height
    image_width = max(event.width // 2 - 20, 100) # Ensure the width is at least 100
    image_height = max(event.height - 20, 100)    # Ensure the height is at least 100
    update_images(image1, image2)

def quit_program():
    root.quit()
    for image, rating in sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True):
        print(f'{image}: {rating}')

folder_path = filedialog.askdirectory(title='Select a folder containing images')
images = get_images_from_folder(folder_path)
elo_ratings = {image: 1200 for image in images}
image1, image2 = None, None
image_width, image_height = 400, 400

root = tk.Tk()
root.title('Image Ranking')
root.configure(bg='black')
root.attributes('-fullscreen', True)  # Set the window to fullscreen
root.resizable(False, False)  # Prevent resizing
left_label = tk.Label(root, bg='black')
left_label.pack(side=tk.LEFT, padx=10, pady=10)
right_label = tk.Label(root, bg='black')
right_label.pack(side=tk.RIGHT, padx=10, pady=10)
button_frame = tk.Frame(root, bg='black')
button_frame.pack(side=tk.BOTTOM, pady=10)
left_button = tk.Button(button_frame, text="Left", command=lambda: select_winner(True), bg='gray', fg='white')
left_button.pack(side=tk.LEFT, padx=5)
right_button = tk.Button(button_frame, text="Right", command=lambda: select_winner(False), bg='gray', fg='white')
right_button.pack(side=tk.LEFT, padx=5)
quit_button = tk.Button(button_frame, text="Quit", command=quit_program, bg='gray', fg='white')
quit_button.pack(side=tk.LEFT, padx=5)

root.bind('<Left>', on_key)
root.bind('<Right>', on_key)
root.bind('<Escape>', on_key)
root.bind('<Configure>', on_resize)

show_next_images()
root.mainloop()
