import cv2
import os
import time
import json
from recognizer import FaceRecognizer
import tkinter as tk
from tkinter import Tk, Label, Entry, Button, Text, Scrollbar, END
from PIL import Image, ImageTk
from datetime import datetime

LOG_FILE = "passages.txt"
IDENTITIES_FILE = "data/identities.json"
PERSISTENCE_THRESHOLD = 3  # secondes avant de considérer une personne partie

# Dictionnaire pour suivre les présences
active_presence = {}  # {id_: {"name": str, "start": float, "last_seen": float}}

def load_identities():
    if os.path.exists(IDENTITIES_FILE):
        with open(IDENTITIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_identities(data):
    os.makedirs(os.path.dirname(IDENTITIES_FILE), exist_ok=True)
    with open(IDENTITIES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def update_last_seen(id_, name):
    """Met à jour le champ last_seen dans identities.json"""
    identities = load_identities()
    found = False
    for ident in identities:
        if ident["id"] == id_:
            ident["name"] = name
            ident["last_seen"] = datetime.now().isoformat()
            found = True
            break
    if not found:
        identities.append({
            "id": id_,
            "name": name,
            "last_seen": datetime.now().isoformat()
        })
    save_identities(identities)

def prompt_for_name_with_image(face_img):
    face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(face_rgb).resize((200, 200))
    
    root = Tk()
    root.title("Renommer le visage")

    imgtk = ImageTk.PhotoImage(img)
    img_label = Label(root, image=imgtk)
    img_label.image = imgtk
    img_label.pack()

    name_var = Entry(root, width=30)
    name_var.pack(pady=10)
    name_var.focus()

    result = {"name": None}

    def submit():
        entered_name = name_var.get().strip()
        if entered_name:
            result["name"] = entered_name
            root.destroy()

    Button(root, text="Valider", command=submit).pack(pady=10)
    root.mainloop()

    return result["name"]

def save_face_crop(image, box, id_):
    os.makedirs("data/faces", exist_ok=True)
    x, y, w, h = box
    face = image[y:y+h, x:x+w]
    path = f"data/faces/{id_}.jpg"
    if not os.path.exists(path):  # ne pas écraser si déjà existant
        cv2.imwrite(path, face)

def write_log_line(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def main():
    recognizer = FaceRecognizer()
    
    # --- Création fenêtre logs tkinter ---
    log_root = tk.Tk()
    log_root.title("Logs Reconnaissance Faciale")
    log_text = Text(log_root, height=20, width=50, state='disabled', bg='black', fg='lime')
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar = Scrollbar(log_root, command=log_text.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    log_text['yscrollcommand'] = scrollbar.set

    def log(msg):
        log_text.config(state='normal')
        log_text.insert(END, msg + "\n")
        log_text.see(END)
        log_text.config(state='disabled')

    log(f"[INFO] Base chargée : {len(recognizer.known_faces)} visages connus.")
    log("Appuyez sur 'r' pour renommer un ID, 'q' pour quitter.")

    cap = cv2.VideoCapture(1)  # Ajuster la source vidéo
    selected_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            log("[WARN] Impossible de lire la vidéo.")
            break

        boxes, embeddings = recognizer.get_embeddings_from_frame(frame)

        seen_ids = []
        now = time.time()

        for emb, box in zip(embeddings, boxes):
            id_ = recognizer.get_or_create_id(emb)
            seen_ids.append(id_)
            name = recognizer.get_display_name(id_)
            log(f"Personne détectée : {name}")

            # Début détection
            if id_ not in active_presence:
                active_presence[id_] = {"name": name, "start": now, "last_seen": now}
                write_log_line(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {name} : Début détection")
            else:
                active_presence[id_]["last_seen"] = now

            # Mise à jour du fichier identities.json avec la date de passage
            update_last_seen(id_, name)

            save_face_crop(frame, box, id_)

        # Fin détection si absent depuis un certain temps
        for id_ in list(active_presence.keys()):
            if id_ not in seen_ids and (now - active_presence[id_]["last_seen"]) > PERSISTENCE_THRESHOLD:
                name = active_presence[id_]["name"]
                start = active_presence[id_]["start"]
                duration = now - start
                minutes, seconds = divmod(int(duration), 60)
                write_log_line(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {name} : Fin détection (durée : {minutes} min {seconds} s)")
                del active_presence[id_]

        # Mise à jour tkinter
        log_root.update()

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r') and boxes:
            x, y, w, h = boxes[selected_idx]
            face_img = frame[y:y+h, x:x+w]
            new_name = prompt_for_name_with_image(face_img)
            if new_name:
                old_id = seen_ids[selected_idx]
                if recognizer.rename_id(old_id, new_name):
                    log(f"[INFO] ID {old_id} renommé en '{new_name}'.")
                else:
                    log("[WARN] Échec du renommage.")
        elif key == 81:  # flèche gauche
            selected_idx = max(0, selected_idx - 1)
        elif key == 83:  # flèche droite
            selected_idx = min(len(boxes) - 1, selected_idx + 1)

    cap.release()
    cv2.destroyAllWindows()
    log_root.destroy()

if __name__ == "__main__":
    main()
