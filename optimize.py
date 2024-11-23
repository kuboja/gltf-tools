from pygltflib import GLTF2, Buffer, Material
from scipy.spatial.transform import Rotation as R
from PIL import Image
import io

def remove_empty_nodes(gltf: GLTF2):
    def is_empty(node_index: int) -> bool:
        node = gltf.nodes[node_index]
        # A node is empty if it has no mesh, no camera, and no children
        return node.mesh is None and node.camera is None and len(node.children) == 0

    # initial_node_count = len(gltf.nodes)

    # Iterate until no changes are needed
    while True:
        nodes_to_remove = set()
        # Identify empty nodes
        for i, node in enumerate(gltf.nodes):
            if is_empty(i):
                nodes_to_remove.add(i)

        # If no nodes to remove, break the loop
        if not nodes_to_remove:
            break

        # Remove references to empty nodes from parents
        for node in gltf.nodes:
            node.children = [child for child in node.children if child not in nodes_to_remove]

        # Remove empty nodes and update index mapping
        new_nodes = []
        index_mapping = {}
        new_index = 0
        for i, node in enumerate(gltf.nodes):
            if i not in nodes_to_remove:
                index_mapping[i] = new_index
                new_nodes.append(node)
                new_index += 1

        # Update children references to new indices
        for node in new_nodes:
            node.children = [index_mapping[child] for child in node.children]

        # Update scene root nodes references to new indices
        for scene in gltf.scenes:
            scene.nodes = [index_mapping[node] for node in scene.nodes if node in index_mapping]

        gltf.nodes = new_nodes

    # final_node_count = len(gltf.nodes)
    # removed_node_count = initial_node_count - final_node_count

    # print(f"Initial node count: {initial_node_count}")
    # print(f"Removed node count: {removed_node_count}")
    # print(f"Final node count: {final_node_count}")

    # count_empty = sum(1 for i in range(len(gltf.nodes)) if is_empty(i))
    # print(f"Any empty nodes left: {count_empty}")

def optimize_buffers(gltf):
    """
    Optimalizuje buffery a odstraní nevyužitá data v GLTF souboru.
    """

    # Sbíráme využité accessors
    used_accessors = set()
    for mesh in gltf.meshes:
        for primitive in mesh.primitives:
            if primitive.attributes:
                for attr in primitive.attributes.__dict__.values():  # Iterujeme přes atributy
                    if attr is not None:
                        used_accessors.add(attr)
            if primitive.indices is not None:
                used_accessors.add(primitive.indices)

    # Sbíráme využité bufferViews z accessors
    used_buffer_views = {gltf.accessors[acc].bufferView for acc in used_accessors if gltf.accessors[acc].bufferView is not None}

    for image in gltf.images:
        if image.bufferView is not None:
            used_buffer_views.add(image.bufferView)

    # Vytváříme nový seznam bufferViews a mapujeme staré na nové
    new_buffer_views = []
    buffer_view_map = {}
    for old_index in sorted(used_buffer_views):
        buffer_view_map[old_index] = len(new_buffer_views)
        new_buffer_views.append(gltf.bufferViews[old_index])

    gltf.bufferViews = new_buffer_views

    # Optimalizujeme buffer data
    new_buffer_data = bytearray()
    for buffer_view in gltf.bufferViews:
        start = buffer_view.byteOffset or 0
        end = start + buffer_view.byteLength
        new_offset = len(new_buffer_data)
        new_buffer_data.extend(gltf._glb_data[start:end])
        buffer_view.byteOffset = new_offset  # Aktualizujeme offset v novém bufferu

    for accessor in gltf.accessors:
        if accessor.bufferView in buffer_view_map:
            accessor.bufferView = buffer_view_map[accessor.bufferView]

    for image in gltf.images:
        if image.bufferView in buffer_view_map:
            image.bufferView = buffer_view_map[image.bufferView]

    # Filtrování využitých accessors
    gltf.accessors = [gltf.accessors[acc] for acc in sorted(used_accessors) if acc < len(gltf.accessors)]

    # Aktualizace referencí mesh primitives
    for mesh in gltf.meshes:
        for primitive in mesh.primitives:
            if primitive.attributes:
                for attr_key in dir(primitive.attributes):
                    if not attr_key.startswith('_'):
                        attr_value = getattr(primitive.attributes, attr_key, None)
                        if attr_value in used_accessors:
                            setattr(primitive.attributes, attr_key, sorted(used_accessors).index(attr_value))
            if primitive.indices is not None and primitive.indices in used_accessors:
                primitive.indices = sorted(used_accessors).index(primitive.indices)

    # Uložíme nové buffer data jako inline base64
    gltf.buffers = [Buffer(byteLength=len(new_buffer_data))]

    # Zapisujeme optimalizovaná data zpět do _glb_data
    gltf._glb_data = new_buffer_data

    return gltf

