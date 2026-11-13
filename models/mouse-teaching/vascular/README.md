# Mouse major-vessel teaching extension

This is newly authored teaching geometry positioned in the existing Digimouse raw millimetre coordinate system. It is **not** an extracted vessel segmentation, an anatomically measured vascular atlas, a simulation-ready lumen, or a complete circulatory system. Source organ and skeleton geometry were inspected for positional anchors only. No published anatomical image or third-party vessel mesh was copied or traced.

The 18 selectable meshes comprise nine arterial and nine venous trees: aortic arch/descending aorta, head-neck arteries, A/B forelimb arteries, renal/suprarenal arteries, celiac branches, mesenteric arteries, iliac/hindlimb arteries, pulmonary arteries; caval trunks, head-neck veins, A/B forelimb veins, renal veins, portal/mesenteric veins, hepatic veins, iliac/hindlimb veins, pulmonary veins.

## Files and reproduction

- `core.glb.gz`: deployment-ready compressed glTF binary.
- `core.glb`: equivalent uncompressed glTF binary.
- `metadata.json`: 18 independent names/categories/centers/bounds and teaching provenance.
- `authored-paths.json`: every authored control point and radius in raw mm.
- `generate_vascular.py`, `glb_writer.py`: portable generator and local writer.
- `validation.json`: counts, sizes, checksum and limitations.
- `vascular-preview.png`: offline oblique and ventral mesh preview; faint source structures are position context, not new content.

Install Python and NumPy, then run from any directory:

```sh
python generate_vascular.py --output ./output
```

The generator requires only NumPy and the adjacent `glb_writer.py`; no absolute workspace path, source download, network access or SciPy dependency is required. Control-point landmarks are embedded and also emitted in `authored-paths.json`. The optional preview script requires Pillow and the local inspection `source-points.npz`; this file is not required to regenerate the vascular asset and is not an input to the production website.

Raw axis convention: head is toward smaller Y, ventral surface is toward smaller Z. A is the lower-X model side, B the higher-X side. This intentionally does not assert anatomically confirmed left/right for the Digimouse specimen. The arch topology is oriented within this teaching coordinate convention; it is not a measured orientation of that specimen's vessels.

Main trunk radii are roughly 0.25–0.44 mm, selected branches about 0.09–0.24 mm, and a limited number of terminal teaching branches 0.05–0.085 mm. These dimensions are chosen for readable illustration, not extracted measurements. Red and blue indicate arterial/venous categories, including pulmonary vessels; the colors do not encode oxygenation.

Each named tree is one glTF mesh. Smooth Hermite-curve tubes overlap at shared root junctions; tube surfaces are not Boolean-unioned into a watertight vascular lumen. They are suitable for rendering, independent selection and explode/reassemble, not hemodynamic analysis. Internal junction caps are hidden within the joining branches.

## Primary anatomical references (facts only)

1. Margaret J. Cook, *The Anatomy of the Laboratory Mouse*, maintained by Mouse Genome Informatics/Jackson Laboratory: [circulatory chapter](https://www.informatics.jax.org/cookbook/chapters/circulatory.shtml). The drawings were consulted for anatomical relationships, not copied. Relevant entries include [thorax after heart removal, Fig. 92](https://www.informatics.jax.org/cookbook/figures/figure92.shtml), [portal system, Fig. 81](https://www.informatics.jax.org/cookbook/figures/figure81.shtml), and [renal vessels, Fig. 111](https://www.informatics.jax.org/cookbook/figures/figure111.shtml). These support the distinction between portal inflow and hepatic venous outflow, renal connections and paired cranial venous routes.
2. [Validation of the murine aortic arch as a model to study human vascular diseases](https://pmc.ncbi.nlm.nih.gov/articles/PMC2871992/). Original cast and micro-CT study: the common murine branching order is brachiocephalic trunk, common carotid and subclavian on the other side. The geometry here preserves that topology; it does not import the study meshes or assume identical individual geometry.
3. [Characterization of the Arterial Anatomy of the Murine Hindlimb](https://pmc.ncbi.nlm.nih.gov/articles/PMC3875518/). Original murine angiographic/dissection study supporting common/external/internal iliac, femoral, deep femoral, popliteal and saphenous regional pathways. Only selected regional branches are represented.
4. [Protocol for studying the superior mesenteric artery in mice](https://pmc.ncbi.nlm.nih.gov/articles/PMC11834953/). Mouse-specific relationship of the mesenteric trunk to abdominal aorta and renal-vein region. Terminal intestinal courses in this teaching extension remain authored and approximate.
5. [Hemodynamics in the mouse aortic arch as assessed by MRI, ultrasound, and numerical modeling](https://journals.physiology.org/doi/full/10.1152/ajpheart.00796.2006). Primary mouse imaging labels both right and left superior vena cavae; this informed avoidance of an unqualified human single-SVC layout.
6. [USC Digimouse](https://neuroimage.usc.edu/neuro/Digimouse) and [Dogdas et al. 2007](https://pmc.ncbi.nlm.nih.gov/articles/PMC3006167/) supply the underlying organ/bone positional context. Those sources do not supply the vessel paths drawn here.

## Authorship and license

Original mouse vascular teaching extension created for Animal Atlas, 2026. Generated assets, authored curve data, and accompanying generator/preview scripts are provided under **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**: https://creativecommons.org/licenses/by-sa/4.0/ . Credit “Animal Atlas — original mouse vascular teaching extension”; indicate changes and share adaptations under the same license. Reference publications retain their respective rights; no rights to their figures are conveyed.
