# Mouse digestive and conduit teaching extension

Twelve independently selectable meshes: esophagus, duodenum, jejunum, ileum, caecum, colon, terminal colon / rectal segment, trachea, main bronchi A/B, and ureters A/B. The two small-intestine meshes form a continuous irregular bundle in three depth layers; the caecum is a curved blind sac. There are no human-style haustra, taenia coli, or appendix.

This is original **teaching geometry**, not additional segmentation recovered from the Digimouse specimen. Anatomical references inform morphology and names, while measured source surfaces anchor stomach and ureter endpoints. Bowel length, calibre, segment boundaries and precise routes are illustrative. Paired A/B labels refer to raw coordinates, not verified anatomical left/right. The two ends of a teaching segment are closed; overlap at junctions makes a visually continuous pathway, not a surgical lumen model.

## Files and integration

- `core.glb.gz`: 12 independent, named mesh nodes; gunzip then load as GLB.
- `metadata.json`: array with id, names, color, description, category, origin, bounds, center and triangle counts.
- `provenance.json`: source references, source SHA-256, endpoint anchors, limitations and license.
- `generate_digestive.py` and `glb_writer.py`: portable reproducible geometry generator.
- `review.png`: offline geometry check with sparse original source-organ faces as coordinate context. Speckles are the review renderer's deliberate source-face sampling, not damaged or decimated source geometry.
- `validate_assets.py` and `validation.json`: structural mesh verification.

Copy the two assets to `public/models/mouse-teaching/digestive/`. Geometry keeps raw source coordinates in **millimetres**: low Y is toward the head, low Z is ventral. Use the same model transform as the original Digimouse objects. No source mesh is included in this GLB and no source geometry has been edited.

## Regeneration

Requires Python 3 and NumPy; Pillow is used only for the optional offline preview. Keep the writer beside the generator, then use explicit input/output paths:

```sh
python generate_digestive.py --metadata path/to/digimouse-voxel/metadata.json --output path/to/mouse-teaching/digestive --skip-preview
python validate_assets.py --directory path/to/mouse-teaching/digestive
```

The source compressed GLB is read beside `--metadata`, or may be supplied with `--source-core`. Omit `--skip-preview` to also create the review image. Original source organ meshes are only read as coordinate anchors and review context.

## License and references

The new teaching geometry and scripts are licensed **CC BY-SA 4.0**, attributable to Animal Atlas contributors. The original Digimouse source retains its own CC BY-SA terms. Reference atlas drawings were consulted for anatomical facts; no reference images or external mesh geometry were copied. Source URLs and the exact Digimouse hash are in `provenance.json`.

- [JAX / MGI Cook atlas, abdominal viscera](https://informatics.jax.org/cookbook/figures/figure54.shtml)
- [Cook atlas, alimentary canal](https://www.informatics.jax.org/cookbook/figures/figure57.shtml)
- [Cook atlas, trachea and lungs](https://informatics.jax.org/cookbook/figures/figure53.shtml)
- [Cook atlas, male urogenital organs](https://informatics.jax.org/cookbook/figures/figure62.shtml)
- [INHAND rodent gastrointestinal morphology](https://pmc.ncbi.nlm.nih.gov/articles/PMC4765498/)
- [Digimouse source atlas](https://neuroimage.usc.edu/neuro/Digimouse)