def clean_gltf(gltf):
    """
    Odstraní nepoužívané geometrie, materiály, textury a buffery z GLTF souboru.
    """

    remove_empty_nodes(gltf)

    # Shromáždění použitých meshes z uzlů
    used_meshes = {node.mesh for node in gltf.nodes if node.mesh is not None}

    # Shromáždění použitých materiálů z použitých meshes
    used_materials = set()
    for mesh_index in used_meshes:
        mesh = gltf.meshes[mesh_index]
        for primitive in mesh.primitives:
            if primitive.material is not None:
                used_materials.add(primitive.material)

    # Shromáždění použitých textur z použitých materiálů
    used_textures = set()
    for material_index in used_materials:
        material: Material = gltf.materials[material_index]
        if material.emissiveTexture:
            used_textures.add(material.emissiveTexture.index)
        if material.normalTexture:
            used_textures.add(material.normalTexture.index)
        if material.occlusionTexture:
            used_textures.add(material.occlusionTexture.index)
        
        if material.extensions.get('KHR_materials_pbrSpecularGlossiness'):
            pbr = material.extensions['KHR_materials_pbrSpecularGlossiness']
            if pbr.get('diffuseTexture'):
                used_textures.add(pbr['diffuseTexture']['index'])
            if pbr.get('specularGlossinessTexture'):
                used_textures.add(pbr['specularGlossinessTexture']['index'])

        if material.pbrMetallicRoughness:
            pbr = material.pbrMetallicRoughness
            if pbr.baseColorTexture:
                used_textures.add(pbr.baseColorTexture.index)
            if pbr.metallicRoughnessTexture:
                used_textures.add(pbr.metallicRoughnessTexture.index)

    # Shromáždění použitých images z použitých textur
    used_images = set()
    for texture_index in used_textures:
        texture = gltf.textures[texture_index]
        if texture.source is not None:
            used_images.add(texture.source)

    used_buffers = set(range(len(gltf.buffers)))  # Buffery budeme optimalizovat později

    # Filtruj položky na základě použitých referencí
    gltf.meshes = [mesh for i, mesh in enumerate(gltf.meshes) if i in used_meshes]
    gltf.materials = [material for i, material in enumerate(gltf.materials) if i in used_materials]
    gltf.textures = [texture for i, texture in enumerate(gltf.textures) if i in used_textures]
    gltf.images = [image for i, image in enumerate(gltf.images) if i in used_images]
    gltf.buffers = [buffer for i, buffer in enumerate(gltf.buffers) if i in used_buffers]

    # Aktualizace referencí v uzlech a ostatních objektech
    def remap_indices(items, used_indices):
        """
        Přečísluje indexy položek na základě použitých referencí.
        """
        index_map = {old: new for new, old in enumerate(sorted(used_indices))}
        return [index_map[i] for i in used_indices], index_map

    _, mesh_map = remap_indices(gltf.meshes, used_meshes)
    _, material_map = remap_indices(gltf.materials, used_materials)
    _, texture_map = remap_indices(gltf.textures, used_textures)
    _, image_map = remap_indices(gltf.images, used_images)

    # Aktualizace referencí v uzlech
    for node in gltf.nodes:
        if node.mesh is not None:
            node.mesh = mesh_map[node.mesh]

    # Aktualizace referencí v primitivách
    for mesh in gltf.meshes:
        for primitive in mesh.primitives:
            if primitive.material is not None:
                primitive.material = material_map[primitive.material]
            # if primitive.indices is not None:
            #     primitive.indices = mesh_map[primitive.indices]

    # Aktualizace referencí v materiálech
    for material in gltf.materials:

        if material.emissiveTexture:
            material.emissiveTexture.index = texture_map[material.emissiveTexture.index]
        if material.normalTexture:
            material.normalTexture.index = texture_map[material.normalTexture.index]
        if material.occlusionTexture:
            material.occlusionTexture.index = texture_map[material.occlusionTexture.index]

        if material.extensions.get('KHR_materials_pbrSpecularGlossiness'):
            pbr = material.extensions['KHR_materials_pbrSpecularGlossiness']
            if pbr.get('diffuseTexture'):
                pbr['diffuseTexture']['index'] = texture_map[pbr['diffuseTexture']['index']]
            if pbr.get('specularGlossinessTexture'):
                pbr['specularGlossinessTexture']['index'] = texture_map[pbr['specularGlossinessTexture']['index']]

        if material.pbrMetallicRoughness:
            pbr = material.pbrMetallicRoughness
            if pbr.baseColorTexture:
                pbr.baseColorTexture.index = texture_map[pbr.baseColorTexture.index]
            if pbr.metallicRoughnessTexture:
                pbr.metallicRoughnessTexture.index = texture_map[pbr.metallicRoughnessTexture.index]

    # Aktualizace referencí v texturách
    for texture in gltf.textures:
        if texture.source is not None:
            texture.source = image_map[texture.source]


