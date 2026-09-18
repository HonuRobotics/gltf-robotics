// Dump what gz-common's mesh loader (the one Gazebo uses) produces for a mesh file.
#include <iostream>
#include <iomanip>
#include <gz/common/Console.hh>
#include <gz/common/MeshManager.hh>
#include <gz/common/Mesh.hh>
#include <gz/common/SubMesh.hh>
#include <gz/common/Material.hh>
#include <gz/common/Pbr.hh>
#include <gz/common/Image.hh>

static std::string img(const std::string &name, std::shared_ptr<const gz::common::Image> data)
{
  if (name.empty()) return "-";
  std::string s = name;
  if (data) s += " [" + std::to_string(data->Width()) + "x" + std::to_string(data->Height()) + "]";
  else s += " [no data]";
  return s;
}

int main(int argc, char **argv)
{
  gz::common::Console::SetVerbosity(4);
  for (int a = 1; a < argc; ++a)
  {
    std::string path = argv[a];
    std::cout << "\n===== " << path << std::endl;
    const gz::common::Mesh *mesh = gz::common::MeshManager::Instance()->Load(path);
    if (!mesh) { std::cout << "LOAD FAILED (null mesh)" << std::endl; continue; }
    std::cout << "bbox min " << mesh->Min() << "  max " << mesh->Max() << std::endl;
    std::cout << "submeshes " << mesh->SubMeshCount() << "  materials " << mesh->MaterialCount()
              << "  skeleton " << (mesh->HasSkeleton() ? "yes" : "no") << std::endl;
    for (unsigned i = 0; i < mesh->SubMeshCount(); ++i)
    {
      auto sm = mesh->SubMeshByIndex(i).lock();
      std::cout << "  submesh[" << i << "] name='" << sm->Name() << "' verts " << sm->VertexCount()
                << " tris " << sm->IndexCount() / 3 << " normals " << sm->NormalCount()
                << " uvsets " << sm->TexCoordSetCount();
      auto mi = sm->GetMaterialIndex();
      std::cout << " material " << (mi ? std::to_string(*mi) : std::string("NONE")) << std::endl;
      // Per-submesh bounds, from the vertices the loader actually built, so a node
      // transform's effect on one submesh is visible on its own.
      if (sm->VertexCount() > 0)
      {
        gz::math::Vector3d lo = sm->Vertex(0), hi = sm->Vertex(0);
        for (unsigned v = 1; v < sm->VertexCount(); ++v)
        {
          lo.Min(sm->Vertex(v)); hi.Max(sm->Vertex(v));
        }
        std::cout << "    bounds min " << lo << "  max " << hi << std::endl;
      }
    }
    for (unsigned i = 0; i < mesh->MaterialCount(); ++i)
    {
      auto m = mesh->MaterialByIndex(i);
      std::cout << "  material[" << i << "] diffuse " << m->Diffuse() << " transparency " << m->Transparency()
                << " alphaFromTexture " << m->TextureAlphaEnabled() << " threshold " << m->AlphaThreshold()
                << " twoSided " << m->TwoSidedEnabled() << " emissive " << m->Emissive() << std::endl;
      std::cout << "    base color: " << img(m->TextureImage(), m->TextureData()) << std::endl;
      const gz::common::Pbr *p = m->PbrMaterial();
      if (p)
      {
        std::cout << "    pbr metalness " << p->Metalness() << " roughness " << p->Roughness() << std::endl;
        std::cout << "    normal:    " << img(p->NormalMap(), p->NormalMapData()) << std::endl;
        std::cout << "    metalness: " << img(p->MetalnessMap(), p->MetalnessMapData()) << std::endl;
        std::cout << "    roughness: " << img(p->RoughnessMap(), p->RoughnessMapData()) << std::endl;
        std::cout << "    emissive:  " << img(p->EmissiveMap(), p->EmissiveMapData()) << std::endl;
        std::cout << "    lightmap:  " << img(p->LightMap(), p->LightMapData()) << " uvset " << p->LightMapTexCoordSet() << std::endl;
      }
    }
  }
  return 0;
}
