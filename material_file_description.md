The OpenFL version of PreForm allows you to set custom material files for Form 1/1+ printers. Once OpenFL PreForm is installed, you can load the custom material file, [Form_1+_FLGPCL02_100.ini](Form_1+_FLGPCL02_100.ini) from the PreForm UI and print with it by selecting the "Load Custom Material..." button:

<img src="LoadCustomMaterial.png" width="500" alt="In the OpenFL version of PreForm, you can select a custom Form 1/1+ material by clicking the &quot;Load Custom Material...&quot; button.">

You can modify that file to create your own material settings. Below is a description of the most useful fields.

* `SliceHeight`, the slice thickness in mm. So 0.1 means 100&nbsp;µm. This should be a multiple of 0.0025&nbsp;mm (2.5&nbsp;µm), the size of one microstep.
* `Xcorrectionfactor`, `Ycorrectionfactor`, a scale factor applied to the model and supports to correct for shrinkage. This correction is applied prior to slicing.

PreForm has three main categories of exposure settings:

<img src="images/image02.png" width="386.50px" height="264.88px" alt="model, support, base">

When slicing, PreForm keeps track of which category each region in each slice came from and uses this information to apply exposure settings.</span></p>

The algorithm that generates laser paths from a slice, uses the `[PrintSettings]` block of the material file. At a high level a region consists of a perimeter/skin and a bulk fill region.

<img alt="" src="images/image01.png" style="width: 624.00px; height: 269.33px; margin-left: 0.00px; margin-top: 0.00px; transform: rotate(0.00rad) translateZ(0px); -webkit-transform: rotate(0.00rad) translateZ(0px);" title="">

The algorithm parameters are as follow:

<img alt="" src="images/image00.png" style="width: 624.00px; height: 518.86px; margin-left: 0.00px; margin-top: 0.00px; transform: rotate(0.00rad) translateZ(0px); -webkit-transform: rotate(0.00rad) translateZ(0px);" title="Line-placement parameters: OuterBoundaryOffset, etc.">

Once the outline and fill geometry is created, PreForm applies the speeds and powers corresponding to the category the geometry came from (model, support, and base), found in the `[perimeter]` and `[fill]` blocks of the settings file. Those `xyfeedrate` and `laserpowermw` fields, along with the spacing and number of passes, define exposure energy density. Assuming a single pass, suppose we have
* `ScanlineSpacing = 0.09` (mm)
* `modelxyfeedrate = 1550` (mm/s)
* `modellaserpowermw = 62` (mW)

then the energy density is 62&nbsp;mW /(0.09&nbsp;mm • 1550&nbsp;mm/s) = 0.4444&nbsp;mW&nbsp;s/mm<sup>2</sup> = 0.4444&nbsp;mJ/mm<sup>2</sup>.


# Copyright
Copyright 2016-2017 Formlabs

Released under the [Apache License](https://github.com/formlabs/openfl/blob/master/COPYING).