def convert_images_to_webp(gltf, min_size_kb=50):
    """
    Konvertuje obrázky v GLTF souboru do formátu WebP a uloží je jako binární data v _glb_data.
    Obrázky se konvertují pouze, pokud jejich velikost přesahuje zadaný práh (v kB).

    :param gltf: GLTF objekt obsahující obrázky.
    :param min_size_kb: Minimální velikost obrázku (v kB) pro konverzi.
    """
    # new_buffer_data = bytearray(gltf._glb_data)  # Vytvoření kopie původních binárních dat

    buffer_data = get_buffer_data(gltf)

    for image in gltf.images:
        if image.mimeType == "image/webp":
            # Pokud je obrázek již ve formátu WebP, přeskočíme ho
            continue

        if image.bufferView is not None:
            buffer_view = gltf.bufferViews[image.bufferView]
            buffer_index = buffer_view.buffer
            start = buffer_view.byteOffset or 0
            end = start + buffer_view.byteLength

            # Podmínka pro minimální velikost obrázku
            if buffer_view.byteLength < min_size_kb * 1024:
                # Pokud je obrázek menší než daný práh, přeskočíme ho
                continue

            image_data = io.BytesIO(buffer_data[buffer_index][start:end])

            # Načtení obrázku pomocí PIL
            img = Image.open(image_data)

            # Konverze obrázku do WebP
            output = io.BytesIO()
            img.save(output, format="WEBP", quality=85)
            output.seek(0)

            # Aktualizace bufferu s novými daty
            new_image_data = output.read()
            new_offset = len(buffer_data[buffer_index])
            buffer_data[buffer_index].extend(new_image_data)

            # Aktualizace bufferView s novými daty
            buffer_view.byteOffset = new_offset
            buffer_view.byteLength = len(new_image_data)

             # Aktualizace MIME typu na image/webp
            image.mimeType = "image/webp"

    # Aktualizace GLB bufferů
    update_buffer_data(gltf, buffer_data)

def get_buffer_data(gltf: GLTF2):
    """
    Načte binární data bufferů do paměti.

    :param gltf: GLTF objekt obsahující buffery.
    """
    # Rozlišení mezi GLB a GLTF
    if hasattr(gltf, '_glb_data') and gltf._glb_data is not None:
        # Práce s `_glb_data`
        buffer_data = [bytearray(gltf._glb_data)]
    else:
        # Práce s více buffery v GLTF
        buffer_data = [bytearray(buffer.data) for buffer in gltf.buffers]

    return buffer_data

def update_buffer_data(gltf: GLTF2, buffer_data):
    """
    Aktualizuje binární data bufferů v GLTF souboru.

    :param gltf: GLTF objekt obsahující buffery.
    :param buffer_data: List s binárními daty bufferů.
    """
    # Rozlišení mezi GLB a GLTF
    if hasattr(gltf, '_glb_data') and gltf._glb_data is not None:
        # Práce s `_glb_data`
        gltf._glb_data = buffer_data[0]
    else:
        # Práce s více buffery v GLTF
        for i, buffer in enumerate(gltf.buffers):
            buffer.data = bytes(buffer_data[i])


