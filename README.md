# 🏔️ UE5 Auto Landscape Map Generator

An automated tool for Unreal Engine 5 that allows you to generate a heightmap and a clean color texture (Albedo/BaseColor) from your Landscape with a single click. 

No more manual top-down camera setup, guessing resolutions, or messing around with exporting to external software!

## ✨ Main Features

* **100% Automated Process:** Enter the resolution, save path, click "Generate", and the tool automatically creates cameras, takes top-down captures, and converts Render Targets into ready-to-use `.uasset` textures.
* **Automatic Height Scaling (Z-Bounds):** The Python script scans your Landscape, finds its lowest and highest points, and dynamically modifies the camera's material parameters (`MinZ`, `TotalHeight`) so the Heightmap uses the full black-and-white gradient range.
* **Clean Albedo (Flat Color):** The Albedo camera is configured to ignore engine lighting, volumetric fog, and post-processing, generating the pure color of the terrain.
* **Render Thread Lag Proof:** Implemented a workaround for GPU lag – the heightmap camera forces a double frame capture, ensuring the material updates correctly and preventing flat, black maps on the first use.

## ⚙️ Requirements

To make the tool work properly, you must enable the following free plugins in your Unreal Engine 5 project:
1. **Python Editor Script Plugin**
2. **Editor Scripting Utilities**

## 📥 Installation

1. Download the repository.
2. Copy the `AutoHitMapgenerator` folder into the `Content` folder of your project on your drive.
3. *Important:* Ensure the `skrypt.py` file is physically located in the `Content/AutoHitMapgenerator` folder (even if you can't see it in the Unreal Engine Editor, it must be there in your OS file explorer!).

## 🚀 How to Use

1. In Unreal Engine, open the tool's folder in the **Content Browser**.
2. Right-click the Widget file (e.g., `EUW_Generate`) and select **Run Editor Utility Widget**.
3. In the tool window, enter:
   * **Save path:** (e.g., `/Game/Textures/Landscape`) - if left blank, it will save in the tool's default folder.
   * **Resolution:** (e.g., `2048`, `4096`, `8192`).
4. Click the generate button. 
5. Check the Output Log and enjoy your ready `T_Heightmap` and `T_Albedo` textures in the chosen folder!

## 🛠️ Under the Hood (For Advanced Users)

* **Python Script (`skrypt.py`):** The core of the tool. Calculates terrain dimensions (Bounds), casts resolution types, dynamically exports textures to a working drive (EXR/PNG), and automatically re-imports them silently back into the engine using `unreal.AssetImportTask`.
* **Bypassing UE Python Node Bugs:** The Widget calls the script using `Execute Console Command` with the `py import sys...` prefix. This allows for fully dynamic path loading and bypasses known bugs with the *Execute Python Command* node in newer engine versions.
* **Height Material (`M_Heightmap` / `MI_Heightmap`):** Uses Absolute World Position Z. Converted into scalar parameters (`MinZ`, `TotalHeight`) that are overwritten by Python, allowing mathematical matching of the gradient to any peaks and valleys.

## ⚠️ Troubleshooting (Known Issues)

* **Python throws an error in the console (ModuleNotFoundError):** Make sure you don't have hidden file extensions enabled in Windows and that your file isn't accidentally named `skrypt.py.txt`.
* **Albedo camera renders dark spots / shadows:** Make sure the material applied to the terrain isn't Unreal's default checkerboard (`WorldGridMaterial`). If issues persist, completely disable the `Lighting` and `Atmosphere/Fog` show flags in the `BP_AlbedoCamera` component.
* **Engine ignores the folder after copying:** Remember that `.uasset` files are not fully backward compatible. A folder created in UE 5.7 might not be visible in UE 5.4. (The Python script, however, works in any version).
