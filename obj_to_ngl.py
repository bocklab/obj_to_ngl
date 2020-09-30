#
# A small example of creating a precomputed neuroglancer data source to host meshes (only).
#

import argparse
import trimesh
import os
import json

from pathlib import Path

from cloudvolume import CloudVolume, Mesh

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cvpath", help="Path to precomputed volume to create")
    parser.add_argument("meshes", nargs="+", help="Mesh files to convert")
    parser.add_argument("--initial-id", default=1, type=int, help="Initial ID for meshes")
    args = parser.parse_args()

    cvpath = args.cvpath
    mesh_path = os.path.join(cvpath, "mesh")
    os.makedirs(mesh_path, exist_ok=True)

    with open(os.path.join(cvpath, "info"), "w") as f:
        info = {
            "data_type": "uint64",
            "scales": [
                {
                    "key" : "fake",
                    "encoding" : "raw",
                    "voxel_offset": [0,0,0],
                    "resolution": [4,4,40],
                    "size": [ 248832, 134144, 7063 ],
                    "chunk_sizes": [[512, 512, 16]]
                }
            ],
            "mesh": "mesh",
            "type": "segmentation",
            "num_channels": 1
        }
        f.write(json.dumps(info))

    with open(os.path.join(mesh_path, "info"), "w") as f:
        info = {"@type" : "neuroglancer_legacy_mesh"}
        f.write(json.dumps(info))

    mesh_id = args.initial_id
    for meshfile in args.meshes:
        # This will work when https://github.com/seung-lab/cloud-volume/pull/413 is merged:
        #cv_mesh = Mesh.from_obj(text=Path(meshfile).read_text(), segid=mesh_id)

        # Until then, use trimesh:
        tmesh = trimesh.load_mesh(meshfile)
        cv_mesh = Mesh(vertices=tmesh.vertices, faces=tmesh.faces, segid=mesh_id)

        ngl_mesh_file = "%d.frag" % mesh_id
        with open(os.path.join(mesh_path, "%d:0" % (mesh_id)), "w") as f:
            info = {"fragments" : [ngl_mesh_file]}
            f.write(json.dumps(info))

        with open(os.path.join(mesh_path, ngl_mesh_file), "wb") as f:
            f.write(cv_mesh.to_precomputed())

        print(cv_mesh)

        mesh_id += 1

if __name__ == "__main__":
    main()

