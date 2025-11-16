import cv2
import mediapipe as mp
import numpy as np
import insightface
from insightface.app import FaceAnalysis
import uuid
import os

from storage import load_db, save_db  # Import de storage.py

class FaceRecognizer:
    def __init__(self, db_path="embeddings.json"):
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.6)

        self.face_analyzer = FaceAnalysis(name="buffalo_l", providers=['CPUExecutionProvider'])
        self.face_analyzer.prepare(ctx_id=0)

        self.db_path = db_path
        self.threshold = 0.6
        self.known_faces = {}  # id -> np.array embedding

        self.load_db()
        # self.print_db()  # Décommente pour debug base

    def load_db(self):
        data = load_db()  # appel à storage.py
        cleaned = {}
        for k, v in data.items():
            try:
                arr = np.array(v, dtype=np.float32)
                if arr.ndim == 1 and arr.size > 0:
                    cleaned[k] = arr
                else:
                    print(f"[WARN] Entrée {k} ignorée (format invalide).")
            except Exception as e:
                print(f"[WARN] Entrée {k} ignorée (exception {e}).")
        self.known_faces = cleaned
        print(f"[INFO] Base chargée : {len(self.known_faces)} visages connus (après nettoyage).")

    def save_db(self):
        serializable = {k: v.tolist() for k, v in self.known_faces.items()}
        save_db(serializable)  # appel à storage.py
        print("[INFO] Base sauvegardée.")

    def get_embeddings_from_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = self.face_analyzer.get(rgb)

        embeddings = []
        boxes = []

        for face in faces:
            emb = face.embedding
            x1, y1, x2, y2 = face.bbox.astype(int)
            embeddings.append(emb)
            boxes.append((x1, y1, x2 - x1, y2 - y1))

        return boxes, embeddings

    def get_or_create_id(self, embedding):
        if len(self.known_faces) == 0:
            new_id = str(uuid.uuid4())
            self.known_faces[new_id] = embedding
            self.save_db()
            return new_id

        distances = []
        for known_id, known_emb in self.known_faces.items():
            dist = self.cosine_distance(embedding, known_emb)
            distances.append((dist, known_id))

        distances.sort(key=lambda x: x[0])
        best_dist, best_id = distances[0]

        if best_dist < self.threshold:
            return best_id
        else:
            new_id = str(uuid.uuid4())
            self.known_faces[new_id] = embedding
            self.save_db()
            return new_id

    def rename_id(self, old_id, new_name):
        if old_id not in self.known_faces:
            print(f"[WARN] ID {old_id} non trouvé.")
            return False
        if new_name in self.known_faces:
            print(f"[WARN] Le nom {new_name} existe déjà.")
            return False
        if not isinstance(new_name, str) or len(new_name.strip()) == 0:
            print(f"[WARN] Nouveau nom invalide.")
            return False

        self.known_faces[new_name] = self.known_faces.pop(old_id)
        self.save_db()
        print(f"[INFO] ID '{old_id}' renommé en '{new_name}'.")
        return True
    
    def get_display_name(self, id_):

    # Ici, ta base known_faces a des clés qui sont soit des UUID soit des noms.
    # Si l’ID est un UUID, il faut vérifier si un nom existe (exemple dans ta base).
    # Dans ta base, c’est le mapping id->embedding, pas id->nom.
    # Donc, il faut adapter selon ton système de gestion des noms.

    # Si tu stockes les noms directement comme clé dans known_faces, fais juste :
        if id_ in self.known_faces:
            return id_  # C’est déjà un nom

    # Sinon, essayer de chercher dans ta base de renommage (s’il existe)
    # Pour simplifier, retourne l’ID tel quel :
            return id_


    @staticmethod
    def cosine_distance(a, b):
        a_norm = a / np.linalg.norm(a)
        b_norm = b / np.linalg.norm(b)
        return 1 - np.dot(a_norm, b_norm)

    def print_db(self):
        print("[DEBUG] Base des visages connus :")
        for k, v in self.known_faces.items():
            print(f" - ID: {k}, type: {type(v)}, shape: {v.shape if isinstance(v, np.ndarray) else 'N/A'}")

