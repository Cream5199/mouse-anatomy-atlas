# Reproducible Digimouse surfaces

`atlas.zip` is the original 0.1 mm, 380 × 992 × 208 labelled Digimouse volume from https://neuroimage.usc.edu/mouse_atlas/atlas.zip. The archive includes the source license (CC BY-SA 4.0). Full attribution is in `public/models/digimouse-voxel/ATTRIBUTION.txt`.

The original volume, reconstruction source, and ready-to-use compressed GLB files are included in this repository. You can run or build the web app without Python. To reproduce the original surfaces yourself, use Python 3.12 or later with the pinned dependencies in an activated virtual environment:

```sh
python -m pip install -r scripts/voxel/requirements.txt
python scripts/voxel/generate.py
npm run build
```

Reconstruction may take several minutes and requires several GB of memory. It uses marching cubes with step 1 for each original label, preserving voxel spacing and original segmentation. There is no smoothing, decimation, subdivision, or invented anatomical detail. Normals alone are rounded to five decimals for compression; positions and triangle indices are checked byte for byte. The shared GLB writer is in `convert_mouse.py`.

The result preserves 21 source classes and 6,708,992 triangles, organized into 27 selectable objects. Twenty-six internal objects load initially, and the original body tissue surface loads on demand. Skin gzip parts are contiguous portions of one stream: concatenate in order before decompressing. Every individual hosting asset is below 25 MiB.

`npm run build` first verifies the original volume SHA-256 and decompressed GLB checksums in `assets.json`. Gzip container timestamps are intentionally excluded from those identity checks. Curated published labels, teaching descriptions, lazy-loading URLs, and attribution are tracked separately under `public/models/digimouse-voxel`; generation does not overwrite them.

The source provides broad tissue labels, not a separate mesh for every bone, vessel, or nerve. More triangles preserve the scanned boundary but cannot supply structures that were never segmented.

## Paired components

The final generation step, `refine_components.py`, splits six original labels that each contain exactly two complete connected components. It preserves every triangle, position and rounded normal, producing 26 internal objects plus unchanged body tissue. No bone fragments or guessed lobe boundaries are promoted into new organs. A/B does not claim anatomical left/right.

The current pipeline requires Python 3.12 or later for the pinned scientific dependencies. Published curated metadata contains 27 rows; generation uses its own original 21-row metadata under `.cache` as the split input and keeps the curated published labels separate. The final core checksum in `assets.json` refers to the paired-component output.
