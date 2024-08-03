import os
import random
import json
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk, ImageEnhance
import rawpy
from queue import Queue
from threading import Thread
import inputs  # New import for Xbox controller support

RATINGS_FILE = "elo_ratings.json"
BLACKLIST_FILE = "blacklist.json"
TOP_RANK_COUNT = 10
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
    elo_ratings[filename_winner]['confidence'] = elo_ratings[filename_winner]['compared'] / float(len(images))
    elo_ratings[filename_loser]['confidence'] = elo_ratings[filename_loser]['compared'] / float(len(images))

    winner_elo, loser_elo = elo_ratings[filename_winner]['rating'], elo_ratings[filename_loser]['rating']
    K = 32 if abs(winner_elo - loser_elo) < 100 else 16
    winner_elo, loser_elo = update_elo_rank(winner_elo, loser_elo, K)

    elo_ratings[filename_winner]['rating'] = winner_elo
    elo_ratings[filename_loser]['rating'] = loser_elo
    
    update_progress()
    show_next_images()

def get_least_compared_images():
    return sorted([img for img in images if os.path.basename(img) not in blacklist], 
                  key=lambda img: elo_ratings[os.path.basename(img)]['compared'])

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
        update_image_info()
        return

    least_compared_images = get_least_compared_images()[:20]  # Grab the 20 least compared images
    if len(least_compared_images) < 2:
        print("Not enough images to compare. Please add more images or remove some from the blacklist.")
        return

    image1 = random.choice(least_compared_images)
    image2 = random.choice([img for img in least_compared_images if img != image1])

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
    update_image_info()

def update_image_info():
    left_info.config(text=f"{os.path.basename(image1)}\nRating: {elo_ratings[os.path.basename(image1)]['rating']:.2f}\nCompared: {elo_ratings[os.path.basename(image1)]['compared']}")
    right_info.config(text=f"{os.path.basename(image2)}\nRating: {elo_ratings[os.path.basename(image2)]['rating']:.2f}\nCompared: {elo_ratings[os.path.basename(image2)]['compared']}")

def on_key(event):
    if event.keysym == 'Left': select_winner(True)
    elif event.keysym == 'Right': select_winner(False)
    elif event.keysym == 'z': blacklist_and_replace_image(True)
    elif event.keysym == 'x': blacklist_and_replace_image(False)
    elif event.keysym == 'Escape': quit_program()

def blacklist_and_replace_image(is_left):
    global image1, image2
    image_to_blacklist = image1 if is_left else image2
    filename = os.path.basename(image_to_blacklist)
    if filename not in blacklist:
        blacklist.append(filename)
        print(f"Blacklisted: {filename}")
        save_blacklist()
    
    # Get a new image to replace the blacklisted one
    least_compared_images = get_least_compared_images()
    if not least_compared_images:
        print("No more images available to compare.")
        return
    
    new_image = random.choice([img for img in least_compared_images if img != image1 and img != image2])
    
    if is_left:
        image1 = new_image
        left_img = open_and_resize_image(image1)
        left_photo = ImageTk.PhotoImage(left_img)
        left_label.config(image=left_photo)
        left_label.image = left_photo
    else:
        image2 = new_image
        right_img = open_and_resize_image(image2)
        right_photo = ImageTk.PhotoImage(right_img)
        right_label.config(image=right_photo)
        right_label.image = right_photo
    
    update_image_info()

def save_ratings():
    with open(RATINGS_FILE, 'w') as file:
        json.dump(elo_ratings, file)

def save_blacklist():
    with open(BLACKLIST_FILE, 'w') as file:
        json.dump(blacklist, file)

def load_ratings():
    if os.path.exists(RATINGS_FILE):
        with open(RATINGS_FILE, 'r') as file:
            loaded_ratings = json.load(file)
            for key, value in loaded_ratings.items():
                if isinstance(value, (int, float)):
                    loaded_ratings[key] = {'path': '', 'rating': value, 'compared': 0, 'confidence': 0.0}
            return loaded_ratings
    return {}

def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, 'r') as file:
            return json.load(file)
    return []

