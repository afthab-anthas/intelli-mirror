import os
import cv2
import pickle
import joblib
import numpy as np
from pathlib import Path
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

print("═════════════════════════════════════════════════")
print("   INTELLI-MIRROR : HYBRID AI RETRAINING HUB     ")
print("═════════════════════════════════════════════════")

print("\n1. Loading RAW enrollment data (100x100 crops)...")
DATA_FILE = Path('Magic_Mirror_Package/face_profiles/face_data.pkl')
OUT_FILE = Path('Magic_Mirror_Package/face_profiles/hybrid_ai_model.pkl')
SFACE_PATH = 'Magic_Mirror_Package/sface.onnx'

with open(DATA_FILE, 'rb') as f:
    faces, labels = pickle.load(f)

print(f"   Loaded {len(labels)} face captures.")

print("\n2. Booting up SFace Neural Network to extract 128d features...")
recognizer = cv2.FaceRecognizerSF.create(SFACE_PATH, "")

embeddings = []
for face in faces:
    # Safely convert historic (100x100) Grayscale back to (112x112) BGR for SFace Compatibility 
    bgr = cv2.cvtColor(cv2.resize(face, (112, 112)), cv2.COLOR_GRAY2BGR)
    feat = recognizer.feature(bgr)
    embeddings.append(feat.flatten())

X = np.array(embeddings)
y = np.array(labels)

print(f"\n3. Activating Support Vector Machine (SVM) on {len(set(y))} unique identities...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Retraining using exact grid settings
svm = SVC(kernel='rbf', class_weight='balanced', probability=True, C=5, gamma=0.001)
svm.fit(X_train, y_train)

acc = svm.score(X_test, y_test)
print(f"   Test Accuracy mapped at: {acc*100:.1f}%")

print("\n4. Serializing final unified logic payload...")
joblib.dump(svm, OUT_FILE)
print(f"\n✅ SUCCESS! Retrained and securely serialized model to:\n   {OUT_FILE}\n")
