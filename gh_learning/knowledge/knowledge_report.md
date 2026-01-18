# GHX Knowledge Report

## Statistics
- Total component types: 141
- Total connection patterns: 155

## Top 20 Most Used Components

### Wasp_Save to DisCo (used 487 times)
- GUID: `410755b1-224a-4c1e-a407-bf32fb45ea7e`

### Panel (used 319 times)
- GUID: `59e0b89a-e487-49f8-bab8-b5bab16be14c`

### Scribble (used 212 times)
- GUID: `7f5c6c55-f846-4a08-9c9a-cfdc285cc6fe`

### Number Slider (used 203 times)
- GUID: `57da07bd-ecab-415d-9d86-af36d7073abc`

### Custom Preview (used 97 times)
- GUID: `537b0419-bbc2-4ff4-bf08-afe526367b2c`
- Inputs:
  - `G`: ['Geometry']
  - `M`: ['Material']
  - `S`: ['Shader']

### Colour Swatch (used 91 times)
- GUID: `9c53bac0-ba66-40bd-8154-ce9829b9db1a`

### Curve (used 87 times)
- GUID: `d5967b9f-e8ee-436b-a8ad-29fdcecf32d5`

### Button (used 86 times)
- GUID: `a8b97322-2d53-47cd-905e-b932c3ccd74e`

### Point (used 80 times)
- GUID: `fbac3e32-f100-4292-8692-77240a42fd1a`

### Boolean Toggle (used 73 times)
- GUID: `2e78987b-9dfb-42a2-8b76-3923ac8bd91a`

### Geometry (used 62 times)
- GUID: `ac2bc2cb-70fb-4dd5-9c78-7e1ea97fe278`

### Merge (used 50 times)
- GUID: `3cadddef-1e2b-4c09-9390-0e8f78f7609f`

### Sketch (used 39 times)
- GUID: `2844fec5-142d-4381-bd5d-4cbcef6d6fed`

### Brep (used 33 times)
- GUID: `919e146f-30ae-4aae-be34-4d72f555e7da`

### Gradient (used 19 times)
- GUID: `6da9f120-3ad0-4b6e-9fe0-f8cde3a649b7`
- Inputs:
  - `L0`: ['Lower limit']
  - `L1`: ['Upper limit']
  - `t`: ['Parameter']
- Outputs:
  - `C`: ['Colour']

### Point List (used 19 times)
- GUID: `cc14daa5-911a-4fcc-8b3b-1149bf7f2eeb`
- Inputs:
  - `P`: ['Points']
  - `S`: ['Size']

### List Item (used 16 times)
- GUID: `59daf374-bc21-4a5e-8282-5504fb7ae9ae`

### List Length (used 15 times)
- GUID: `1817fd29-20ae-4503-b542-f0fb651e67d7`
- Inputs:
  - `L`: ['List']
- Outputs:
  - `L`: ['Length']

### Remap Numbers (used 15 times)
- GUID: `2fcc2743-8339-4cdf-a046-a1f17439191d`
- Inputs:
  - `V`: ['Value']
  - `S`: ['Source']
  - `T`: ['Target']
- Outputs:
  - `R`: ['Mapped']
  - `C`: ['Clipped']

### Bounds (used 14 times)
- GUID: `f44b92b0-3b5b-493a-86f4-fd7408c3daf3`
- Inputs:
  - `N`: ['Numbers']
- Outputs:
  - `I`: ['Domain']

## Top 20 Connection Patterns

- `Bounds.I -> Remap Numbers.S` (15 times)
- `Gradient.C -> Custom Preview.M` (11 times)
- `Area.C -> Line SDL.S` (8 times)
- `Gradient.C -> Custom Preview.S` (7 times)
- `Unit Y.V -> Line SDL.D` (7 times)
- `Volume.C -> Scale NU.P` (7 times)
- `Larger Than.> -> Cull Pattern.P` (7 times)
- `List Length.L -> Random.N` (6 times)
- `Construct Point.Pt -> Iso Curve.uv` (6 times)
- `Bounding Box.B -> Scale NU.G` (6 times)
- `Bounding Box.B -> Volume.G` (6 times)
- `Pull Point.D -> Remap Numbers.V` (6 times)
- `Range.R -> Construct Point.X` (5 times)
- `Range.R -> Construct Point.Y` (5 times)
- `Unit X.V -> Move.T` (5 times)
- `List Length.L -> Repeat Data.L` (5 times)
- `Pull Point.D -> Bounds.N` (5 times)
- `Cull Pattern.L -> Custom Preview.G` (5 times)
- `Random.R -> Gradient.t` (4 times)
- `List Length.L -> Split List.i` (4 times)