def view_rankings():
    ranking_window = tk.Toplevel(root)
    ranking_window.title('Image Rankings')
    ranking_window.geometry('800x600')
    ranking_window.configure(bg='#2c2c2c')
    
    style = ttk.Style(ranking_window)
    style.theme_use('clam')
    style.configure("Treeview", background="#2c2c2c", foreground="white", fieldbackground="#2c2c2c")
    style.map('Treeview', background=[('selected', '#22559b')])
    
    tree = ttk.Treeview(ranking_window, columns=('Filename', 'Rating', 'Compared', 'Blacklisted'), show='headings')
    tree.heading('Filename', text='Filename')
    tree.heading('Rating', text='Rating')
    tree.heading('Compared', text='Compared')
    tree.heading('Blacklisted', text='Blacklisted')
    
    for image, details in sorted(elo_ratings.items(), key=lambda x: x[1]['rating'], reverse=True):
        tree.insert('', 'end', values=(image, f"{details['rating']:.2f}", details['compared'], 'Yes' if image in blacklist else 'No'))
    
    tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

def view_top_ranked():
    top_rank_window = tk.Toplevel(root)
    top_rank_window.title('Top Ranked Images')
    top_rank_window.state('zoomed')
    top_rank_window.configure(bg='#2c2c2c')
    
    canvas = tk.Canvas(top_rank_window, bg='#2c2c2c', highlightthickness=0)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar = ttk.Scrollbar(top_rank_window, orient=tk.VERTICAL, command=canvas.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.configure(yscrollcommand=scrollbar.set)
    frame = ttk.Frame(canvas, style='TFrame')
    canvas.create_window((0, 0), window=frame, anchor='nw')
    
    for filename, details in sorted(elo_ratings.items(), key=lambda x: x[1]['rating'], reverse=True)[:TOP_RANK_COUNT]:
        img_path = details["path"]
        rating = round(details["rating"], 2)
        if os.path.exists(img_path) and filename not in blacklist:
            img = open_and_resize_image(img_path, width=400, height=300)
            photo = ImageTk.PhotoImage(img)
            image_label = ttk.Label(frame, image=photo, style='TLabel')
            image_label.image = photo
            image_label.pack(pady=10)
            ttk.Label(frame, text=f'{filename}\nRating: {rating}', style='TLabel').pack()
        elif filename in blacklist:
            ttk.Label(frame, text=f'{filename} is blacklisted. Rating: {rating}', style='TLabel').pack()
        else:
            ttk.Label(frame, text=f'{filename} not found. Rating: {rating}', style='TLabel').pack()
    
    frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

def quit_program():
    save_ratings()
    save_blacklist()
    root.quit()

def open_and_resize_image(img_path, width=None, height=None):
    img = open_image(img_path)
    if width and height:
        return resize_image(img, width, height)
    return resize_image(img, image_width, image_height)

def get_next_images_for_preload():
    least_compared = get_least_compared_images()[:20]
    if len(least_compared) < 2:
        return None, None
    img1, img2 = random.sample(least_compared, 2)
    return img1, img2

def preload_images():
    while True:
        img1, img2 = get_next_images_for_preload()
        if img1 is None or img2 is None:
            continue
        left_img = open_and_resize_image(img1)
        right_img = open_and_resize_image(img2)
        preloaded_images.put((img1, img2, left_img, right_img))

def update_progress():
    unrated_count = get_unrated_count()
    total_count = len(images)
    progress = (total_count - unrated_count) / total_count * 100
    progress_bar['value'] = progress

def create_styled_button(parent, text, command):
    return tk.Button(parent, text=text, command=command, bg="#4CAF50", fg="white", 
                     activebackground="#45a049", activeforeground="white", 
                     relief=tk.FLAT, padx=20, pady=10, font=("Helvetica", 12))

# New function to handle Xbox controller input
def handle_controller_input():
    while True:
        try:
            events = inputs.get_gamepad()
            for event in events:
                if event.code == 'BTN_SOUTH' and event.state == 1:  # A button
                    root.event_generate('<<ControllerLeft>>')
                elif event.code == 'BTN_EAST' and event.state == 1:  # B button
                    root.event_generate('<<ControllerRight>>')
                elif event.code == 'BTN_WEST' and event.state == 1:  # X button
                    root.event_generate('<<ControllerBlacklistLeft>>')
                elif event.code == 'BTN_NORTH' and event.state == 1:  # Y button
                    root.event_generate('<<ControllerBlacklistRight>>')
        except inputs.UnpluggedError:
            # No gamepad found, sleep for a while before trying again
            import time
            time.sleep(1)
        except Exception as e:
            print(f"Unexpected error in controller input: {e}")
            # Sleep to avoid tight loop if persistent error
            import time
            time.sleep(1)

# Main program
folder_path = filedialog.askdirectory(title='Select a folder containing images')
images = get_images_from_folder(folder_path)
elo_ratings = load_ratings()
blacklist = load_blacklist()

for image in images:
    filename = os.path.basename(image)
    existing_entry = elo_ratings.get(filename, {'rating': 1200, 'compared': 0, 'confidence': 0.0})
    elo_ratings[filename] = {
        'path': image,
        'rating': existing_entry.get('rating', 1200),
        'compared': existing_entry.get('compared', 0),
        'confidence': existing_entry.get('confidence', 0.0)
    }

image_width, image_height = 800, 600
preloaded_images = Queue(maxsize=5)
Thread(target=preload_images, daemon=True).start()

# Start the controller input thread
Thread(target=handle_controller_input, daemon=True).start()

try:
    Thread(target=handle_controller_input, daemon=True).start()
    print("Xbox controller support enabled. Connect a controller to use it.")
except Exception as e:
    print(f"Could not initialize Xbox controller support: {e}")
    print("Continuing without controller support. Use keyboard controls.")

root = tk.Tk()
root.title('Image Ranking')
root.state('zoomed')
root.configure(bg='#2C2C2C')

main_frame = tk.Frame(root, bg='#2C2C2C', padx=20, pady=20)
main_frame.pack(fill=tk.BOTH, expand=True)

image_frame = tk.Frame(main_frame, bg='#2C2C2C')
image_frame.pack(fill=tk.BOTH, expand=True)

left_frame = tk.Frame(image_frame, bg='#2C2C2C')
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
left_label = tk.Label(left_frame, bg='#2C2C2C')
left_label.pack(fill=tk.BOTH, expand=True)
left_info = tk.Label(left_frame, bg='#2C2C2C', fg='white', font=('Helvetica', 12))
left_info.pack(pady=10)

right_frame = tk.Frame(image_frame, bg='#2C2C2C')
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
right_label = tk.Label(right_frame, bg='#2C2C2C')
right_label.pack(fill=tk.BOTH, expand=True)
right_info = tk.Label(right_frame, bg='#2C2C2C', fg='white', font=('Helvetica', 12))
right_info.pack(pady=10)

button_frame = tk.Frame(main_frame, bg='#2C2C2C')
button_frame.pack(side=tk.BOTTOM, pady=20)

left_button = create_styled_button(button_frame, "← Left (←)", lambda: select_winner(True))
left_button.pack(side=tk.LEFT, padx=5)
right_button = create_styled_button(button_frame, "Right (→) →", lambda: select_winner(False))
right_button.pack(side=tk.LEFT, padx=5)
view_ranking_button = create_styled_button(button_frame, "View Rankings", view_rankings)
view_ranking_button.pack(side=tk.LEFT, padx=5)
view_top_button = create_styled_button(button_frame, "View Top Ranked", view_top_ranked)
view_top_button.pack(side=tk.LEFT, padx=5)
quit_button = create_styled_button(button_frame, "Quit", quit_program)
quit_button.pack(side=tk.LEFT, padx=5)

progress_frame = tk.Frame(root, bg='#2C2C2C', height=30)
progress_frame.pack(side=tk.BOTTOM, fill=tk.X)
progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
progress_bar.pack(fill=tk.X, padx=20, pady=10)

# Bind controller events
root.bind('<<ControllerLeft>>', lambda e: select_winner(True))
root.bind('<<ControllerRight>>', lambda e: select_winner(False))
root.bind('<<ControllerBlacklistLeft>>', lambda e: blacklist_and_replace_image(True))
root.bind('<<ControllerBlacklistRight>>', lambda e: blacklist_and_replace_image(False))

# Existing key bindings
root.bind('<Left>', on_key)
root.bind('<Right>', on_key)
root.bind('<z>', on_key)
root.bind('<x>', on_key)
root.bind('<Escape>', on_key)

show_next_images()
update_progress()
root.mainloop()