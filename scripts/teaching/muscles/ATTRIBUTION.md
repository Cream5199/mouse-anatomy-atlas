# Mouse teaching muscle extension

Assets and generator: **CC BY-SA 4.0**.
https://creativecommons.org/licenses/by-sa/4.0/

The 26 muscle-group surfaces were authored for Animal Atlas with curved lofts,
tapering tendon ends, asymmetric bellies and subtle longitudinal fascicle relief.
The muscle surfaces are teaching reconstructions, not CT-segmented muscles.
No muscle mesh was copied from the anatomy references.

The pose uses the original Digimouse skeleton as an alignment reference:
B. Dogdas, D. Stout, A. Chatziioannou and R. M. Leahy,
*Digimouse: A 3D Whole Body Mouse Atlas from CT and Cryosection Data* (2007).
https://neuroimage.usc.edu/neuro/Digimouse_Download

Landmarks were estimated from front and side source-skeleton projections,
then the depth coordinate was checked against local source vertices. They
are practical teaching anchors, not validated muscle attachment measurements.
A/B preserve the source's positional pairing without asserting anatomical
left and right.

Anatomical terminology and qualitative muscle arrangements were checked against:

- *A Whole-Body Musculoskeletal Model of the Mouse*:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC8865483/
- Charles et al., *Musculoskeletal Geometry, Muscle Architecture and Functional
  Specialisations of the Mouse Hindlimb*:
  https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0147669
- Mouse Genome Informatics, skeletal muscle terminology:
  https://www.informatics.jax.org/vocab/gxd/anatomy/EMAPA%3A35988

## Rebuild

Use Python 3.12, NumPy 2.3.5 and SciPy 1.18.1 in a virtual environment.
`generate_muscles.py` also checks an optional `pydeps/` beside the script.

```text
python generate_muscles.py --output generated --landmarks landmarks.json
```

The GLB keeps the original source millimetre coordinate frame: head toward
smaller Y and the ventral observer toward smaller Z. The application applies
its shared X-axis rotation to both the original organs and these additions.

`COLOR_0` contains linear RGB vertex colors with a white base material, showing
soft pink muscle bellies and pale tendon ends. Enable vertex colors in the
viewer. The external-oblique and rectus-abdominis pairs are hidden by default
to retain an unobstructed central viscera view.
