#
# A small example of creating a precomputed neuroglancer data source to host meshes (only). 
#
# Quick modification to parse a CSV file exported from R with headers 'Material' and 'Label'

import argparse
import trimesh
import numpy as np
import os
import json
import pandas

from pathlib import Path

from cloudvolume import CloudVolume, Mesh

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("meshcsv", help="Mesh files to convert")
    parser.add_argument("meshdir", help="Mesh files to convert")
    parser.add_argument("cvpath", help="Path to precomputed volume to create")
    parser.add_argument("--resolution", nargs=3, default=[4,4,40], help="Voxel resolution (full res)")
    parser.add_argument("--volume-size", nargs=3, default=[248832, 134144, 7063], help="Extent of segmentation (full res)")
    args = parser.parse_args()

    df = pandas.read_csv(args.meshcsv, header=1)

    cvpath = args.cvpath
    mesh_path = os.path.join(cvpath, "mesh")
    seg_props_path = os.path.join(cvpath, "seg_props")
    os.makedirs(mesh_path, exist_ok=True)
    os.makedirs(seg_props_path, exist_ok=True)

    segment_props = {
        "@type" : "neuroglancer_segment_properties",
        'inline' : {
            'ids' : [],
            'properties' : [
                {
                    "id" : "source",
                    "type" : "label",
                    "values" : []
                }
            ]
        }
    }

    # Set size to the max value in the polygons
    size = np.asarray([0,0,0])

    for _, row in df.iterrows():
        meshfile = os.path.join(args.meshdir, "%s.obj" % row['Material'])
        mesh_id = row['Nr']
        mesh_name = row['Material']
        if os.path.exists(meshfile):
            # This will work when https://github.com/seung-lab/cloud-volume/pull/413 is merged:
            #cv_mesh = Mesh.from_obj(text=Path(meshfile).read_text(), segid=mesh_id)

            # Until then, use trimesh:
            tmesh = trimesh.load_mesh(meshfile)

            vertices = np.asarray(tmesh.vertices)

            size[0] = max(size[0], np.max(vertices[:,0]))
            size[1] = max(size[1], np.max(vertices[:,1]))
            size[2] = max(size[2], np.max(vertices[:,2]))

            cv_mesh = Mesh(vertices=tmesh.vertices, faces=tmesh.faces, segid=mesh_id)

            ngl_mesh_file = "%d.frag" % mesh_id
            with open(os.path.join(mesh_path, "%d:0" % (mesh_id)), "w") as f:
                info = {"fragments" : [ngl_mesh_file]}
                f.write(json.dumps(info))

            with open(os.path.join(mesh_path, ngl_mesh_file), "wb") as f:
                f.write(cv_mesh.to_precomputed())

            segment_props['inline']['ids'].append(f'{mesh_id}')
            segment_props['inline']['properties'][0]['values'].append(mesh_name)
        
        else:
            print(f'{meshfile} does not exist. Skipping.')


    with open(os.path.join(seg_props_path, "info"), "w") as f:
        f.write(json.dumps(segment_props))        


    # Convert the entire space into units of "one entire brain" in case neuroglancer tries to load the image layer
    # resolution = np.asarray(args.resolution) * np.asarray(args.volume_size)
    
    resolution = size
    size = np.asarray([1,1,1])

    with open(os.path.join(cvpath, "info"), "w") as f:
        info = {
            "data_type": "uint64",
            "scales": [
                {
                    "key" : "fake",
                    "encoding" : "raw",
                    "voxel_offset": [0,0,0],
                    "resolution": resolution.tolist(),
                    "size": size.tolist(),
                    "chunk_sizes": [[256, 256, 16]]
                }
            ],
            "mesh": "mesh",
            "segment_properties" : "seg_props",
            "type": "segmentation",
            "num_channels": 1
        }
        f.write(json.dumps(info))

    with open(os.path.join(mesh_path, "info"), "w") as f:
        info = {"@type" : "neuroglancer_legacy_mesh"}
        f.write(json.dumps(info))

if __name__ == "__main__":
    main()

