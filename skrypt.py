import unreal
import os

def get_dynamic_paths():
    """Wykrywa oba typy ścieżek na podstawie lokalizacji pliku .py"""
    win_path = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
    ue_path = "/Game/AutoHitMapgenerator"
    if '/Content/' in win_path:
        ue_path = "/Game/" + win_path.split('/Content/')[1]
    return win_path, ue_path

def generuj_pelny_zestaw_map(docelowa_sciezka_ue="", rozdzielczosc=2048):
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    # ŚCIEŻKI NARZĘDZIA (Skąd brać Blueprinty i Render Targety)
    win_path, tool_ue_path = get_dynamic_paths()
    
    # ŚCIEŻKA DOCELOWA (Gdzie zapisać finalne tekstury)
    # Jeśli z Widgetu przyjdzie pusta ścieżka, awaryjnie używamy folderu narzędzia
    sciezka_zapisu = docelowa_sciezka_ue if docelowa_sciezka_ue else tool_ue_path
    
    unreal.log(f"--- Uruchamiam generator z folderu: {tool_ue_path} ---")
    unreal.log(f"--- Docelowy folder zapisu tekstur: {sciezka_zapisu} | Rozdzielczość: {rozdzielczosc}x{rozdzielczosc} ---")

    # 1. ZNAJDŹ TEREN
    proxies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.LandscapeProxy)
    if not proxies:
        unreal.log_error("BŁĄD: Brak terenu!")
        return

    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')
    for p in proxies:
        o, e = p.get_actor_bounds(False)
        if e.x == 0 and e.y == 0: continue
        min_x = min(min_x, o.x - e.x); min_y = min(min_y, o.y - e.y); min_z = min(min_z, o.z - e.z)
        max_x = max(max_x, o.x + e.x); max_y = max(max_y, o.y + e.y); max_z = max(max_z, o.z + e.z)

    szerokosc = max(max_x - min_x, max_y - min_y)
    lokacja_kamery = unreal.Vector((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, max_z + 20000.0)
    rotacja_kamery = unreal.Rotator(0.0, -90.0, 0.0)

    # 2. ZMIANA ROZDZIELCZOŚCI RENDER TARGETÓW
    # Ładujemy RT narzędzia i wymuszamy na nich nową rozdzielczość z Widgetu
    rt_height = unreal.EditorAssetLibrary.load_asset(f"{tool_ue_path}/RT_Heightmap")
    rt_albedo = unreal.EditorAssetLibrary.load_asset(f"{tool_ue_path}/RT_Albedo")
    
    if rt_height and rt_albedo:
        rt_height.set_editor_property("size_x", int(rozdzielczosc))
        rt_height.set_editor_property("size_y", int(rozdzielczosc))
        rt_albedo.set_editor_property("size_x", int(rozdzielczosc))
        rt_albedo.set_editor_property("size_y", int(rozdzielczosc))
    else:
        unreal.log_error("BŁĄD: Nie znaleziono Render Targetów w folderze narzędzia!")
        return

    # 3. KAMERA HEIGHTMAPY
    bp_class_height = unreal.EditorAssetLibrary.load_blueprint_class(f"{tool_ue_path}/BP_KameraHeightmap")
    kamera_height = actor_subsystem.spawn_actor_from_class(bp_class_height, lokacja_kamery, rotacja_kamery)
    comp_height = kamera_height.get_component_by_class(unreal.SceneCaptureComponent2D)
    comp_height.set_editor_property("ortho_width", szerokosc)

    instancja_mat = unreal.EditorAssetLibrary.load_asset(f"{tool_ue_path}/MI_Heightmap")
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(instancja_mat, "MinZ", float(min_z))
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(instancja_mat, "TotalHeight", float(max_z - min_z))
    comp_height.capture_scene()

    # 4. KAMERA ALBEDO
    bp_class_albedo = unreal.EditorAssetLibrary.load_blueprint_class(f"{tool_ue_path}/BP_AlbedoCamera")
    kamera_albedo = actor_subsystem.spawn_actor_from_class(bp_class_albedo, lokacja_kamery, rotacja_kamery)
    comp_albedo = kamera_albedo.get_component_by_class(unreal.SceneCaptureComponent2D)
    comp_albedo.set_editor_property("ortho_width", szerokosc)
    comp_albedo.capture_scene()

    # 5. EKSPORT I NADPISANIE TEKSTUR
    unreal.log("Przetwarzam Render Targety bezpośrednio na tekstury UE5...")
    
    plik_height = f"{win_path}/Temp_Height.exr"
    plik_albedo = f"{win_path}/Temp_Albedo.png"

    # Python zrzuca cicho pliki do swojego roboczego folderu na dysku
    unreal.RenderingLibrary.export_render_target(world, rt_height, win_path, "Temp_Height.exr")
    unreal.RenderingLibrary.export_render_target(world, rt_albedo, win_path, "Temp_Albedo.png")

    # Python natychmiast przerabia je na finalne tekstury w DOCELOWEJ ścieżce
    task_height = unreal.AssetImportTask()
    task_height.filename = plik_height
    task_height.destination_path = sciezka_zapisu
    task_height.destination_name = "T_Heightmap"
    task_height.replace_existing = True  
    task_height.automated = True
    task_height.save = True

    task_albedo = unreal.AssetImportTask()
    task_albedo.filename = plik_albedo
    task_albedo.destination_path = sciezka_zapisu
    task_albedo.destination_name = "T_Albedo"
    task_albedo.replace_existing = True
    task_albedo.automated = True
    task_albedo.save = True

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task_height, task_albedo])

    # Sprzątanie cichych plików tymczasowych
    if os.path.exists(plik_height): os.remove(plik_height)
    if os.path.exists(plik_albedo): os.remove(plik_albedo)

    # 6. KASOWANIE KAMER
    actor_subsystem.destroy_actor(kamera_height)
    actor_subsystem.destroy_actor(kamera_albedo)

    unreal.log_warning(f"GOTOWE! Tekstury zapisane/nadpisane w folderze: {sciezka_zapisu} z rozdzielczością {rozdzielczosc}x{rozdzielczosc}")

# UWAGA: Usunięto wywołanie generuj_pelny_zestaw_map() z tego miejsca!
# Będzie ono odpalane wyłącznie na polecenie płynące z Twojego Blueprinta (Widgetu).