def resize_images_in_gltf(gltf: GLTF2, max_width: float = 1024, max_height: float = 1024):
    """
    Zmenší obrázky v GLTF souboru na dané maximální rozlišení a uloží je jako binární data v _glb_data.

    :param gltf: GLTF objekt obsahující obrázky.
    :param max_width: Maximální šířka obrázku.
    :param max_height: Maximální výška obrázku.
    """
    buffer_data = get_buffer_data(gltf)

    for image in gltf.images:
        if image.bufferView is not None:
            buffer_view = gltf.bufferViews[image.bufferView]
            buffer_index = buffer_view.buffer
            start = buffer_view.byteOffset or 0
            end = start + buffer_view.byteLength

            image_data = io.BytesIO(buffer_data[buffer_index][start:end])

            # Načtení obrázku pomocí PIL
            img = Image.open(image_data)

            # Změna velikosti obrázku, pokud přesahuje maximální rozměry
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height))

                # Uložení změněného obrázku
                output = io.BytesIO()
                img_format = img.format or "PNG"  # Zachování původního formátu, pokud je známý
                img.save(output, format=img_format, quality=85)
                output.seek(0)

                # Aktualizace bufferu s novými daty
                new_image_data = output.read()
                new_offset = len(buffer_data[buffer_index])
                buffer_data[buffer_index].extend(new_image_data)

                # Aktualizace bufferView s novými daty
                buffer_view.byteOffset = new_offset
                buffer_view.byteLength = len(new_image_data)

    # Aktualizace GLB bufferů
    update_buffer_data(gltf, buffer_data)

def process_images_in_gltf(gltf: GLTF2, max_width: float = 1024, max_height: float = 1024, min_size_kb: float = 50, quality: int = 85):
    """
    Převádí obrázky v GLTF souboru na formát WebP a zmenšuje je na zadané maximální rozměry.
    Obrázky se zpracovávají pouze, pokud jejich velikost přesahuje zadaný práh (v kB).

    :param gltf: GLTF objekt obsahující obrázky.
    :param max_width: Maximální šířka obrázku.
    :param max_height: Maximální výška obrázku.
    :param min_size_kb: Minimální velikost obrázku (v kB) pro zpracování.
    """
    buffer_data = get_buffer_data(gltf)

    for image in gltf.images:
        if image.bufferView is not None:
            buffer_view = gltf.bufferViews[image.bufferView]
            buffer_index = buffer_view.buffer
            start = buffer_view.byteOffset or 0
            end = start + buffer_view.byteLength


            # Podmínka pro minimální velikost obrázku
            if buffer_view.byteLength < min_size_kb * 1024:
                # pokud je obrázek menší než daný práh, přeskočíme ho
                continue

            image_data = io.BytesIO(buffer_data[buffer_index][start:end])

            # Načtení obrázku pomocí PIL
            img = Image.open(image_data)

            doResize = img.width > max_width or img.height > max_height

            if not doResize and image.mimeType == "image/webp":
                # pokud není třeba zmenšovat a obrázek je již ve formátu WebP, přeskočíme ho 
                continue

            # Změna velikosti obrázku, pokud přesahuje maximální rozměry
            if doResize:
                img.thumbnail((max_width, max_height))  # Zmenšení obrázku

            # Konverze obrázku do WebP
            output = io.BytesIO()
            img.save(output, format="WEBP", quality=quality)
            output.seek(0)

            # Aktualizace bufferu s novými daty
            new_image_data = output.read()
            new_offset = len(buffer_data[buffer_index])
            buffer_data[buffer_index].extend(new_image_data)

            # Aktualizace bufferView s novými daty
            buffer_view.byteOffset = new_offset
            buffer_view.byteLength = len(new_image_data)

            # Aktualizace MIME typu na image/webp
            image.mimeType = "image/webp"

    # Aktualizace GLB dat
    update_buffer_data(gltf, buffer_data)

if __name__ == "__main__":

    path = r"..\Sconces_10102024_01\Sconces_10102024_01_level1-31_optimized.glb"

    # Načtení GLB souboru
    gltf = GLTF2().load(path)

    # remove_empty_nodes(gltf)

    # clean_gltf(gltf)

    # optimize_buffers(gltf)


    # convert_images_to_webp(gltf)
    resize_images_in_gltf(gltf)

    # process_images_in_gltf(gltf)



    # Uložení GLB souboru
    gltf.save(path.replace('.glb', '_cleaned.glb'))
