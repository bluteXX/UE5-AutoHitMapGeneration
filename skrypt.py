import unreal
import os

def get_dynamic_paths():
    # Detect both OS and UE paths based on the .py file location
    win_path = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
    ue_path = "/Game/AutoHitMapgenerator"
    if '/Content/' in win_path:
        ue_path = "/Game/" + win_path.split('/Content/')[1]
    return win_path, ue_path

def generate_map_set(target_ue_path="", resolution=2048):
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    # Resolve paths
    win_path, tool_ue_path = get_dynamic_paths()
    save_path = target_ue_path if target_ue_path else tool_ue_path
    
    unreal.log(f"--- Starting generator from: {tool_ue_path} ---")
    unreal.log(f"--- Target save path: {save_path} | Resolution: {resolution}x{resolution} ---")

    # 1. Find Landscape and calculate bounds
    proxies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.LandscapeProxy)
    if not proxies:
        unreal.log_error("ERROR: No Landscape found!")
        return

    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')
    
    for p in proxies:
        origin, extent = p.get_actor_bounds(False)
        if extent.x == 0 and extent.y == 0: continue
        min_x = min(min_x, origin.x - extent.x)
        min_y = min(min_y, origin.y - extent.y)
        min_z = min(min_z, origin.z - extent.z)
        max_x = max(max_x, origin.x + extent.x)
        max_y = max(max_y, origin.y + extent.y)
        max_z = max(max_z, origin.z + extent.z)

    ortho_width = max(max_x - min_x, max_y - min_y)
    camera_location = unreal.Vector((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, max_z + 20000.0)
    camera_rotation = unreal.Rotator(0.0, -90.0, 0.0)

    # 2. Update Render Targets resolution
    res_int = int(resolution)
    rt_height = unreal.EditorAssetLibrary.load_asset(f"{tool_ue_path}/RT_Heightmap")
    rt_albedo = unreal.EditorAssetLibrary.load_asset(f"{tool_ue_path}/RT_Albedo")
    
    if rt_height and rt_albedo:
        rt_height.set_editor_property("size_x", res_int)
        rt_height.set_editor_property("size_y", res_int)
        rt_albedo.set_editor_property("size_x", res_int)
        rt_albedo.set_editor_property("size_y", res_int)
    else:
        unreal.log_error("ERROR: Render Targets not found in the tool folder!")
        return

    # 3. Setup and capture Heightmap
    bp_class_height = unreal.EditorAssetLibrary.load_blueprint_class(f"{tool_ue_path}/BP_CameraHeightmap")
    camera_height = actor_subsystem.spawn_actor_from_class(bp_class_height, camera_location, camera_rotation)
    comp_height = camera_height.get_component_by_class(unreal.SceneCaptureComponent2D)
    comp_height.set_editor_property("ortho_width", ortho_width)

    mat_instance = unreal.EditorAssetLibrary.load_asset(f"{tool_ue_path}/MI_Heightmap")
    if mat_instance:
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mat_instance, "MinZ", float(min_z))
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mat_instance, "TotalHeight", float(max_z - min_z))
        unreal.MaterialEditingLibrary.update_material_instance(mat_instance)
        comp_height.add_or_update_blendable(mat_instance, 1.0)
    
    comp_height.capture_scene()
    comp_height.capture_scene() # Double capture to prevent Render Thread Lag

    # 4. Setup and capture Albedo
    bp_class_albedo = unreal.EditorAssetLibrary.load_blueprint_class(f"{tool_ue_path}/BP_AlbedoCamera")
    camera_albedo = actor_subsystem.spawn_actor_from_class(bp_class_albedo, camera_location, camera_rotation)
    comp_albedo = camera_albedo.get_component_by_class(unreal.SceneCaptureComponent2D)
    comp_albedo.set_editor_property("ortho_width", ortho_width)
    comp_albedo.capture_scene()

    # 5. Export and re-import as final textures
    unreal.log("Processing Render Targets into UE5 textures...")
    file_height = f"{win_path}/Temp_Height.exr"
    file_albedo = f"{win_path}/Temp_Albedo.png"

    unreal.RenderingLibrary.export_render_target(world, rt_height, win_path, "Temp_Height.exr")
    unreal.RenderingLibrary.export_render_target(world, rt_albedo, win_path, "Temp_Albedo.png")

    task_height = unreal.AssetImportTask()
    task_height.filename = file_height
    task_height.destination_path = save_path
    task_height.destination_name = "T_Heightmap"
    task_height.replace_existing = True  
    task_height.automated = True
    task_height.save = True

    task_albedo = unreal.AssetImportTask()
    task_albedo.filename = file_albedo
    task_albedo.destination_path = save_path
    task_albedo.destination_name = "T_Albedo"
    task_albedo.replace_existing = True
    task_albedo.automated = True
    task_albedo.save = True

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task_height, task_albedo])

    # 6. Cleanup temporary files and actors
    if os.path.exists(file_height): os.remove(file_height)
    if os.path.exists(file_albedo): os.remove(file_albedo)

    actor_subsystem.destroy_actor(camera_height)
    actor_subsystem.destroy_actor(camera_albedo)

    unreal.log_warning(f"DONE! Textures saved in: {save_path} at {resolution}x{resolution}")