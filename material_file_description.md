# Custom material file fields
PreForm has three main categories of exposure settings:

<img src="images/image02.png" width="386.50px" height="264.88px" alt="model, support, base">

When slicing, PreForm keeps track of which category each region in each slice came from and uses this information to apply exposure settings.</span></p>

The algorithm that generates laser paths from a slice, uses the `[PrintSettings]` block of the material file. At a high level a region consists of a perimeter/skin and a bulk fill region.

<img alt="" src="images/image01.png" style="width: 624.00px; height: 269.33px; margin-left: 0.00px; margin-top: 0.00px; transform: rotate(0.00rad) translateZ(0px); -webkit-transform: rotate(0.00rad) translateZ(0px);" title="">

The algorithm parameters are as follow:

<img alt="" src="images/image00.png" style="width: 624.00px; height: 518.86px; margin-left: 0.00px; margin-top: 0.00px; transform: rotate(0.00rad) translateZ(0px); -webkit-transform: rotate(0.00rad) translateZ(0px);" title="Line-placement parameters: OuterBoundaryOffset, etc.">

In addition there are three settings that affect how the model is sliced:
* `SliceHeight`
* `Xcorrectionfactor`
* `Ycorrectionfactor`

Slice height is the slicer resolution, and `X`/`Ycorrectionfactor`s are scaling factors applied to the entire model to correct for shrinkage. These are applied to the whole model/scene prior to slicing.

Once the outline and fill geometry is created, PreForm applies the speeds and powers corresponding to the category the geometry came from (model, support, and base), found in the `[perimeter]` and `[fill]` blocks of the settings file.
