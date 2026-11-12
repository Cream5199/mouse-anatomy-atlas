# Mouse teaching extension

These are authored, approximate anatomical teaching meshes anchored to the existing Digimouse skeleton and organ positions. They are not newly recovered scan segmentations. No third-party meshes or reference illustrations are copied.

The 56 new objects comprise 12 digestive/respiratory/urinary conduit objects, 18 major arterial/venous regional trees and 26 named skeletal muscle groups. They retain the same raw millimetre coordinate system as the original model. All A/B labels refer to coordinate-side groups, not verified anatomical laterality.

## Reproduce

Ready-to-use compressed models are included in this repository. These Python steps are optional; they are for regenerating geometry, not starting the web app.

Use Python 3.12+ with the versions in `../voxel/requirements.txt` (NumPy and SciPy; Pillow is optional for the digestive script's asset preview). Generate the original mouse assets first as described in `../voxel/README.md`, then:

```
python scripts/teaching/generate.py
npm run build
```

When using an isolated dependency directory, include it in PYTHONPATH. Each system also supports `python generate_<system>.py --output <directory>`. Digestive geometry additionally accepts `--metadata` and `--source-core`; the wrapper passes explicit paths. Muscles use the tracked `landmarks.json`. Vascular authored curve anchors are in the script and emitted as `authored-paths.json`.

`assets.json` validates normalized source text and the decompressed final GLBs. Gzip timestamps are excluded from identity checks. Vertex colors in the muscle GLB are linear RGB and must be rendered with vertexColors enabled and a white base material. Four abdominal-wall meshes start hidden to retain a visceral viewing window.

All new geometry and code are released under CC BY-SA 4.0. Source facts, authorship, scope and limitations are recorded in `/models/mouse-teaching/ATTRIBUTION.txt` and per-system provenance/validation files. These are schematic major structures, not complete measured vascular topology, muscle attachments, physiological bowel length, histology or all anatomical subdivisions.
