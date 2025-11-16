from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
import numpy as np
from storage import load_db, save_db

app = Flask(__name__)

DB_PATH = "embeddings.json"
FACE_DIR = "data/faces"

def is_uuid(s):
    """Vérifie si une chaîne est un UUID."""
    import uuid
    try:
        uuid.UUID(s)
        return True
    except ValueError:
        return False

@app.route('/')
def index():
    db = load_db()
    known_faces = {k: k for k in db.keys() if not is_uuid(k)}
    unknown_faces = {k: k for k in db.keys() if is_uuid(k)}
    return render_template('index.html', known_faces=known_faces, unknown_faces=unknown_faces)

@app.route('/faces/<filename>')
def serve_face(filename):
    return send_from_directory(FACE_DIR, filename)

@app.route('/rename', methods=['POST'])
def rename_identity():
    data = request.json
    old_id = data.get('old_id')
    new_id = data.get('new_id')
    db = load_db()
    
    if not old_id or not new_id or old_id not in db or new_id in db:
        return jsonify({'success': False, 'message': 'Nom invalide ou déjà utilisé.'})
    
    db[new_id] = db.pop(old_id)
    save_db(db)
    
    old_path = os.path.join(FACE_DIR, f"{old_id}.jpg")
    new_path = os.path.join(FACE_DIR, f"{new_id}.jpg")
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
    
    return jsonify({'success': True})

@app.route('/delete', methods=['POST'])
def delete_identities():
    data = request.json
    ids = data.get('ids', [])
    db = load_db()
    
    for id_ in ids:
        db.pop(id_, None)
        img_path = os.path.join(FACE_DIR, f"{id_}.jpg")
        if os.path.exists(img_path):
            os.remove(img_path)
    
    save_db(db)
    return jsonify({'success': True})

@app.route('/merge', methods=['POST'])
def merge_identities():
    data = request.json
    ids = data.get('ids', [])
    new_id = data.get('new_id')
    db = load_db()
    
    if len(ids) < 2 or not new_id or new_id in db:
        return jsonify({'success': False, 'message': 'Sélectionnez au moins deux identités et un nom valide.'})
    
    vectors = [np.array(db[i]) for i in ids if i in db]
    if not vectors:
        return jsonify({'success': False, 'message': 'Aucun embedding valide.'})
    
    merged = np.mean(vectors, axis=0).tolist()
    for id_ in ids:
        db.pop(id_, None)
        img_path = os.path.join(FACE_DIR, f"{id_}.jpg")
        if os.path.exists(img_path):
            os.remove(img_path)
    
    db[new_id] = merged
    save_db(db)
    
    old_img_path = os.path.join(FACE_DIR, f"{ids[0]}.jpg")
    new_img_path = os.path.join(FACE_DIR, f"{new_id}.jpg")
    if os.path.exists(old_img_path):
        os.rename(old_img_path, new_img_path)
    
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)