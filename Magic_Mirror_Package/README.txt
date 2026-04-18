# Magic Mirror OS (Friend Edition)

This is a professional AI-based face recognition and hand gesture control system.

## Step 1: Install Python & AI Libraries
Open your terminal in this folder and run:
pip install -r requirements.txt

## Step 2: Register Your Face
Run this command and look at the camera for the 150 snapshot loop:
python face_recognition_system.py --enroll

## Step 3: Train the Hybrid Brain
Open 'train_face_model.ipynb' in Jupyter or VS Code and click "Run All Cells".
This will build your personal AI identity model.

## Step 4: Launch the Mirror!
Run the master engine:
python magic_mirror_engine.py

Enjoy!
