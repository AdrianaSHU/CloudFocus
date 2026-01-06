import numpy as np
import tflite_runtime.interpreter as tflite
import os

MODEL_PATH = 'emo_model.tflite'

# Load Model
interpreter = tflite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Create a fake "Average Gray" image (all pixels = 127)
# We use 127 because it's a safe middle value
input_shape = input_details[0]['shape']
fake_image_0_255 = np.full(input_shape, 127.0, dtype=np.float32)

print("🔍 STARTING INPUT RANGE TEST...\n")

# --- TEST 1: Raw 0-255 (What we tried last) ---
print("Test 1: Inputs 0 to 255")
interpreter.set_tensor(input_details[0]['index'], fake_image_0_255)
interpreter.invoke()
out1 = interpreter.get_tensor(output_details[0]['index'])[0]
print(f"   Output: {out1} \n")

# --- TEST 2: Normalized 0-1 (Standard) ---
print("Test 2: Inputs 0.0 to 1.0")
fake_image_0_1 = fake_image_0_255 / 255.0
interpreter.set_tensor(input_details[0]['index'], fake_image_0_1)
interpreter.invoke()
out2 = interpreter.get_tensor(output_details[0]['index'])[0]
print(f"   Output: {out2} \n")

# --- TEST 3: Normalized -1 to 1 (MobileNet Standard) ---
print("Test 3: Inputs -1.0 to 1.0")
fake_image_neg1_1 = (fake_image_0_255 / 127.5) - 1.0
interpreter.set_tensor(input_details[0]['index'], fake_image_neg1_1)
interpreter.invoke()
out3 = interpreter.get_tensor(output_details[0]['index'])[0]
print(f"   Output: {out3} \n")

# Verdict Logic
if np.isnan(out1).any(): print("❌ Test 1 FAILED (NaN)")
else: print("✅ Test 1 PASSED")

if np.isnan(out2).any(): print("❌ Test 2 FAILED (NaN)")
else: print("✅ Test 2 PASSED")

if np.isnan(out3).any(): print("❌ Test 3 FAILED (NaN)")
else: print("✅ Test 3 PASSED")




